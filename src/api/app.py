"""SafeStreet REST API.

FastAPI endpoints for programmatic access to SafeStreet data.

Run with:
    PYTHONPATH=. uvicorn src.api.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.db.queries import (
    get_available_years,
    get_city_stats,
    get_correlation_data,
    get_crime_categories,
    get_crime_locations,
    get_cities_with_data,
    get_h3_cells,
    get_temporal_trend,
    get_vulnerability_gaps,
)

app = FastAPI(
    title="SafeStreet API",
    description="API de acesso aos dados de inteligencia espacial urbana noturna",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    version: str


class CityStatsResponse(BaseModel):
    total_cells: int
    total_crimes: int
    high_risk: int
    moran_hh: int


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/cities")
def list_cities() -> list[str]:
    cities = get_cities_with_data()
    if not cities:
        return ["sao-paulo"]
    return cities


@app.get("/cities/{city}/stats", response_model=CityStatsResponse)
def city_stats(city: str) -> CityStatsResponse:
    stats = get_city_stats(city)
    if stats.get("total_cells", 0) == 0:
        raise HTTPException(status_code=404, detail=f"No data for city: {city}")
    return CityStatsResponse(**stats)


@app.get("/cities/{city}/h3-cells")
def h3_cells(
    city: str,
    limit: int = Query(1000, ge=1, le=50000),
    min_vulnerability: float = Query(0.0, ge=0.0, le=1.0),
) -> list[dict]:
    cells = get_h3_cells(city)
    if not cells:
        raise HTTPException(status_code=404, detail=f"No data for city: {city}")
    filtered = [c for c in cells if (c.get("vulnerability_score") or 0) >= min_vulnerability]
    return filtered[:limit]


@app.get("/cities/{city}/crimes")
def crime_locations(
    city: str,
    category: str | None = None,
    limit: int = Query(5000, ge=1, le=50000),
) -> list[dict]:
    locations = get_crime_locations(city, category)
    if not locations:
        raise HTTPException(status_code=404, detail=f"No crime data for city: {city}")
    return locations[:limit]


@app.get("/cities/{city}/categories")
def crime_categories(city: str) -> list[dict]:
    cats = get_crime_categories(city)
    if not cats:
        raise HTTPException(status_code=404, detail=f"No data for city: {city}")
    return cats


@app.get("/cities/{city}/temporal")
def temporal_trend(
    city: str,
    year: int | None = None,
) -> list[dict]:
    trend = get_temporal_trend(city, year=year)
    if not trend:
        raise HTTPException(status_code=404, detail=f"No temporal data for city: {city}")
    return trend


@app.get("/cities/{city}/correlations")
def correlations(city: str) -> list[dict]:
    data = get_correlation_data(city)
    if not data:
        raise HTTPException(status_code=404, detail=f"No correlation data for city: {city}")
    return data


@app.get("/cities/{city}/gaps")
def vulnerability_gaps(city: str) -> list[dict]:
    gaps = get_vulnerability_gaps(city)
    if not gaps:
        raise HTTPException(status_code=404, detail=f"No gap data for city: {city}")
    return gaps


@app.get("/cities/{city}/years")
def available_years(city: str) -> list[int]:
    return get_available_years(city)
