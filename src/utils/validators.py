from __future__ import annotations

from datetime import time
from typing import Any

import pandas as pd
from geopandas import GeoDataFrame
from shapely.geometry.base import BaseGeometry


NIGHT_START = time(18, 0)
NIGHT_END = time(6, 0)

VALID_CRIME_NATURES: set[str] = {
    "roubo a pedestre",
    "furto a pedestre",
    "roubo de celular",
    "furto de celular",
    "roubo de veículo",
    "furto de veículo",
}


def is_nighttime(occurrence_time: time) -> bool:
    return occurrence_time >= NIGHT_START or occurrence_time < NIGHT_END


def filter_nighttime_crimes(df: pd.DataFrame, time_column: str) -> pd.DataFrame:
    df = df.copy()
    df[time_column] = pd.to_datetime(df[time_column], format="%H:%M", errors="coerce").dt.time
    mask = df[time_column].apply(is_nighttime)
    return df.loc[mask].reset_index(drop=True)


def filter_valid_natures(
    df: pd.DataFrame,
    nature_column: str,
    valid_natures: set[str] | None = None,
) -> pd.DataFrame:
    valid = valid_natures or VALID_CRIME_NATURES
    df = df.copy()
    df[nature_column] = df[nature_column].str.strip().str.lower()
    return df.loc[df[nature_column].isin(valid)].reset_index(drop=True)


def validate_geodataframe(gdf: GeoDataFrame) -> bool:
    required = {"geometry"}
    if not required.issubset(gdf.columns):
        return False
    if gdf.empty:
        return False
    if not all(isinstance(geom, BaseGeometry) for geom in gdf.geometry):
        return False
    if gdf.geometry.isna().any():
        return False
    if gdf.geometry.is_empty.any():
        return False
    return True


def validate_schema(df: pd.DataFrame, expected_schema: dict[str, type]) -> list[str]:
    errors: list[str] = []
    for col, dtype in expected_schema.items():
        if col not in df.columns:
            errors.append(f"Coluna obrigatória '{col}' não encontrada.")
        elif not pd.api.types.is_dtype_equal(df[col].dtype, dtype):
            errors.append(
                f"Coluna '{col}': esperado {dtype.__name__}, "
                f"obtido {df[col].dtype.name}."
            )
    return errors
