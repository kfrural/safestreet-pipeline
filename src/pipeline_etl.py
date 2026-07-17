from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from loguru import logger

from src.config import CITIES, get_city, settings
from src.utils.classifiers import classify_crime
from src.utils.logger import setup_logger


def run_pipeline(city_key: str = "recife", crime_file: Path | None = None) -> None:
    from src.data.geocoder import assign_coordinates_from_bairros, geocode_bairros
    from src.data.osm_infra import fetch_all_infrastructure
    from src.db.connection import check_connection, engine
    from src.db.models import Base
    from src.db.queries import (
        get_h3_cells,
        insert_crime_records_batch,
        insert_infrastructure_batch,
    )
    from src.spatial.h3_indexer import add_h3_column
    from src.spatial.postgis_ops import (
        calculate_moran_clusters,
        calculate_nearest_infra_distance,
        calculate_vulnerability_score,
        create_spatial_indexes,
        populate_h3_cells,
    )

    city = get_city(city_key)

    logger.info("=" * 60)
    logger.info("SafeStreet Pipeline ETL - Cidade: {} ({})", city.name, city_key)
    logger.info("=" * 60)

    if not check_connection():
        raise ConnectionError("Nao foi possivel conectar ao banco PostGIS")

    Base.metadata.create_all(engine)

    raw_df = _load_city_data(city_key, city, crime_file)

    centroids = geocode_bairros(city.osm_name, city_key)

    has_lat = "latitude" in raw_df.columns and raw_df["latitude"].notna().any()
    has_bairro = "bairro" in raw_df.columns

    if not has_lat and has_bairro:
        raw_df = assign_coordinates_from_bairros(
            raw_df,
            centroids=centroids,
        )
        raw_df = raw_df.dropna(subset=["latitude", "longitude"])
        logger.info(
            "Geocodificacao por bairro concluida: {} registros",
            len(raw_df),
        )

    gdf = _clean_city_data(city_key, raw_df)
    gdf = add_h3_column(gdf, settings.h3_resolution)

    crime_records = []
    cols = {c.lower(): c for c in gdf.columns}

    for idx, (_, row) in enumerate(gdf.iterrows()):
        proto = str(
            row.get(cols.get("protocolo", ""), "")
            or row.get(cols.get("num_bo", ""), "")
            or row.get(cols.get("id", ""), "")
        )
        if not proto or proto == "nan":
            proto = f"{city_key}_{idx}"
        else:
            proto = f"{proto}_{idx}"
        natureza_val = str(
            row.get(cols.get("tipo", ""), "") or row.get(cols.get("natureza", ""), "crime")
        )
        crime_records.append(
            {
                "occurrence_id": proto,
                "nature": natureza_val,
                "crime_category": classify_crime(natureza_val),
                "date": row.get(cols.get("data", ""), None),
                "time": str(
                    row.get(cols.get("horario", ""), "")
                    or row.get(cols.get("hora", ""), "")
                    or row.get(cols.get("hora_ocorrencia", ""), "")
                )[:5],
                "city": city_key,
                "neighborhood": str(row.get(cols.get("bairro", ""), "")),
                "lat": row.geometry.y,
                "lon": row.geometry.x,
                "h3_index": row.get("h3_index"),
            }
        )

    insert_crime_records_batch(crime_records)
    logger.info(
        "Inseridos {} registros criminais para {}",
        len(crime_records),
        city_key,
    )

    infra_data = fetch_all_infrastructure(city.osm_name)

    nightlife_data = None
    try:
        from src.data.nightlife import fetch_nightlife_pois

        nightlife_data = fetch_nightlife_pois(city.osm_name)
    except Exception as e:
        logger.warning("Erro ao buscar nightlife: {}", e)

    infra_records = []
    for infra_type, gdf_infra in infra_data.items():
        if gdf_infra.empty:
            continue
        gdf_crs = gdf_infra.to_crs("EPSG:4326")
        gdf_crs["geometry"] = gdf_crs["geometry"].centroid
        gdf_h3 = add_h3_column(gdf_crs, settings.h3_resolution)
        for infra_idx, (_, row) in enumerate(gdf_h3.iterrows()):
            osm_id = str(row.get("osmid", ""))
            if not osm_id or osm_id == "nan":
                osm_id = f"{city_key}_{infra_type}_{infra_idx}"
            infra_records.append(
                {
                    "osm_id": osm_id,
                    "infra_type": infra_type,
                    "city": city_key,
                    "lat": row.geometry.y,
                    "lon": row.geometry.x,
                    "h3_index": row.get("h3_index"),
                }
            )

    if nightlife_data:
        for poi_type, gdf_poi in nightlife_data.items():
            if gdf_poi.empty:
                continue
            gdf_crs = gdf_poi.to_crs("EPSG:4326")
            gdf_crs["geometry"] = gdf_crs["geometry"].centroid
            gdf_h3 = add_h3_column(gdf_crs, settings.h3_resolution)
            for idx_p, (_, row) in enumerate(gdf_h3.iterrows()):
                infra_records.append(
                    {
                        "osm_id": f"{city_key}_{poi_type}_{idx_p}",
                        "infra_type": poi_type,
                        "city": city_key,
                        "lat": row.geometry.y,
                        "lon": row.geometry.x,
                        "h3_index": row.get("h3_index"),
                    }
                )

    insert_infrastructure_batch(infra_records)
    logger.info(
        "Inseridos {} pontos de infraestrutura para {}",
        len(infra_records),
        city_key,
    )

    _fetch_and_store_weather(city, city_key, gdf)

    create_spatial_indexes()
    populate_h3_cells(city_key, settings.h3_resolution)
    calculate_nearest_infra_distance(city_key)
    calculate_vulnerability_score(city_key)
    calculate_moran_clusters(city_key)

    output_dir = Path(settings.pipeline_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cells = get_h3_cells(city=city_key)
    df_out = pd.DataFrame(cells)
    output_path = output_dir / f"h3_analysis_results_{city_key}.csv"
    df_out.to_csv(output_path, index=False)
    logger.info("Resultados exportados para {}", output_path)

    logger.info(
        "Pipeline ETL concluido com sucesso para {}!",
        city_key,
    )
    logger.info("=" * 60)


def _load_city_data(
    city_key: str,
    city_config: object,
    crime_file: Path | None = None,
) -> pd.DataFrame:
    from src.data.ingestion import load_dataframe

    if crime_file:
        return load_dataframe(crime_file)

    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    if city_config.data_source == "ssp_sp":
        csv_path = raw_dir / "ssp_sp_crimes.csv"
        if csv_path.exists():
            return load_dataframe(csv_path)

        labcidade_path = raw_dir / "mdip_2013_19.csv"
        if labcidade_path.exists():
            return load_dataframe(labcidade_path, sep=";", encoding="latin-1")

        xlsx_files = sorted(raw_dir.glob("CelularesSubtraidos_*.xlsx"))
        if xlsx_files:
            frames = []
            for f in xlsx_files:
                try:
                    frames.append(load_dataframe(f))
                except Exception as e:
                    logger.warning("Erro ao carregar {}: {}", f, e)
            if frames:
                return pd.concat(frames, ignore_index=True)

        raise FileNotFoundError(
            f"Nenhum arquivo SSP-SP encontrado em {raw_dir}. "
            "Execute: python scripts/download_ssp_sp.py"
        )

    pattern = city_config.crime_file_pattern
    csv_files = sorted(
        raw_dir.glob(pattern.replace("{year}", "*")),
    )
    if csv_files:
        return load_dataframe(csv_files[-1])

    raise FileNotFoundError(
        f"Nenhum dado encontrado para {city_key} em {raw_dir}. "
        "Execute o script de download correspondente.",
    )


def _clean_city_data(
    city_key: str,
    df: pd.DataFrame,
) -> object:
    from src.data.preprocessing import (
        clean_accident_data,
        clean_crime_data_sp,
        clean_generic_crime_data,
    )

    if city_key == "recife":
        return clean_accident_data(df)
    elif city_key == "sao-paulo":
        return clean_crime_data_sp(df)
    else:
        return clean_generic_crime_data(df)


def _fetch_and_store_weather(
    city_config: object,
    city_key: str,
    crime_gdf: object,
) -> None:
    from src.data.weather import (
        compute_weather_stats,
        fetch_weather_data,
        match_crime_weather,
    )

    try:
        date_cols = [
            c for c in crime_gdf.columns
            if c.lower() in ("date", "data", "data_bo", "data_hora_bo")
        ]
        if not date_cols:
            logger.warning("Sem coluna de data no GeoDataFrame para clima")
            return

        dates = pd.to_datetime(
            crime_gdf[date_cols[0]], errors="coerce"
        ).dropna()

        if dates.empty:
            logger.warning("Sem datas validas para buscar clima")
            return

        start = dates.min().strftime("%Y-%m-%d")
        end = dates.max().strftime("%Y-%m-%d")

        weather_dir = Path("data/external")
        weather_df = fetch_weather_data(
            latitude=city_config.center_lat,
            longitude=city_config.center_lon,
            start_date=start,
            end_date=end,
            cache_dir=weather_dir,
        )

        if not weather_df.empty:
            temp_df = crime_gdf.copy()
            temp_df["date"] = temp_df[date_cols[0]]
            crime_with_weather = match_crime_weather(temp_df, weather_df)
            stats = compute_weather_stats(crime_with_weather)
            if stats:
                weather_file = weather_dir / f"weather_stats_{city_key}.json"
                import json

                weather_file.write_text(json.dumps(stats, default=str))
                logger.info(
                    "Estatisticas climaticas salvas: {}",
                    weather_file,
                )
    except Exception as e:
        logger.warning("Erro ao processar dados climaticos: {}", e)


def run_all_cities(
    crime_files: dict[str, Path] | None = None,
) -> None:
    crime_files = crime_files or {}
    for city_key in CITIES:
        try:
            cf = crime_files.get(city_key)
            run_pipeline(city_key, crime_file=cf)
        except Exception as e:
            logger.error("Erro ao processar {}: {}", city_key, e)


def main() -> None:
    setup_logger(
        level="DEBUG" if "--debug" in sys.argv else "INFO",
    )

    args = sys.argv[1:]
    city = "recife"
    crime_file = None

    for i, arg in enumerate(args):
        if arg == "--city" and i + 1 < len(args):
            city = args[i + 1]
        if arg == "--input" and i + 1 < len(args):
            crime_file = Path(args[i + 1])
        if arg == "--all":
            run_all_cities()
            return

    run_pipeline(city, crime_file)


if __name__ == "__main__":
    main()
