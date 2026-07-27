from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests
from loguru import logger

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_weather_data(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    if cache_dir:
        cache_path = cache_dir / f"weather_{latitude}_{longitude}_{start_date}_{end_date}.csv"
        if cache_path.exists():
            logger.info("Carregando dados climaticos do cache: {}", cache_path)
            return pd.read_csv(cache_path, parse_dates=["date"])

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "timezone": "America/Sao_Paulo",
    }

    logger.info(
        "Buscando dados climaticos: {} a {} para ({}, {})",
        start_date,
        end_date,
        latitude,
        longitude,
    )

    try:
        resp = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Erro ao buscar dados climaticos: {}", e)
        return pd.DataFrame()

    daily = data.get("daily", {})
    if not daily:
        logger.warning("Resposta climatica vazia")
        return pd.DataFrame()

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temp_max": daily.get("temperature_2m_max"),
            "temp_min": daily.get("temperature_2m_min"),
            "precipitation": daily.get("precipitation_sum", [0] * len(daily["time"])),
            "wind_max": daily.get("wind_speed_10m_max"),
        }
    )

    df["temp_avg"] = (df["temp_max"] + df["temp_min"]) / 2
    df["is_rainy"] = df["precipitation"] > 0.5
    df["rain_category"] = pd.cut(
        df["precipitation"],
        bins=[-0.1, 0, 2, 10, 100],
        labels=["Seco", "Chuva leve", "Chuva moderada", "Chuva forte"],
    )

    logger.info("Dados climaticos: {} registros", len(df))

    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_path, index=False)

    return df


def match_crime_weather(
    crime_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    date_column: str = "date",
) -> pd.DataFrame:
    if weather_df.empty or date_column not in crime_df.columns:
        crime_df["temp_avg"] = None
        crime_df["precipitation"] = None
        crime_df["is_rainy"] = False
        crime_df["rain_category"] = "Seco"
        return crime_df

    crime_df = crime_df.copy()
    crime_df["_crime_date"] = pd.to_datetime(crime_df[date_column], errors="coerce").dt.date

    weather_lookup = weather_df.set_index(pd.to_datetime(weather_df["date"]).dt.date)[
        ["temp_avg", "precipitation", "is_rainy", "rain_category"]
    ].to_dict("index")

    crime_df["temp_avg"] = crime_df["_crime_date"].map(
        lambda d: weather_lookup.get(d, {}).get("temp_avg")
    )
    crime_df["precipitation"] = crime_df["_crime_date"].map(
        lambda d: weather_lookup.get(d, {}).get("precipitation", 0)
    )
    crime_df["is_rainy"] = crime_df["_crime_date"].map(
        lambda d: weather_lookup.get(d, {}).get("is_rainy", False)
    )
    crime_df["rain_category"] = crime_df["_crime_date"].map(
        lambda d: weather_lookup.get(d, {}).get("rain_category", "Seco")
    )

    crime_df = crime_df.drop(columns=["_crime_date"])
    matched = crime_df["temp_avg"].notna().sum()
    logger.info(
        "Clima associado a {}/{} crimes",
        matched,
        len(crime_df),
    )
    return crime_df


def compute_weather_stats(crime_df: pd.DataFrame) -> dict:
    if crime_df.empty or "is_rainy" not in crime_df.columns:
        return {}

    total = len(crime_df)
    rainy = crime_df["is_rainy"].sum()
    avg_temp = crime_df["temp_avg"].mean()

    stats = {
        "total_crimes": total,
        "rainy_crimes": int(rainy),
        "dry_crimes": total - int(rainy),
        "rain_pct": round(rainy / total * 100, 1) if total > 0 else 0,
        "avg_temp": round(avg_temp, 1) if pd.notna(avg_temp) else None,
    }

    if "rain_category" in crime_df.columns:
        stats["by_rain_category"] = crime_df["rain_category"].value_counts().to_dict()

    return stats
