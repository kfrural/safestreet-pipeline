from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    from pydantic import Field, field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _HAS_PYDANTIC = True
except Exception:
    _HAS_PYDANTIC = False

    class Field:
        def __init__(self, default=None, *args, **kwargs):
            self.default = default

    def field_validator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    class SettingsConfigDict(dict):
        pass

    class BaseSettings:
        def __init__(self, **kwargs):
            import os

            for key in self.__annotations__:
                # try env/alias
                env_key = key.upper()
                if env_key in os.environ:
                    value = os.environ[env_key]
                    # simple cast
                    ann = self.__annotations__.get(key)
                    if ann is int:
                        try:
                            value = int(value)
                        except Exception:
                            pass
                    elif ann is float:
                        try:
                            value = float(value)
                        except Exception:
                            pass
                    elif hasattr(ann, "__origin__") and ann.__origin__ is Literal:
                        pass
                    elif ann is Path or getattr(ann, "__name__", "") == "Path":
                        value = Path(value)
                    setattr(self, key, value)
                    continue
                # check aliases from Field if possible
                field = getattr(type(self), key, None)
                if isinstance(field, Field):
                    setattr(self, key, field.default)
                elif hasattr(self, key):
                    pass
                else:
                    default = getattr(type(self), key, None)
                    if isinstance(default, Field):
                        setattr(self, key, default.default)
                    else:
                        setattr(self, key, default)
            # apply kwargs
            for k, v in kwargs.items():
                setattr(self, k, v)


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
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @field_validator("pipeline_output_dir", mode="before")
    @classmethod
    def resolve_path(cls, v: str) -> Path:
        try:
            return Path(v).resolve()
        except Exception:
            return Path("data/processed").resolve()


try:
    settings = Settings()
except Exception:
    settings = Settings.__new__(Settings)
    settings.postgres_host = "localhost"
    settings.postgres_port = 5432
    settings.postgres_db = "safestreet"
    settings.postgres_user = "safestreet"
    settings.postgres_password = "safestreet_pass"
    settings.overpass_api_url = "https://overpass-api.de/api/interpreter"
    settings.pipeline_output_dir = Path("data/processed").resolve()
    settings.external_data_dir = Path("data/external").resolve()
    settings.h3_resolution = 9
    settings.dashboard_title = "SafeStreet - Analise de Vulnerabilidade Urbana Noturna"
    settings.dashboard_theme = "dark"


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
