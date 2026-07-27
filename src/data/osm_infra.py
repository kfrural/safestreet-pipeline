from __future__ import annotations

import time
from typing import Any

import osmnx as ox
from geopandas import GeoDataFrame
from loguru import logger

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api",
    "https://overpass.kumi.systems/api",
]
OVERPASS_QUERY_TIMEOUTS = [300, 600]
HTTP_TIMEOUT = 600


def fetch_infrastructure(
    city_name: str,
    infra_type: str,
    tags: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> GeoDataFrame:
    if tags is None:
        tags = _DEFAULT_TAGS.get(infra_type)
    if tags is None:
        raise ValueError(f"Tipo de infraestrutura desconhecido: {infra_type}")

    if isinstance(tags, list):
        frames = []
        for tag in tags:
            gdf = fetch_infrastructure(city_name, infra_type, tags=tag)
            if not gdf.empty:
                frames.append(gdf)
        if frames:
            import pandas as pd
            result = pd.concat(frames, ignore_index=True)
            if "osmid" in result.columns:
                result = result.drop_duplicates(subset=["osmid"])
            logger.info(
                "Total de {} geometrias de {} (OR de {} tags)",
                len(result),
                infra_type,
                len(tags),
            )
            return result
        return GeoDataFrame()

    logger.info("Buscando {} em '{}'", infra_type, city_name)

    orig_url = ox.settings.overpass_url
    orig_timeout = ox.settings.requests_timeout

    for attempt, endpoint in enumerate(OVERPASS_ENDPOINTS):
        query_timeout = OVERPASS_QUERY_TIMEOUTS[
            min(attempt, len(OVERPASS_QUERY_TIMEOUTS) - 1)
        ]
        ox.settings.overpass_url = endpoint
        ox.settings.requests_timeout = HTTP_TIMEOUT
        ox.settings.overpass_settings = (
            "[out:json][timeout:" + str(query_timeout) + "]{maxsize}"
        )
        try:
            gdf = ox.features_from_place(city_name, tags=tags)
            gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
            logger.info("Encontradas {} geometrias de {}", len(gdf), infra_type)
            return gdf
        except Exception as e:
            logger.warning(
                "Tentativa {}/{} falhou para {} (endpoint={}): {}",
                attempt + 1,
                len(OVERPASS_ENDPOINTS),
                infra_type,
                endpoint,
                e,
            )
            if attempt < len(OVERPASS_ENDPOINTS) - 1:
                time.sleep(10)
        finally:
            ox.settings.overpass_url = orig_url
            ox.settings.requests_timeout = orig_timeout

    logger.warning("Todas as tentativas falharam para {}", infra_type)
    return GeoDataFrame()


def fetch_all_infrastructure(city_name: str) -> dict[str, GeoDataFrame]:
    result: dict[str, GeoDataFrame] = {}
    for infra_type in _DEFAULT_TAGS:
        result[infra_type] = fetch_infrastructure(city_name, infra_type)
    return result


_DEFAULT_TAGS: dict[str, dict[str, Any]] = {
    "street_lamp": {"highway": "street_lamp"},
    "bus_stop": [
        {"highway": "bus_stop"},
        {"public_transport": "stop_position"},
    ],
    "metro_station": {
        "railway": "station",
        "station": "subway",
    },
    "camera": {
        "man_made": "surveillance",
        "surveillance": "public",
    },
}
