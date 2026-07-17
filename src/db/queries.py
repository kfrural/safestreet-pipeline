from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy import text

from src.db.connection import get_connection


def insert_crime_records_batch(records: list[dict[str, Any]], batch_size: int = 1000) -> int:
    query = text("""
        INSERT INTO safestreet.crime_records
            (occurrence_id, nature, crime_category,
             date, time, city, neighborhood, geometry, h3_index)
        VALUES
            (:occurrence_id, :nature, :crime_category,
             :date, :time, :city, :neighborhood,
             ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :h3_index)
        ON CONFLICT (occurrence_id) DO NOTHING
    """)
    total = 0
    with get_connection() as conn:
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            conn.execute(query, batch)
            total += len(batch)
        logger.info("Inseridos {} registros criminais", total)
    return total


def insert_infrastructure_batch(records: list[dict[str, Any]], batch_size: int = 1000) -> int:
    query = text("""
        INSERT INTO safestreet.infrastructure_points (osm_id, infra_type, city, geometry, h3_index)
        VALUES (:osm_id, :infra_type, :city, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :h3_index)
        ON CONFLICT (osm_id) DO NOTHING
    """)
    total = 0
    skipped = 0
    with get_connection() as conn:
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            for r in batch:
                if not r.get("osm_id"):
                    r["osm_id"] = f"{r['city']}_{r['infra_type']}_{i + skipped}"
                    skipped += 1
            conn.execute(query, batch)
            total += len(batch)
        logger.info("Inseridos {} pontos de infraestrutura", total)
    return total


def get_h3_cells(city: str | None = None) -> list[dict[str, Any]]:
    if city:
        query = text("""
            SELECT
                h3_index, city, resolution, crime_count,
                lighting_density, bus_stop_density, metro_density,
                camera_count, nightlife_density,
                dist_nearest_lit, dist_nearest_bus, dist_nearest_metro,
                vulnerability_score, moran_cluster
            FROM safestreet.h3_cells
            WHERE city = :city
            ORDER BY vulnerability_score DESC
        """)
        try:
            with get_connection() as conn:
                result = conn.execute(query, {"city": city}).mappings().all()
            return [dict(row) for row in result]
        except Exception:
            return []
    else:
        query = text("""
            SELECT
                h3_index, city, resolution, crime_count,
                lighting_density, bus_stop_density, metro_density,
                camera_count, nightlife_density,
                dist_nearest_lit, dist_nearest_bus, dist_nearest_metro,
                vulnerability_score, moran_cluster
            FROM safestreet.h3_cells
            ORDER BY vulnerability_score DESC
        """)
        try:
            with get_connection() as conn:
                result = conn.execute(query).mappings().all()
            return [dict(row) for row in result]
        except Exception:
            return []


def get_cities_with_data() -> list[str]:
    query = text("""
        SELECT DISTINCT city FROM safestreet.h3_cells
        WHERE crime_count > 0
        ORDER BY city
    """)
    try:
        with get_connection() as conn:
            result = conn.execute(query).mappings().all()
        return [row["city"] for row in result]
    except Exception:
        return []


def get_city_stats(city: str) -> dict[str, Any]:
    query = text("""
        SELECT
            COUNT(*) as total_cells,
            SUM(crime_count) as total_crimes,
            COUNT(*) FILTER (WHERE vulnerability_score >= 0.7) as high_risk,
            COUNT(*) FILTER (WHERE moran_cluster = 'HH') as moran_hh
        FROM safestreet.h3_cells
        WHERE city = :city
    """)
    try:
        with get_connection() as conn:
            result = conn.execute(query, {"city": city}).mappings().one()
        return dict(result)
    except Exception:
        return {"total_cells": 0, "total_crimes": 0, "high_risk": 0, "moran_hh": 0}


def get_crime_categories(city: str) -> list[dict[str, Any]]:
    query = text("""
        SELECT
            crime_category,
            COUNT(*) AS count,
            ROUND(COUNT(*)::numeric / NULLIF(SUM(COUNT(*)) OVER (), 0) * 100, 1) AS pct
        FROM safestreet.crime_records
        WHERE city = :city AND crime_category IS NOT NULL
        GROUP BY crime_category
        ORDER BY count DESC
    """)
    try:
        with get_connection() as conn:
            result = conn.execute(query, {"city": city}).mappings().all()
        return [dict(row) for row in result]
    except Exception:
        return []


def get_crime_by_infra_proximity(city: str) -> list[dict[str, Any]]:
    query = text("""
        SELECT
            cr.crime_category,
            CASE
                WHEN h.dist_nearest_lit IS NULL THEN 'Sem dados'
                WHEN h.dist_nearest_lit < 200 THEN '0-200m'
                WHEN h.dist_nearest_lit < 500 THEN '200-500m'
                WHEN h.dist_nearest_lit < 1000 THEN '500-1000m'
                ELSE '1000m+'
            END AS lighting_distance,
            COUNT(*) AS crime_count
        FROM safestreet.crime_records cr
        JOIN safestreet.h3_cells h ON cr.h3_index = h.h3_index AND cr.city = h.city
        WHERE cr.city = :city AND cr.crime_category IS NOT NULL
        GROUP BY cr.crime_category, lighting_distance
        ORDER BY cr.crime_category, lighting_distance
    """)
    try:
        with get_connection() as conn:
            result = conn.execute(query, {"city": city}).mappings().all()
        return [dict(row) for row in result]
    except Exception:
        return []


