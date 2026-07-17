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
            "latitude": [-8.05, -8.06, -8.07, -8.08, -8.09],
            "longitude": [-34.88, -34.89, -34.90, -34.91, -34.92],
        }
    )


@pytest.fixture
def sample_accident_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Protocolo": ["1001", "1002", "1003", "1004", "1005"],
            "data": ["2024-06-01", "2024-06-02", "2024-06-03", "2024-06-04", "2024-06-05"],
            "hora": ["22:30:00", "03:15:00", "14:00:00", "20:00:00", "10:00:00"],
            "natureza": ["COM VITIMA", "COM VITIMA", "SEM VITIMA", "COM VITIMA", "SEM VITIMA"],
            "bairro": ["BOA VIAGEM", "ARRUDA", "CASA AMARELA", "BOA VIAGEM", "AFLITOS"],
            "tipo": ["COLISAO", "ATROPELAMENTO", "COLISAO", "COLISAO LATERAL", "COLISAO"],
            "vitimas": ["1,0", "2,0", "0,0", "1,0", "0,0"],
            "vitimasfatais": ["0,0", "0,0", "0,0", "0,0", "0,0"],
            "latitude": [-8.05, -8.06, None, -8.08, -8.09],
            "longitude": [-34.88, -34.89, None, -34.91, -34.92],
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
            Point(-34.88, -8.05),
            Point(-34.89, -8.06),
            Point(-34.90, -8.07),
        ],
        crs="EPSG:4326",
    )
    return gdf


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    output_dir = tmp_path / "processed"
    output_dir.mkdir()
    return output_dir
