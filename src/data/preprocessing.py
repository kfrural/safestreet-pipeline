from __future__ import annotations

from typing import Any

import pandas as pd
from geopandas import GeoDataFrame
from loguru import logger
from shapely.geometry import Point

from src.utils.validators import filter_nighttime_crimes, filter_valid_natures


def clean_crime_data(
    df: pd.DataFrame,
    time_column: str = "horario",
    nature_column: str = "natureza",
    lat_column: str = "latitude",
    lon_column: str = "longitude",
) -> GeoDataFrame:
    logger.info("Iniciando limpeza dos dados criminais ({} registros)", len(df))

    df = filter_nighttime_crimes(df, time_column)
    logger.info("Após filtro noturno: {} registros", len(df))

    df = filter_valid_natures(df, nature_column)
    logger.info("Após filtro de naturezas: {} registros", len(df))

    df = df.dropna(subset=[lat_column, lon_column])
    df = df[(df[lat_column].between(-33.75, 5.25)) & (df[lon_column].between(-73.98, -34.79))]

    geometry = [
        Point(xy) for xy in zip(df[lon_column], df[lat_column])
    ]
    gdf = GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    logger.info("GeoDataFrame criado com {} pontos", len(gdf))
    return gdf


def aggregate_by_hour(df: pd.DataFrame, time_column: str = "horario") -> pd.DataFrame:
    df = df.copy()
    df["hour"] = pd.to_datetime(df[time_column], format="%H:%M", errors="coerce").dt.hour
    return df.groupby("hour").size().reset_index(name="count")
