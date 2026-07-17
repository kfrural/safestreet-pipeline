from __future__ import annotations

from typing import Any

import osmnx as ox
from geopandas import GeoDataFrame
from loguru import logger


def fetch_infrastructure(
    city_name: str,
    infra_type: str,
    tags: dict[str, Any] | None = None,
) -> GeoDataFrame:
    if tags is None:
        tags = _DEFAULT_TAGS.get(infra_type)
    if tags is None:
        raise ValueError(f"Tipo de infraestrutura desconhecido: {infra_type}")

    logger.info("Buscando {} em '{}'", infra_type, city_name)
    try:
        gdf = ox.features_from_place(city_name, tags=tags)
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
        logger.info("Encontradas {} geometrias de {}", len(gdf), infra_type)
        return gdf
    except Exception as e:
        logger.warning("Erro ao buscar {}: {}", infra_type, e)
        return GeoDataFrame()


def fetch_all_infrastructure(city_name: str) -> dict[str, GeoDataFrame]:
    result: dict[str, GeoDataFrame] = {}
    for infra_type in _DEFAULT_TAGS:
        result[infra_type] = fetch_infrastructure(city_name, infra_type)
    return result


_DEFAULT_TAGS: dict[str, dict[str, Any]] = {
    "street_lamp": {"highway": "street_lamp"},
    "bus_stop": {
        "highway": "bus_stop",
        "public_transport": "stop_position",
    },
    "metro_station": {
        "railway": "station",
        "station": "subway",
    },
    "camera": {
        "man_made": "surveillance",
        "surveillance": "public",
    },
}