def get_crime_by_transit_proximity(city: str) -> list[dict[str, Any]]:
    query = text("""
        SELECT
            cr.crime_category,
            CASE
                WHEN h.dist_nearest_bus IS NULL THEN 'Sem dados'
                WHEN h.dist_nearest_bus < 200 THEN '0-200m'
                WHEN h.dist_nearest_bus < 500 THEN '200-500m'
                WHEN h.dist_nearest_bus < 1000 THEN '500-1000m'
                ELSE '1000m+'
            END AS transit_distance,
            COUNT(*) AS crime_count
        FROM safestreet.crime_records cr
        JOIN safestreet.h3_cells h ON cr.h3_index = h.h3_index AND cr.city = h.city
        WHERE cr.city = :city AND cr.crime_category IS NOT NULL
        GROUP BY cr.crime_category, transit_distance
        ORDER BY cr.crime_category, transit_distance
    """)
    try:
        with get_connection() as conn:
            result = conn.execute(query, {"city": city}).mappings().all()
        return [dict(row) for row in result]
    except Exception:
        return []


def get_crime_locations(city: str, category: str | None = None) -> list[dict[str, Any]]:
    query = text("""
        SELECT
            ST_Y(geometry) AS latitude,
            ST_X(geometry) AS longitude,
            nature,
            crime_category,
            neighborhood,
            time
        FROM safestreet.crime_records
        WHERE city = :city
          AND crime_category IS NOT NULL
          AND (:category IS NULL OR crime_category = :category)
    """)
    try:
        with get_connection() as conn:
            result = conn.execute(query, {"city": city, "category": category}).mappings().all()
        return [dict(row) for row in result]
    except Exception:
        return []


def get_correlation_data(city: str) -> list[dict[str, Any]]:
    query = text("""
        SELECT
            crime_count,
            lighting_density,
            bus_stop_density,
            metro_density,
            camera_count,
            nightlife_density,
            dist_nearest_lit,
            dist_nearest_bus,
            dist_nearest_metro,
            vulnerability_score
        FROM safestreet.h3_cells
        WHERE city = :city AND crime_count > 0
    """)
    try:
        with get_connection() as conn:
            result = conn.execute(query, {"city": city}).mappings().all()
        return [dict(row) for row in result]
    except Exception:
        return []


def get_crime_by_hour(city: str) -> list[dict[str, Any]]:
    query = text("""
        SELECT
            time AS hour_label,
            COUNT(*) AS crime_count,
            crime_category
        FROM safestreet.crime_records
        WHERE city = :city
          AND time IS NOT NULL
          AND time != ''
        GROUP BY time, crime_category
        ORDER BY time
    """)
    try:
        with get_connection() as conn:
            result = conn.execute(query, {"city": city}).mappings().all()
        return [dict(row) for row in result]
    except Exception:
        return []


def get_top_natures(city: str, limit: int = 10) -> list[dict[str, Any]]:
    query = text("""
        SELECT
            crime_category,
            nature,
            COUNT(*) AS count
        FROM safestreet.crime_records
        WHERE city = :city
          AND crime_category IS NOT NULL
          AND nature IS NOT NULL
          AND nature != 'nan'
        GROUP BY crime_category, nature
        ORDER BY crime_category, count DESC
    """)
    try:
        with get_connection() as conn:
            result = conn.execute(query, {"city": city}).mappings().all()
        rows = [dict(row) for row in result]
        from collections import defaultdict

        by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            by_cat[r["crime_category"]].append(r)
        top = []
        for cat, items in by_cat.items():
            for item in items[:limit]:
                top.append(item)
        return top
    except Exception:
        return []


def get_vulnerability_gaps(city: str) -> list[dict[str, Any]]:
    query = text("""
        SELECT
            h3_index,
            crime_count,
            lighting_density,
            dist_nearest_lit,
            bus_stop_density,
            camera_count,
            nightlife_density,
            vulnerability_score
        FROM safestreet.h3_cells
        WHERE city = :city
          AND crime_count > 0
          AND (
              (lighting_density = 0 AND crime_count > 1)
              OR (dist_nearest_lit > 1000 AND crime_count > 1)
          )
        ORDER BY crime_count DESC, vulnerability_score DESC
        LIMIT 20
    """)
    try:
        with get_connection() as conn:
            result = conn.execute(query, {"city": city}).mappings().all()
        return [dict(row) for row in result]
    except Exception:
        return []
