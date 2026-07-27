from __future__ import annotations

import pandas as pd
from geopandas import GeoDataFrame
from loguru import logger
from shapely.geometry import Point

from src.utils.validators import filter_nighttime_crimes


def clean_accident_data(
    df: pd.DataFrame,
    time_column: str = "hora",
    lat_column: str = "latitude",
    lon_column: str = "longitude",
) -> GeoDataFrame:
    logger.info("Limpando dados de acidentes ({} registros)", len(df))

    df = df.copy()

    if time_column in df.columns:
        df[time_column] = df[time_column].astype(str).str[:5]
        df = filter_nighttime_crimes(df, time_column)
        logger.info("Apos filtro noturno: {} registros", len(df))

    if "vitimas" in df.columns:
        df["vitimas"] = (
            df["vitimas"].astype(str).str.replace(",", ".", regex=False).str.strip().astype(float)
        )
        df = df[df["vitimas"] > 0].reset_index(drop=True)
        logger.info("Apos filtro de victimas: {} registros", len(df))

    df = df.dropna(subset=[lat_column, lon_column])
    df = df[(df[lat_column].between(-33.75, 5.25)) & (df[lon_column].between(-73.98, -34.79))]

    geometry = [Point(xy) for xy in zip(df[lon_column], df[lat_column])]
    gdf = GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    logger.info("GeoDataFrame criado com {} pontos", len(gdf))
    return gdf


def clean_crime_data_sp(
    df: pd.DataFrame,
    time_column: str = "horario",
    lat_column: str | None = None,
    lon_column: str | None = None,
) -> GeoDataFrame:
    logger.info("Limpando dados SSP-SP ({} registros)", len(df))

    df = df.copy()

    if lat_column is None:
        lat_candidates = [c for c in df.columns if c.lower() in ("latitude", "lat")]
        lat_column = lat_candidates[0] if lat_candidates else "latitude"
    if lon_column is None:
        lon_candidates = [c for c in df.columns if c.lower() in ("longitude", "lon")]
        lon_column = lon_candidates[0] if lon_candidates else "longitude"

    if time_column not in df.columns:
        time_candidates = [c for c in df.columns if "hora" in c.lower() and "ocorr" in c.lower()]
        if time_candidates:
            df["horario"] = df[time_candidates[0]].astype(str).str[:5]
            time_column = "horario"

    if "natureza" not in df.columns:
        natureza_candidates = [
            c for c in df.columns if c.lower() in ("rubrica", "natureza_apurada", "natureza")
        ]
        if natureza_candidates:
            df["natureza"] = df[natureza_candidates[0]].astype(str)

    if time_column in df.columns:
        df[time_column] = df[time_column].astype(str).str[:5]
        df = filter_nighttime_crimes(df, time_column)
        logger.info("Apos filtro noturno: {} registros", len(df))

    df = df.dropna(subset=[lat_column, lon_column])
    df = df[df[lat_column].between(-24.5, -22.5) & df[lon_column].between(-47.5, -45.5)]

    if "natureza" in df.columns:
        df["natureza"] = df["natureza"].str.strip().str.lower()

    geometry = [Point(xy) for xy in zip(df[lon_column], df[lat_column])]
    gdf = GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    logger.info("GeoDataFrame SSP-SP criado com {} pontos", len(gdf))
    return gdf


def clean_generic_crime_data(
    df: pd.DataFrame,
    time_column: str = "horario",
    lat_column: str = "latitude",
    lon_column: str = "longitude",
) -> GeoDataFrame:
    logger.info("Limpando dados genericos ({} registros)", len(df))

    df = df.copy()

    if time_column in df.columns:
        df[time_column] = df[time_column].astype(str).str[:5]
        df = filter_nighttime_crimes(df, time_column)
        logger.info("Apos filtro noturno: {} registros", len(df))

    df = df.dropna(subset=[lat_column, lon_column])

    geometry = [Point(xy) for xy in zip(df[lon_column], df[lat_column])]
    gdf = GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    logger.info("GeoDataFrame generico criado com {} pontos", len(gdf))
    return gdf
