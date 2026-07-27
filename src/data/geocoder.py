from __future__ import annotations

import json
from pathlib import Path

import osmnx as ox
import pandas as pd
from loguru import logger

_CACHE_DIR = Path("data/external")


def geocode_bairros(
    city_osm_name: str,
    city_key: str,
    force_refresh: bool = False,
) -> dict[str, tuple[float, float]]:
    cache_file = _CACHE_DIR / f"bairros_{city_key}_centroides.json"

    if cache_file.exists() and not force_refresh:
        logger.info("Carregando centroides de {} do cache", city_key)
        with open(cache_file) as f:
            data = json.load(f)
        return {k.lower(): tuple(v) for k, v in data.items()}

    logger.info("Geocodificando bairros de '{}' via OSMnx...", city_osm_name)
    tags = {"admin_level": "10"}
    try:
        gdf = ox.features_from_place(city_osm_name, tags=tags)
    except Exception as e:
        logger.warning("Erro ao geocodificar bairros: {}", e)
        return {}

    gdf = gdf[gdf.geometry.notna()]

    centroids: dict[str, tuple[float, float]] = {}
    for _, row in gdf.iterrows():
        name = row.get("name")
        if name and row.geometry is not None and not row.geometry.is_empty:
            centroid = row.geometry.centroid
            centroids[str(name).lower()] = (centroid.y, centroid.x)

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(centroids, f, ensure_ascii=False, indent=2)

    logger.info("Centroides de {} bairros geocodificados para {}", len(centroids), city_key)
    return centroids


def assign_coordinates_from_bairros(
    df: pd.DataFrame,
    bairro_column: str = "bairro",
    centroids: dict[str, tuple[float, float]] | None = None,
) -> pd.DataFrame:
    if centroids is None:
        return df

    df = df.copy()
    df["latitude"] = df[bairro_column].str.lower().map(lambda b: centroids.get(b, (None, None))[0])
    df["longitude"] = df[bairro_column].str.lower().map(lambda b: centroids.get(b, (None, None))[1])

    matched = df["latitude"].notna().sum()
    total = len(df)
    logger.info(
        "Coordenadas atribuidas: {}/{} registros ({:.1f}%)",
        matched,
        total,
        (matched / total * 100) if total > 0 else 0,
    )

    unmatched = set(df.loc[df["latitude"].isna(), bairro_column].unique())
    if unmatched:
        logger.warning("Bairros nao geocodificados: {}", unmatched)

    return df
