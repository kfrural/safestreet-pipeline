from __future__ import annotations

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

    # PostGIS
    postgres_host: str = Field("localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")
    postgres_db: str = Field("safestreet", alias="POSTGRES_DB")
    postgres_user: str = Field("safestreet", alias="POSTGRES_USER")
    postgres_password: str = Field("safestreet_pass", alias="POSTGRES_PASSWORD")

    # OSM
    overpass_api_url: str = Field(
        "https://overpass-api.de/api/interpreter",
        alias="OVERPASS_API_URL",
    )
    osm_city_name: str = Field("Recife, Brazil", alias="OSM_CITY_NAME")

    # Pipeline
    pipeline_crime_file: Path = Field(
        Path("data/raw/crime_records.csv"),
        alias="PIPELINE_CRIME_FILE",
    )
    pipeline_output_dir: Path = Field(
        Path("data/processed"),
        alias="PIPELINE_OUTPUT_DIR",
    )
    h3_resolution: int = Field(9, alias="H3_RESOLUTION", ge=0, le=15)

    # Dashboard
    dashboard_title: str = Field(
        "SafeStreet - Análise de Vulnerabilidade Urbana Noturna",
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

    @field_validator("pipeline_crime_file", "pipeline_output_dir", mode="before")
    @classmethod
    def resolve_path(cls, v: str) -> Path:
        return Path(v).resolve()


settings = Settings()
