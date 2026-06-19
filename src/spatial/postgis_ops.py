from __future__ import annotations

from loguru import logger
from sqlalchemy import text

from src.db.connection import get_connection


def create_spatial_indexes() -> None:
    queries = [
        "CREATE INDEX IF NOT EXISTS idx_crime_geometry ON safestreet.crime_records USING GIST (geometry)",
        "CREATE INDEX IF NOT EXISTS idx_infra_geometry ON safestreet.infrastructure_points USING GIST (geometry)",
        "CREATE INDEX IF NOT EXISTS idx_crime_h3 ON safestreet.crime_records (h3_index)",
        "CREATE INDEX IF NOT EXISTS idx_infra_h3 ON safestreet.infrastructure_points (h3_index)",
        "CREATE INDEX IF NOT EXISTS idx_h3_cells_h3 ON safestreet.h3_cells (h3_index)",
        "ANALYZE safestreet.crime_records",
        "ANALYZE safestreet.infrastructure_points",
    ]
    with get_connection() as conn:
        for query in queries:
            conn.execute(text(query))
    logger.info("Índices espaciais criados com sucesso")


def calculate_lighting_density() -> None:
    query = text("""
        WITH h3_stats AS (
            SELECT
                h3_index,
                COUNT(*) AS crime_count,
                COALESCE(
                    (SELECT COUNT(*)
                     FROM safestreet.infrastructure_points i
                     WHERE i.h3_index = c.h3_index),
                    0
                ) AS infra_count
            FROM safestreet.crime_records c
            WHERE c.h3_index IS NOT NULL
            GROUP BY c.h3_index
        )
        INSERT INTO safestreet.h3_cells (h3_index, resolution, crime_count, lighting_density)
        SELECT
            h3_index,
            9,
            crime_count,
            CASE WHEN crime_count > 0
                THEN infra_count::FLOAT / crime_count
                ELSE 0
            END AS lighting_density
        FROM h3_stats
        ON CONFLICT (h3_index) DO UPDATE SET
            crime_count = EXCLUDED.crime_count,
            lighting_density = EXCLUDED.lighting_density
    """)
    with get_connection() as conn:
        conn.execute(query)
    logger.info("Densidade de iluminação calculada por célula H3")


def calculate_nearest_light_distance() -> None:
    query = text("""
        UPDATE safestreet.h3_cells h
        SET dist_nearest_lit = (
            SELECT MIN(
                ST_Distance(
                    ST_Centroid(c.geometry),
                    i.geometry
                )
            )
            FROM safestreet.crime_records c
            JOIN safestreet.infrastructure_points i ON true
            WHERE c.h3_index = h.h3_index
        )
    """)
    with get_connection() as conn:
        conn.execute(query)
    logger.info("Distância até iluminação mais próxima calculada")
