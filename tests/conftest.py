from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from geopandas import GeoDataFrame
from shapely.geometry import Point


@pytest.fixture
def sample_crime_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": ["1", "2", "3", "4", "5"],
            "natureza": [
                "roubo a pedestre",
                "furto de celular",
                "homicidio",
                "roubo a pedestre",
                "estelionato",
            ],
            "data": pd.to_datetime(
                [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                ]
            ),
            "horario": ["22:30", "03:15", "14:00", "20:00", "10:00"],
            "latitude": [-23.55, -23.56, -23.57, -23.58, -23.59],
            "longitude": [-46.63, -46.64, -46.65, -46.66, -46.67],
        }
    )


@pytest.fixture
def sample_geodataframe() -> GeoDataFrame:
    gdf = GeoDataFrame(
        {
            "id": [1, 2, 3],
            "natureza": ["roubo", "furto", "roubo"],
            "h3_index": ["89a1b2c3d4e5fff", "89a1b2c3d4e6fff", "89a1b2c3d4e7fff"],
        },
        geometry=[
            Point(-46.63, -23.55),
            Point(-46.64, -23.56),
            Point(-46.65, -23.57),
        ],
        crs="EPSG:4326",
    )
    return gdf


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    output_dir = tmp_path / "processed"
    output_dir.mkdir()
    return output_dir
