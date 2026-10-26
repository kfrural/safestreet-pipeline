"""Cached query wrappers for Streamlit dashboard.

Uses @st.cache_data with TTL to avoid re-querying the database
on every Streamlit rerun. Wraps functions from src.db.queries.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.db.queries import (
    get_available_months,
    get_available_years,
    get_city_stats,
    get_correlation_data,
    get_crime_by_hour,
    get_crime_by_infra_proximity,
    get_crime_by_transit_proximity,
    get_crime_categories,
    get_crime_category_list,
    get_crime_locations,
    get_crime_locations_filtered,
    get_h3_cells,
    get_heatmap_hour_weekday,
    get_heatmap_monthly,
    get_neighborhood_crime_summary,
    get_neighborhood_infra_gaps,
    get_neighborhoods,
    get_seasonal_monthly,
    get_temporal_trend,
    get_temporal_trend_by_category,
    get_top_natures,
    get_vulnerability_gaps,
    get_weekly_cycle,
)

_TTL = 300  # 5 minutes
_ROOT = Path(__file__).resolve().parents[2]
_PROCESSED = _ROOT / "data" / "processed"
_EXTERNAL = _ROOT / "data" / "external"


def _load_h3_from_files(city: str | None = None) -> list[dict[str, Any]]:
    csv_path = _PROCESSED / "h3_analysis_results_sao-paulo.csv"
    if not csv_path.exists():
        for p in _PROCESSED.glob("h3_analysis_results*.csv"):
            csv_path = p
            break
    if not csv_path.exists():
        return []

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return []

    if city and "city" in df.columns:
        df = df[df["city"] == city]

    df = df.replace({float("nan"): None})
    return df.to_dict("records")


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_h3_cells(city: str | None = None) -> list[dict[str, Any]]:
    try:
        res = get_h3_cells(city)
        if res:
            return res
    except Exception:
        pass
    return _load_h3_from_files(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_available_years(city: str) -> list[int]:
    try:
        res = get_available_years(city)
        if res:
            return res
    except Exception:
        pass
    return []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_available_months(city: str) -> list[int]:
    try:
        res = get_available_months(city)
        if res:
            return res
    except Exception:
        pass
    return []


def _load_city_stats_from_files(city: str) -> dict[str, Any]:
    cells = _load_h3_from_files(city)
    if not cells:
        return {
            "total_crimes": 0,
            "total_cells": 0,
            "high_risk": 0,
            "moran_hh": 0,
        }
    total_crimes = sum(int(c.get("crime_count") or 0) for c in cells)
    total_cells = len(cells)
    high_risk = 0
    for c in cells:
        try:
            v = float(c.get("vulnerability_score") or 0)
            if v >= 0.7:
                high_risk += 1
        except Exception:
            pass
    moran_hh = sum(1 for c in cells if str(c.get("moran_cluster") or "") in ("HH", "High-High"))
    return {
        "total_crimes": total_crimes,
        "total_cells": total_cells,
        "high_risk": high_risk,
        "moran_hh": moran_hh,
    }


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_city_stats(city: str) -> dict[str, Any]:
    try:
        res = get_city_stats(city)
        if res and res.get("total_crimes") is not None:
            return res
    except Exception:
        pass
    return _load_city_stats_from_files(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_correlation_data(city: str) -> list[dict[str, Any]]:
    return get_correlation_data(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_categories(city: str) -> list[dict[str, Any]]:
    return get_crime_categories(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_by_infra(city: str) -> list[dict[str, Any]]:
    return get_crime_by_infra_proximity(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_by_transit(city: str) -> list[dict[str, Any]]:
    return get_crime_by_transit_proximity(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_top_natures(city: str, limit: int = 10) -> list[dict[str, Any]]:
    return get_top_natures(city, limit)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_vulnerability_gaps(city: str) -> list[dict[str, Any]]:
    return get_vulnerability_gaps(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_temporal_trend(
    city: str,
    year: int | None = None,
    month: int | None = None,
) -> list[dict[str, Any]]:
    return get_temporal_trend(city, year, month)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_seasonal_monthly(city: str) -> list[dict[str, Any]]:
    return get_seasonal_monthly(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_weekly_cycle(
    city: str,
    year: int | None = None,
    month: int | None = None,
) -> list[dict[str, Any]]:
    return get_weekly_cycle(city, year, month)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_heatmap_hour_weekday(
    city: str,
    year: int | None = None,
    month: int | None = None,
) -> list[dict[str, Any]]:
    return get_heatmap_hour_weekday(city, year, month)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_locations_filtered(
    city: str,
    year: int | None = None,
    month: int | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    return get_crime_locations_filtered(city, year, month, category)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_locations(
    city: str,
    category: str | None = None,
) -> list[dict[str, Any]]:
    return get_crime_locations(city, category)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_by_hour(city: str) -> list[dict[str, Any]]:
    return get_crime_by_hour(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_neighborhoods(city: str) -> list[str]:
    try:
        res = get_neighborhoods(city)
        if res:
            return res
    except Exception:
        pass
    return []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_category_list(city: str) -> list[str]:
    try:
        res = get_crime_category_list(city)
        if res:
            return res
    except Exception:
        pass
    return ["Violencia", "Roubo/Furto", "Trafico/Armas", "Outros"]


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_temporal_trend_by_category(
    city: str,
    category: str | None = None,
    neighborhood: str | None = None,
) -> list[dict[str, Any]]:
    return get_temporal_trend_by_category(city, category, neighborhood)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_neighborhood_crime_summary(city: str) -> list[dict[str, Any]]:
    return get_neighborhood_crime_summary(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_neighborhood_infra_gaps(city: str) -> list[dict[str, Any]]:
    return get_neighborhood_infra_gaps(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_heatmap_monthly(city: str) -> list[dict[str, Any]]:
    return get_heatmap_monthly(city)
