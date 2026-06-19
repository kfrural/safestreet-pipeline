from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from src.config import settings
from src.utils.logger import setup_logger


def run_pipeline(crime_file: Path | None = None) -> None:
    logger.info("=" * 60)
    logger.info("SafeStreet Pipeline ETL - Iniciando")
    logger.info("=" * 60)

    from src.data.ingestion import load_dataframe
    from src.data.osm_extractor import fetch_lighting_infrastructure
    from src.data.preprocessing import clean_crime_data
    from src.db.connection import check_connection, engine
    from src.db.models import Base
    from src.db.queries import (
        insert_crime_records_batch,
        insert_infrastructure_batch,
    )
    from src.spatial.h3_indexer import add_h3_column
    from src.spatial.postgis_ops import (
        calculate_lighting_density,
        calculate_nearest_light_distance,
        create_spatial_indexes,
    )

    if not check_connection():
        raise ConnectionError("Não foi possível conectar ao banco PostGIS")

    Base.metadata.create_all(engine)

    crime_path = crime_file or settings.pipeline_crime_file
    raw_df = load_dataframe(crime_path)
    gdf = clean_crime_data(raw_df)
    gdf = add_h3_column(gdf, settings.h3_resolution)

    gdf_lighting = fetch_lighting_infrastructure(settings.osm_city_name)
    gdf_lighting = gdf_lighting.to_crs("EPSG:4326")
    gdf_lighting = add_h3_column(gdf_lighting, settings.h3_resolution)

    crime_records = []
    for _, row in gdf.iterrows():
        crime_records.append({
            "occurrence_id": str(row.get("id", "")),
            "nature": row.get("natureza", ""),
            "date": row.get("data", None),
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
    calculate_nearest_light_distance()

    output_dir = Path(settings.pipeline_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    from src.db.queries import get_h3_cells
    cells = get_h3_cells()

    import pandas as pd
    df_out = pd.DataFrame(cells)
    output_path = output_dir / "h3_analysis_results.csv"
    df_out.to_csv(output_path, index=False)
    logger.info("Resultados exportados para {}", output_path)

    logger.info("Pipeline ETL concluído com sucesso!")
    logger.info("=" * 60)


def main() -> None:
    setup_logger(level="DEBUG" if "--debug" in sys.argv else "INFO")
    crime_file = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--input" and i + 1 < len(sys.argv[1:]):
            crime_file = Path(sys.argv[i + 2])
    run_pipeline(crime_file)


if __name__ == "__main__":
    main()
