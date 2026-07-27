from __future__ import annotations

import pandas as pd
from loguru import logger
from sqlalchemy import text

from src.analytics import (
    build_spatial_weights,
    classify_lisa_clusters,
    compute_moran_global,
    compute_moran_local,
)
from src.db.connection import get_connection


def create_spatial_indexes() -> None:
    queries = [
        "CREATE INDEX IF NOT EXISTS idx_crime_geometry "
        "ON safestreet.crime_records USING GIST (geometry)",
        "CREATE INDEX IF NOT EXISTS idx_infra_geometry "
        "ON safestreet.infrastructure_points USING GIST (geometry)",
        "CREATE INDEX IF NOT EXISTS idx_crime_h3 ON safestreet.crime_records (h3_index)",
        "CREATE INDEX IF NOT EXISTS idx_crime_category "
        "ON safestreet.crime_records (crime_category)",
        "CREATE INDEX IF NOT EXISTS idx_infra_h3 ON safestreet.infrastructure_points (h3_index)",
        "CREATE INDEX IF NOT EXISTS idx_h3_cells_h3 ON safestreet.h3_cells (h3_index)",
        "CREATE INDEX IF NOT EXISTS idx_h3_cells_city ON safestreet.h3_cells (city)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_h3_cells_h3_city "
        "ON safestreet.h3_cells (h3_index, city)",
        "ANALYZE safestreet.crime_records",
        "ANALYZE safestreet.infrastructure_points",
    ]
    with get_connection() as conn:
        for query in queries:
            conn.execute(text(query))
    logger.info("Indices espaciais criados com sucesso")


def populate_h3_cells(city: str, resolution: int = 9) -> None:
    query = text("""
        WITH crime_h3 AS (
            SELECT h3_index, COUNT(*) AS crime_count
            FROM safestreet.crime_records
            WHERE h3_index IS NOT NULL AND city = :city
            GROUP BY h3_index
        ),
        infra_by_type AS (
            SELECT h3_index, infra_type, COUNT(*) AS cnt
            FROM safestreet.infrastructure_points
            WHERE h3_index IS NOT NULL AND city = :city
            GROUP BY h3_index, infra_type
        ),
        lighting AS (
            SELECT h3_index, cnt AS lighting_count
            FROM infra_by_type
            WHERE infra_type = 'street_lamp'
        ),
        bus_stops AS (
            SELECT h3_index, cnt AS bus_count
            FROM infra_by_type
            WHERE infra_type = 'bus_stop'
        ),
        metro AS (
            SELECT h3_index, cnt AS metro_count
            FROM infra_by_type
            WHERE infra_type = 'metro_station'
        ),
        cameras AS (
            SELECT h3_index, cnt AS cam_count
            FROM infra_by_type
            WHERE infra_type = 'camera'
        ),
        nightlife AS (
            SELECT h3_index, SUM(cnt) AS nightlife_count
            FROM infra_by_type
            WHERE infra_type IN ('bar', 'pub', 'nightclub', 'restaurant')
            GROUP BY h3_index
        )
        INSERT INTO safestreet.h3_cells
            (h3_index, city, resolution, crime_count,
             lighting_density, bus_stop_density,
             metro_density, camera_count, nightlife_density)
        SELECT
            c.h3_index,
            :city,
            :resolution,
            c.crime_count,
            COALESCE(l.lighting_count, 0)::float
                / GREATEST(c.crime_count, 1),
            COALESCE(b.bus_count, 0)::float
                / GREATEST(c.crime_count, 1),
            COALESCE(m.metro_count, 0)::float
                / GREATEST(c.crime_count, 1),
            COALESCE(cam.cam_count, 0),
            COALESCE(n.nightlife_count, 0)::float
                / GREATEST(c.crime_count, 1)
        FROM crime_h3 c
        LEFT JOIN lighting l ON c.h3_index = l.h3_index
        LEFT JOIN bus_stops b ON c.h3_index = b.h3_index
        LEFT JOIN metro m ON c.h3_index = m.h3_index
        LEFT JOIN cameras cam ON c.h3_index = cam.h3_index
        LEFT JOIN nightlife n ON c.h3_index = n.h3_index
        ON CONFLICT (h3_index, city) DO UPDATE SET
            crime_count = EXCLUDED.crime_count,
            lighting_density = EXCLUDED.lighting_density,
            bus_stop_density = EXCLUDED.bus_stop_density,
            metro_density = EXCLUDED.metro_density,
            camera_count = EXCLUDED.camera_count,
            nightlife_density = EXCLUDED.nightlife_density
    """)
    with get_connection() as conn:
        conn.execute(query, {"city": city, "resolution": resolution})
    logger.info("Celulas H3 populadas para {}", city)


