from __future__ import annotations

import re

import osmnx as ox
from geopandas import GeoDataFrame
from loguru import logger


def _parse_opening_hours(hours_str: str) -> dict:
    if not hours_str or hours_str == "24/7":
        return {"is_24h": True, "opens": 0, "closes": 24, "raw": hours_str}

    hours_str = str(hours_str).strip()
    if "24/7" in hours_str:
        return {"is_24h": True, "opens": 0, "closes": 24, "raw": hours_str}

    time_match = re.findall(r"(\d{1,2}:\d{2})\s*[-\u2013]\s*(\d{1,2}:\d{2})", hours_str)
    if not time_match:
        return {"is_24h": False, "opens": None, "closes": None, "raw": hours_str}

    opens_str, closes_str = time_match[0]
    try:
        opens_h = int(opens_str.split(":")[0])
        closes_h = int(closes_str.split(":")[0])
        if closes_h == 0:
            closes_h = 24
        return {
            "is_24h": False,
            "opens": opens_h,
            "closes": closes_h,
            "raw": hours_str,
        }
    except (ValueError, IndexError):
        return {"is_24h": False, "opens": None, "closes": None, "raw": hours_str}


def _is_open_at_night(parsed: dict, night_start: int = 20, night_end: int = 6) -> bool:
    if parsed.get("is_24h"):
        return True
    opens = parsed.get("opens")
    closes = parsed.get("closes")
    if opens is None or closes is None:
        return True

    if opens < closes:
        return opens <= night_start or closes >= night_end
    else:
        return opens <= night_start or closes <= night_end


def fetch_transit_with_hours(city_name: str) -> dict[str, GeoDataFrame]:
    results: dict[str, GeoDataFrame] = {}

    for infra_type, tags in [
        ("bus_stop", {"highway": "bus_stop"}),
        ("metro_station", {"railway": "station", "station": "subway"}),
    ]:
        try:
            gdf = ox.features_from_place(city_name, tags=tags)
            gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]

            if "opening_hours" in gdf.columns:
                parsed = gdf["opening_hours"].apply(
                    lambda x: _parse_opening_hours(x)
                    if x and str(x) != "nan"
                    else {"is_24h": False, "opens": None, "closes": None, "raw": ""}
                )
                gdf["is_24h"] = parsed.apply(lambda p: p.get("is_24h", False))
                gdf["opens_at_night"] = parsed.apply(
                    lambda p: _is_open_at_night(p)
                )
                gdf["night_hours_raw"] = parsed.apply(lambda p: p.get("raw", ""))

                n_24h = gdf["is_24h"].sum()
                n_night = gdf["opens_at_night"].sum()
                logger.info(
                    "{}: {} total, {} 24h, {} abrem a noite",
                    infra_type, len(gdf), n_24h, n_night,
                )
            else:
                gdf["is_24h"] = False
                gdf["opens_at_night"] = True
                gdf["night_hours_raw"] = ""
                logger.info(
                    "{}: {} total (sem opening_hours)",
                    infra_type, len(gdf),
                )

            results[infra_type] = gdf
        except Exception as e:
            logger.warning("Erro ao buscar {}: {}", infra_type, e)
            results[infra_type] = GeoDataFrame()

    return results


def compute_night_transit_stats(
    transit_data: dict[str, GeoDataFrame],
) -> dict:
    stats: dict = {}
    for infra_type, gdf in transit_data.items():
        if gdf.empty:
            stats[infra_type] = {"total": 0, "night_24h": 0, "night_open": 0}
            continue
        stats[infra_type] = {
            "total": len(gdf),
            "night_24h": int(gdf["is_24h"].sum()) if "is_24h" in gdf.columns else 0,
            "night_open": int(gdf["opens_at_night"].sum())
            if "opens_at_night" in gdf.columns
            else len(gdf),
        }
    return stats
