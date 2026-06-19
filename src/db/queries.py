from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy import text

from src.db.connection import get_connection


def insert_crime_records_batch(records: list[dict[str, Any]], batch_size: int = 1000) -> int:
    query = text("""
        INSERT INTO safestreet.crime_records (occurrence_id, nature, date, time, geometry, h3_index)
        VALUES (:occurrence_id, :nature, :date, :time, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :h3_index)
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
        INSERT INTO safestreet.infrastructure_points (osm_id, infra_type, geometry, h3_index)
        VALUES (:osm_id, :infra_type, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :h3_index)
        ON CONFLICT (osm_id) DO NOTHING
    """)
    total = 0
    with get_connection() as conn:
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            conn.execute(query, batch)
            total += len(batch)
        logger.info("Inseridos {} pontos de infraestrutura", total)
    return total


def get_crime_density_by_h3(resolution: int = 9) -> list[dict[str, Any]]:
    query = text("""
        SELECT
            h3_index,
            COUNT(*) AS crime_count
        FROM safestreet.crime_records
        WHERE h3_index IS NOT NULL
        GROUP BY h3_index
    """)
    with get_connection() as conn:
        result = conn.execute(query).mappings().all()
    return [dict(row) for row in result]


def get_infrastructure_density_by_h3() -> list[dict[str, Any]]:
    query = text("""
        SELECT
            h3_index,
            COUNT(*) AS infra_count
        FROM safestreet.infrastructure_points
        WHERE h3_index IS NOT NULL
        GROUP BY h3_index
    """)
    with get_connection() as conn:
        result = conn.execute(query).mappings().all()
    return [dict(row) for row in result]


def get_h3_cells() -> list[dict[str, Any]]:
    query = text("""
        SELECT
            h3_index,
            resolution,
            crime_count,
            lighting_density,
            dist_nearest_lit,
            vulnerability_score,
            moran_cluster
        FROM safestreet.h3_cells
        ORDER BY vulnerability_score DESC
    """)
    with get_connection() as conn:
        result = conn.execute(query).mappings().all()
    return [dict(row) for row in result]