def calculate_nearest_infra_distance(city: str) -> None:
    for infra_type, col_name in [
        ("street_lamp", "dist_nearest_lit"),
        ("bus_stop", "dist_nearest_bus"),
        ("metro_station", "dist_nearest_metro"),
    ]:
        query = text(f"""
            UPDATE safestreet.h3_cells h
            SET {col_name} = (
                SELECT MIN(
                    ST_Distance(
                        ST_Centroid(c.geometry),
                        i.geometry
                    )
                )
                FROM safestreet.crime_records c
                JOIN safestreet.infrastructure_points i ON true
                WHERE c.h3_index = h.h3_index
                  AND c.city = :city
                  AND i.infra_type = :infra_type
                  AND i.city = :city
            )
            WHERE h.city = :city
        """)
        with get_connection() as conn:
            conn.execute(
                query,
                {"city": city, "infra_type": infra_type},
            )
        logger.info(
            "Distancia ate {} calculada para {}",
            infra_type,
            city,
        )


def calculate_vulnerability_score(city: str) -> None:
    from src.analytics.statistics import compute_pca_vulnerability

    query = text("""
        SELECT h3_index, city, crime_count, lighting_density,
               dist_nearest_lit, bus_stop_density, metro_density,
               camera_count, nightlife_density
        FROM safestreet.h3_cells
        WHERE city = :city AND crime_count > 0
    """)
    with get_connection() as conn:
        result = conn.execute(query, {"city": city}).mappings().all()

    if not result:
        logger.warning("Nenhuma celula H3 com dados para PCA em {}", city)
        return

    df = pd.DataFrame([dict(r) for r in result])
    pca_result = compute_pca_vulnerability(df)

    if pca_result["scores"].empty:
        logger.warning("PCA nao retornou scores para {}", city)
        return

    df["vulnerability_score"] = pca_result["scores"].values

    with get_connection() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text(
                    "UPDATE safestreet.h3_cells "
                    "SET vulnerability_score = :score "
                    "WHERE h3_index = :h3 AND city = :city"
                ),
                {
                    "score": float(row["vulnerability_score"]),
                    "h3": row["h3_index"],
                    "city": city,
                },
            )

    logger.info(
        "Score de vulnerabilidade PCA calculado para {} | "
        "PC1 explica {:.1f}% da variancia | loadings: {}",
        city,
        pca_result["variance_explained"][0] * 100 if pca_result["variance_explained"] else 0,
        pca_result["loadings"],
    )


def calculate_moran_clusters(city: str) -> None:
    with get_connection() as conn:
        result = (
            conn.execute(
                text("""
                SELECT h3_index, crime_count, vulnerability_score
                FROM safestreet.h3_cells
                WHERE city = :city
                  AND crime_count > 0
                  AND vulnerability_score IS NOT NULL
                ORDER BY h3_index
            """),
                {"city": city},
            )
            .mappings()
            .all()
        )

    if not result:
        logger.warning(
            "Nenhuma celula H3 com dados para Moran em {}",
            city,
        )
        return

    df = pd.DataFrame([dict(r) for r in result])
    values = df["vulnerability_score"].values.astype(float)
    weights = build_spatial_weights(df)

    if weights is None:
        logger.warning(
            "Pesos espaciais nao disponiveis para {}",
            city,
        )
        return

    moran_global = compute_moran_global(values, weights)
    logger.info(
        "Moran Global {} I={:.4f}, p={:.4f}",
        city,
        moran_global["moran_i"],
        moran_global["p_value"],
    )

    local_result = compute_moran_local(values, weights)
    clusters = classify_lisa_clusters(
        local_result["q"],
        local_result["p_sim"],
    )
    df["moran_cluster"] = clusters

    with get_connection() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text(
                    "UPDATE safestreet.h3_cells "
                    "SET moran_cluster = :cluster "
                    "WHERE h3_index = :h3 AND city = :city"
                ),
                {
                    "cluster": row["moran_cluster"],
                    "h3": row["h3_index"],
                    "city": city,
                },
            )

    cluster_counts = pd.Series(clusters).value_counts().to_dict()
    logger.info("Clusters LISA {}: {}", city, cluster_counts)
