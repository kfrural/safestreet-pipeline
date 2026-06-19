from __future__ import annotations

import h3
import h3.api.basic_str as h3_basic
import numpy as np
from geopandas import GeoDataFrame
from loguru as logger
from shapely.geometry import Point


def geo_to_h3(lat: float, lon: float, resolution: int = 9) -> str:
    return h3_basic.geo_to_h3(lat, lon, resolution)


def add_h3_column(gdf: GeoDataFrame, resolution: int = 9) -> GeoDataFrame:
    logger.info("Indexando {} geometrias com H3 resolução {}", len(gdf), resolution)
    gdf = gdf.copy()
    gdf["h3_index"] = gdf.geometry.apply(
        lambda geom: geo_to_h3(geom.y, geom.x, resolution)
        if isinstance(geom, Point)
        else None
    )
    return gdf


def h3_to_polygon(h3_index: str) -> list[tuple[float, float]]:
    boundary = h3_basic.h3_to_geo_boundary(h3_index)
    return [(lng, lat) for lat, lng in boundary]


def create_h3_grid(
    bounds: tuple[float, float, float, float],
    resolution: int = 9,
) -> list[str]:
    min_lat, min_lon, max_lat, max_lon = bounds
    hex_set: set[str] = set()

    lat_steps = int(np.ceil((max_lat - min_lat) / 0.01))
    lon_steps = int(np.ceil((max_lon - min_lon) / 0.01))

    for i in range(lat_steps + 1):
        for j in range(lon_steps + 1):
            lat = min_lat + i * 0.01
            lon = min_lon + j * 0.01
            h3_index = geo_to_h3(lat, lon, resolution)
            hex_set.add(h3_index)

    logger.info("Grid H3 gerado: {} células na resolução {}", len(hex_set), resolution)
    return list(hex_set)
