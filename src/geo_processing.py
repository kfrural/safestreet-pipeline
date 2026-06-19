from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from src.config import settings
from src.data.ingestion import load_dataframe
from src.data.osm_extractor import fetch_lighting_infrastructure
from src.data.preprocessing import clean_crime_data
from src.db.connection import check_connection, engine
from src.db.models import Base
from src.db.queries import (
    get_crime_density_by_h3,
    get_h3_cells,
    get_infrastructure_density_by_h3,
    insert_crime_records_batch,
    insert_infrastructure_batch,
)
from src.spatial.h3_indexer import add_h3_column
from src.spatial.postgis_ops import (
    calculate_lighting_density,
    create_spatial_indexes,
)


def run_geo_processing(crime_file: Path | None = None) -> None:
    logger.info("=" * 60)
    logger.info("SafeStreet - Módulo de Processamento Geoespacial")
    logger.info("=" * 60)

    crime_path = crime_file or settings.pipeline_crime_file

    if not check_connection():
        raise ConnectionError("Não foi possível conectar ao banco PostGIS")

    Base.metadata.create_all(engine)

    logger.info("Carregando dados criminais de {}", crime_path)
    raw_df = load_dataframe(crime_path)
    logger.info("Total de registros brutos: {}", len(raw_df))

    gdf_crimes = clean_crime_data(raw_df)
    gdf_crimes = add_h3_column(gdf_crimes, settings.h3_resolution)
    gdf_crimes = gdf_crimes.to_crs("EPSG:4326")

    logger.info("Buscando infraestrutura de iluminação do OpenStreetMap")
    gdf_lighting = fetch_lighting_infrastructure(settings.osm_city_name)
    gdf_lighting = gdf_lighting.to_crs("EPSG:4326")
    gdf_lighting = add_h3_column(gdf_lighting, settings.h3_resolution)

    crime_records = []
    for _, row in gdf_crimes.iterrows():
        crime_records.append({
            "occurrence_id": str(row.get("id", "")),
            "nature": row.get("natureza", ""),
            "date": row.get("data", pd.Timestamp.now()),
            "time": str(row.get("horario", "")),
            "lat": row.geometry.y,
            "lon": row.geometry.x,
            "h3_index": row.get("h3_index"),
        })

    infra_records = []
    for _, row in gdf_lighting.iterrows():
        infra_records.append({
            "osm_id": str(row.get("osmid", "")),
            "infra_type": "street_lamp",
            "lat": row.geometry.y,
            "lon": row.geometry.x,
            "h3_index": row.get("h3_index"),
        })

    insert_crime_records_batch(crime_records)
    insert_infrastructure_batch(infra_records)

    create_spatial_indexes()
    calculate_lighting_density()

    logger.info("Processamento geoespacial concluído com sucesso")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_geo_processing()
