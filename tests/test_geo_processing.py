from __future__ import annotations

from src.config import get_city, list_cities
from src.data.preprocessing import clean_crime_data_sp
from src.spatial.h3_indexer import add_h3_column, geo_to_h3


def test_geo_to_h3() -> None:
    h3_index = geo_to_h3(-23.55, -46.63, 9)
    assert isinstance(h3_index, str)
    assert len(h3_index) > 0


def test_clean_crime_data_sp() -> None:
    import pandas as pd

    df = pd.DataFrame(
        {
            "id": ["1", "2", "3", "4", "5"],
            "natureza": [
                "roubo",
                "furto",
                "homicidio",
                "roubo",
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
    gdf = clean_crime_data_sp(df)
    assert len(gdf) == 3
    assert all(gdf.geometry.notna())


def test_add_h3_column(sample_geodataframe) -> None:
    gdf = add_h3_column(sample_geodataframe, resolution=9)
    assert "h3_index" in gdf.columns
    assert all(gdf["h3_index"].notna())


def test_city_config_saopaulo() -> None:
    city = get_city("sao-paulo")
    assert city.name == "Sao Paulo"
    assert city.state == "SP"
    assert city.data_source == "ssp_sp"


def test_list_cities() -> None:
    cities = list_cities()
    assert "sao-paulo" in cities
    assert len(cities) == 1


def test_get_city_invalid() -> None:
    import pytest

    with pytest.raises(ValueError, match="nao encontrada"):
        get_city("invalid-city")
