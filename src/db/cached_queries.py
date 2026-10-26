"""Cached query wrappers for the Streamlit dashboard.

Primary source is the exported static snapshot
(``data/processed/dashboard_snapshot.json``) so the dashboard works without a
database (e.g. Streamlit Cloud). If the snapshot is missing, the functions fall
back to PostgreSQL and finally to the raw/processed CSV files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
_RAW = _ROOT / "data" / "raw"

_SNAPSHOT: dict[str, Any] | None = None


def _snapshot() -> dict[str, Any]:
    global _SNAPSHOT
    if _SNAPSHOT is not None:
        return _SNAPSHOT
    snap_path = _PROCESSED / "dashboard_snapshot.json"
    if not snap_path.exists():
        _SNAPSHOT = {}
        return _SNAPSHOT
    try:
        _SNAPSHOT = json.loads(snap_path.read_text(encoding="utf-8"))
    except Exception:
        _SNAPSHOT = {}
    return _SNAPSHOT


def _safe(fn, *args, default=None):
    try:
        return fn(*args)
    except Exception:
        return default


# ---------------------------------------------------------------------------
# H3 cells / city stats
# ---------------------------------------------------------------------------
@st.cache_data(ttl=_TTL, show_spinner=False)
def load_h3_cells(city: str | None = None) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("h3_cells"):
        cells = snap["h3_cells"]
        if city:
            cells = [c for c in cells if c.get("city") == city]
        if cells:
            return cells

    res = _safe(get_h3_cells, city, default=[])
    if res:
        return res

    return []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_city_stats(city: str) -> dict[str, Any]:
    snap = _snapshot()
    if snap.get("city_stats"):
        return snap["city_stats"]

    res = _safe(get_city_stats, city, default={})
    if res and int(res.get("total_cells", 0)) > 0:
        return res

    return {"total_crimes": 0, "total_cells": 0, "high_risk": 0, "moran_hh": 0}


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
@st.cache_data(ttl=_TTL, show_spinner=False)
def load_available_years(city: str) -> list[int]:
    snap = _snapshot()
    if snap.get("available_years"):
        return snap["available_years"]
    return _safe(get_available_years, city, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_available_months(city: str) -> list[int]:
    snap = _snapshot()
    if snap.get("available_months"):
        return snap["available_months"]
    return _safe(get_available_months, city, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_category_list(city: str) -> list[str]:
    snap = _snapshot()
    if snap.get("crime_category_list"):
        return snap["crime_category_list"]
    res = _safe(get_crime_category_list, city, default=[])
    if res:
        return res
    return ["Violencia", "Roubo/Furto", "Trafico/Armas", "Outros"]


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_neighborhoods(city: str) -> list[str]:
    snap = _snapshot()
    if snap.get("neighborhoods"):
        return snap["neighborhoods"]
    return _safe(get_neighborhoods, city, default=[]) or []


# ---------------------------------------------------------------------------
# Location points
# ---------------------------------------------------------------------------
def _filter_locations(
    city: str,
    year: int | None,
    month: int | None,
    category: str | None,
) -> list[dict[str, Any]]:
    snap = _snapshot()
    locs = snap.get("crime_locations_all") or []
    out = []
    for c in locs:
        if year is not None and c.get("year") != year:
            continue
        if month is not None and c.get("month") != month:
            continue
        if category is not None and c.get("crime_category") != category:
            continue
        out.append(c)
    return out


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_locations_filtered(
    city: str,
    year: int | None = None,
    month: int | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("crime_locations_all"):
        return _filter_locations(city, year, month, category)

    res = _safe(get_crime_locations_filtered, city, year, month, category, default=[])
    return res or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_locations(
    city: str,
    category: str | None = None,
) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("crime_locations_all"):
        return _filter_locations(city, None, None, category)

    res = _safe(get_crime_locations, city, category, default=[])
    return res or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_by_hour(city: str) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("crime_locations_all"):
        counts: dict[int, int] = {}
        for c in snap["crime_locations_all"]:
            h = c.get("hour")
            if h is None:
                continue
            counts[int(h)] = counts.get(int(h), 0) + 1
        return [{"hour": k, "crime_count": v} for k, v in sorted(counts.items())]

    return _safe(get_crime_by_hour, city, default=[]) or []


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------
@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_categories(city: str) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("crime_categories"):
        return snap["crime_categories"]
    return _safe(get_crime_categories, city, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_by_infra(city: str) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("crime_by_infra"):
        return snap["crime_by_infra"]
    return _safe(get_crime_by_infra_proximity, city, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_by_transit(city: str) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("crime_by_transit"):
        return snap["crime_by_transit"]
    return _safe(get_crime_by_transit_proximity, city, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_top_natures(city: str, limit: int = 10) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("top_natures"):
        return snap["top_natures"][:limit]
    return _safe(get_top_natures, city, limit, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_vulnerability_gaps(city: str) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("vulnerability_gaps"):
        return snap["vulnerability_gaps"]
    return _safe(get_vulnerability_gaps, city, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_temporal_trend(
    city: str,
    year: int | None = None,
    month: int | None = None,
) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("temporal_trend"):
        trend = snap["temporal_trend"]
        if year is not None:
            trend = [t for t in trend if t.get("year") == year]
        if month is not None:
            trend = [t for t in trend if t.get("month") == month]
        return trend
    return _safe(get_temporal_trend, city, year, month, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_seasonal_monthly(city: str) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("seasonal_monthly"):
        return snap["seasonal_monthly"]
    return _safe(get_seasonal_monthly, city, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_weekly_cycle(
    city: str,
    year: int | None = None,
    month: int | None = None,
) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("crime_locations_all") and (year is not None or month is not None):
        counts: dict[int, int] = {}
        for c in snap["crime_locations_all"]:
            if year is not None and c.get("year") != year:
                continue
            if month is not None and c.get("month") != month:
                continue
            d = c.get("day_of_week")
            if d is None:
                continue
            counts[int(d)] = counts.get(int(d), 0) + 1
        return [{"day_of_week": k, "crime_count": v} for k, v in sorted(counts.items())]
    if snap.get("weekly_cycle"):
        return snap["weekly_cycle"]
    return _safe(get_weekly_cycle, city, year, month, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_heatmap_hour_weekday(
    city: str,
    year: int | None = None,
    month: int | None = None,
) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("crime_locations_all") and (year is not None or month is not None):
        counts: dict[tuple[int, int], int] = {}
        for c in snap["crime_locations_all"]:
            if year is not None and c.get("year") != year:
                continue
            if month is not None and c.get("month") != month:
                continue
            d = c.get("day_of_week")
            h = c.get("hour")
            if d is None or h is None:
                continue
            key = (int(d), int(h))
            counts[key] = counts.get(key, 0) + 1
        return [
            {"day_of_week": k[0], "hour": k[1], "crime_count": v} for k, v in sorted(counts.items())
        ]
    if snap.get("heatmap_hour_weekday"):
        return snap["heatmap_hour_weekday"]
    return _safe(get_heatmap_hour_weekday, city, year, month, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_heatmap_monthly(city: str) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("heatmap_monthly"):
        return snap["heatmap_monthly"]
    return _safe(get_heatmap_monthly, city, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_temporal_trend_by_category(
    city: str,
    category: str | None = None,
    neighborhood: str | None = None,
) -> list[dict[str, Any]]:
    res = _safe(get_temporal_trend_by_category, city, category, neighborhood, default=[])
    if res:
        return res
    trend = load_temporal_trend(city)
    if category:
        trend = [t for t in trend if t.get("crime_category") == category]
    return trend


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_neighborhood_crime_summary(city: str) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("neighborhood_crime_summary"):
        return snap["neighborhood_crime_summary"]
    return _safe(get_neighborhood_crime_summary, city, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_neighborhood_infra_gaps(city: str) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("neighborhood_infra_gaps"):
        return snap["neighborhood_infra_gaps"]
    return _safe(get_neighborhood_infra_gaps, city, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_correlation_data(city: str) -> list[dict[str, Any]]:
    snap = _snapshot()
    if snap.get("correlation_data"):
        return snap["correlation_data"]
    return _safe(get_correlation_data, city, default=[]) or []


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_ibge_stats(city: str) -> dict[str, Any]:
    snap = _snapshot()
    if snap.get("ibge_stats"):
        return snap["ibge_stats"]
    ibge_file = _EXTERNAL / f"ibge_stats_{city}.json"
    if ibge_file.exists():
        try:
            return json.loads(ibge_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_weather_stats(city: str) -> dict[str, Any]:
    snap = _snapshot()
    if snap.get("weather_stats"):
        return snap["weather_stats"]
    w_file = _EXTERNAL / f"weather_stats_{city}.json"
    if w_file.exists():
        try:
            return json.loads(w_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_rental_stats(city: str) -> dict[str, Any]:
    snap = _snapshot()
    if snap.get("rental_stats"):
        return snap["rental_stats"]
    r_file = _EXTERNAL / f"rental_stats_{city}.json"
    if r_file.exists():
        try:
            return json.loads(r_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_transport_night_stats(city: str) -> dict[str, Any]:
    snap = _snapshot()
    if snap.get("transport_night"):
        return snap["transport_night"]
    t_file = _EXTERNAL / f"transport_night_{city}.json"
    if t_file.exists():
        try:
            return json.loads(t_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_sentiment_stats(city: str) -> dict[str, Any]:
    snap = _snapshot()
    if snap.get("sentiment"):
        return snap["sentiment"]
    s_file = _EXTERNAL / f"sentiment_{city}.json"
    if s_file.exists():
        try:
            return json.loads(s_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

