from __future__ import annotations

from pathlib import Path

import pytest

from src.data.preprocessing import clean_crime_data
from src.spatial.h3_indexer import add_h3_column, geo_to_h3


def test_geo_to_h3() -> None:
    h3_index = geo_to_h3(-8.05, -34.88, 9)
    assert isinstance(h3_index, str)
    assert len(h3_index) > 0


def test_clean_crime_data(sample_crime_data) -> None:
    gdf = clean_crime_data(sample_crime_data)
    assert len(gdf) == 3
    assert all(gdf.geometry.notna())


def test_add_h3_column(sample_geodataframe) -> None:
    gdf = add_h3_column(sample_geodataframe, resolution=9)
    assert "h3_index" in gdf.columns
    assert all(gdf["h3_index"].notna())
