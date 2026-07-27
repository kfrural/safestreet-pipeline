from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    postgres_host: str = Field("localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")
    postgres_db: str = Field("safestreet", alias="POSTGRES_DB")
    postgres_user: str = Field("safestreet", alias="POSTGRES_USER")
    postgres_password: str = Field("safestreet_pass", alias="POSTGRES_PASSWORD")

    overpass_api_url: str = Field(
        "https://overpass-api.de/api/interpreter",
        alias="OVERPASS_API_URL",
    )

    pipeline_output_dir: Path = Field(
        Path("data/processed"),
        alias="PIPELINE_OUTPUT_DIR",
    )
    external_data_dir: Path = Field(
        Path("data/external"),
        alias="EXTERNAL_DATA_DIR",
    )
    h3_resolution: int = Field(9, alias="H3_RESOLUTION", ge=0, le=15)

    dashboard_title: str = Field(
        "SafeStreet - Analise de Vulnerabilidade Urbana Noturna",
        alias="DASHBOARD_TITLE",
    )
    dashboard_theme: Literal["dark", "light"] = Field(
        "dark",
        alias="DASHBOARD_THEME",
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @field_validator("pipeline_output_dir", mode="before")
    @classmethod
    def resolve_path(cls, v: str) -> Path:
        return Path(v).resolve()


settings = Settings()


@dataclass
class CityConfig:
    name: str
    state: str
    osm_name: str
    center_lat: float
    center_lon: float
    zoom_start: int = 12
    bbox_lat_min: float = 0.0
    bbox_lat_max: float = 0.0
    bbox_lon_min: float = 0.0
    bbox_lon_max: float = 0.0
    data_source: str = ""
    crime_file_pattern: str = ""


CITIES: dict[str, CityConfig] = {
    "sao-paulo": CityConfig(
        name="Sao Paulo",
        state="SP",
        osm_name="Sao Paulo, Brazil",
        center_lat=-23.5505,
        center_lon=-46.6333,
        zoom_start=11,
        bbox_lat_min=-23.85,
        bbox_lat_max=-23.30,
        bbox_lon_min=-46.90,
        bbox_lon_max=-46.30,
        data_source="ssp_sp",
        crime_file_pattern="ssp_sp_{year}.xlsx",
    ),
}


def get_city(city_key: str) -> CityConfig:
    if city_key not in CITIES:
        available = ", ".join(CITIES.keys())
        raise ValueError(f"Cidade '{city_key}' nao encontrada. Disponiveis: {available}")
    return CITIES[city_key]


def list_cities() -> list[str]:
    return list(CITIES.keys())
