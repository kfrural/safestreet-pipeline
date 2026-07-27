from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import requests
from loguru import logger
from shapely.geometry import Point

GEOSAMPA_WFS = "https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs"
LAYER = "geoportal:iluminacao_publica"
BATCH_SIZE = 10000
MAX_POINTS = 100000


def fetch_lighting_from_geosampa(
    cache_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    cache_path = cache_dir / "lighting_geosampa.parquet" if cache_dir else None

    if cache_path and cache_path.exists():
        logger.info("Carregando iluminacao GeoSampa do cache: {}", cache_path)
        gdf = gpd.read_parquet(cache_path)
        if gdf.crs and str(gdf.crs) != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        return gdf

    all_coords = []
    start_index = 0

    logger.info(
        "Iniciando download de iluminacao via WFS GeoSampa (max ~{}pts)...",
        MAX_POINTS,
    )

    while start_index < MAX_POINTS:
        current_batch = min(BATCH_SIZE, MAX_POINTS - start_index)
        params = {
            "service": "WFS",
            "version": "1.1.0",
            "request": "GetFeature",
            "typeName": LAYER,
            "outputFormat": "application/json",
            "maxFeatures": str(current_batch),
            "startIndex": str(start_index),
        }

        try:
            resp = requests.get(GEOSAMPA_WFS, params=params, timeout=300)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(
                "Erro WFS GeoSampa (offset {}): {}", start_index, e,
            )
            break

        features = data.get("features", [])
        if not features:
            break

        for feat in features:
            coords = feat.get("geometry", {}).get("coordinates")
            if coords and len(coords) >= 2:
                all_coords.append(coords[:2])

        total = data.get("totalFeatures", "?")
        logger.info(
            "Iluminacao: {}/{} pontos (total server: {})",
            len(all_coords),
            start_index + len(features),
            total,
        )

        if len(features) < BATCH_SIZE:
            break

        start_index += BATCH_SIZE

    if not all_coords:
        logger.warning("Nenhum ponto de iluminacao obtido do GeoSampa")
        return gpd.GeoDataFrame()

    logger.info(
        "Total de {} pontos brutos, convertendo UTM->WGS84...",
        len(all_coords),
    )

    geometry = [Point(xy) for xy in all_coords]
    gdf_utm = gpd.GeoDataFrame(
        geometry=geometry,
        crs="EPSG:31983",
    )
    gdf = gdf_utm.to_crs("EPSG:4326")

    lons = gdf.geometry.x.values
    lats = gdf.geometry.y.values
    sp_mask = (
        (lons >= -46.90) & (lons <= -46.30)
        & (lats >= -23.85) & (lats <= -23.30)
    )
    gdf = gdf[sp_mask].reset_index(drop=True)
    gdf["source"] = "geosampa"
    gdf["infra_type"] = "street_lamp"
    logger.info(
        "Filtrado para SP: {} de {} pontos", len(gdf), len(all_coords),
    )

    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            gdf.to_parquet(cache_path, index=False)
            logger.info("Cache iluminacao salvo: {}", cache_path)
        except Exception as e:
            logger.warning("Erro ao salvar cache parquet: {}", e)
            csv_path = cache_path.with_suffix(".csv")
            gdf.to_csv(csv_path, index=False)
            logger.info("Cache iluminacao salvo (CSV): {}", csv_path)

    return gdf


def count_lighting_by_h3(
    lighting_gdf: gpd.GeoDataFrame,
    h3_cells: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    if lighting_gdf.empty or h3_cells.empty:
        return h3_cells

    from src.spatial.h3_indexer import add_h3_column

    lighting_h3 = add_h3_column(lighting_gdf, resolution=9)
    counts = lighting_h3.groupby("h3_index").size().reset_index(
        name="lighting_official_count",
    )

    result = h3_cells.merge(counts, on="h3_index", how="left")
    result["lighting_official_count"] = (
        result["lighting_official_count"].fillna(0).astype(int)
    )

    logger.info(
        "Iluminacao oficial: {} celulas H3 com pontos",
        (result["lighting_official_count"] > 0).sum(),
    )

    return result
