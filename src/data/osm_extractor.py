from __future__ import annotations

from typing import Any

import osmnx as ox
from geopandas import GeoDataFrame
from loguru import logger


def fetch_lighting_infrastructure(
    city_name: str,
    tags: dict[str, Any] | None = None,
) -> GeoDataFrame:
    if tags is None:
        tags = {"highway": "street_lamp"}
    logger.info("Buscando pontos de iluminação em '{}'", city_name)
    gdf = ox.features_from_place(city_name, tags=tags)
    logger.info("Encontradas {} geometrias de iluminação", len(gdf))
    return gdf


def fetch_public_transport_stops(city_name: str) -> GeoDataFrame:
    tags = {"highway": "bus_stop", "public_transport": "stop_position"}
    logger.info("Buscando paradas de transporte público em '{}'", city_name)
    gdf = ox.features_from_place(city_name, tags=tags)
    logger.info("Encontradas {} paradas de transporte", len(gdf))
    return gdf


def fetch_road_network(city_name: str, network_type: str = "drive") -> GeoDataFrame:
    logger.info("Buscando malha viária em '{}' (tipo: {})", city_name, network_type)
    graph = ox.graph_from_place(city_name, network_type=network_type)
    edges = ox.graph_to_gdfs(graph, nodes=False, edges=True)
    logger.info("Extraídos {} segmentos de via", len(edges))
    return edges
