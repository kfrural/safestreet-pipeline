"""Cached query wrappers for Streamlit dashboard.

Uses @st.cache_data with TTL to avoid re-querying the database
on every Streamlit rerun. Wraps functions from src.db.queries.
"""
from __future__ import annotations

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


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_h3_cells(city: str | None = None) -> list[dict[str, Any]]:
    return get_h3_cells(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_available_years(city: str) -> list[int]:
    return get_available_years(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_available_months(city: str) -> list[int]:
    return get_available_months(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_city_stats(city: str) -> dict[str, Any]:
    return get_city_stats(city)


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
    return get_neighborhoods(city)


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_crime_category_list(city: str) -> list[str]:
    return get_crime_category_list(city)


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
