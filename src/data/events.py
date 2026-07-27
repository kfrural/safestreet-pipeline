from __future__ import annotations

import osmnx as ox
from geopandas import GeoDataFrame
from loguru import logger

CULTURAL_TAGS = {
    "amenity": [
        "cinema",
        "theatre",
        "arts_centre",
        "stadium",
        "arena",
        "events_venue",
        "conference_centre",
    ],
    "leisure": ["stadium", "sports_centre", "dance"],
}


def fetch_cultural_venues(city_name: str) -> dict[str, GeoDataFrame]:
    results: dict[str, GeoDataFrame] = {}
    all_frames: list[GeoDataFrame] = []

    for tag_key, tag_values in CULTURAL_TAGS.items():
        if isinstance(tag_values, list):
            for val in tag_values:
                try:
                    gdf = ox.features_from_place(
                        city_name, tags={tag_key: val}
                    )
                    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
                    if not gdf.empty:
                        gdf = gdf.copy()
                        gdf["venue_type"] = f"{tag_key}={val}"
                        all_frames.append(gdf)
                        logger.info(
                            "{} {}: {} venues",
                            tag_key, val, len(gdf),
                        )
                except Exception as e:
                    logger.warning(
                        "Erro ao buscar {}={}: {}", tag_key, val, e
                    )
        else:
            try:
                gdf = ox.features_from_place(
                    city_name, tags={tag_key: tag_values}
                )
                gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
                if not gdf.empty:
                    gdf = gdf.copy()
                    gdf["venue_type"] = f"{tag_key}={tag_values}"
                    all_frames.append(gdf)
                    logger.info(
                        "{} {}: {} venues",
                        tag_key, tag_values, len(gdf),
                    )
            except Exception as e:
                logger.warning(
                    "Erro ao buscar {}={}: {}", tag_key, tag_values, e
                )

    if all_frames:
        import pandas as pd
        combined = pd.concat(all_frames, ignore_index=True)
        if "osmid" in combined.columns:
            combined = combined.drop_duplicates(subset=["osmid"])
        results["all_venues"] = combined
        logger.info(
            "Total de venues culturais: {} (tipos: {})",
            len(combined),
            combined["venue_type"].nunique(),
        )
    else:
        results["all_venues"] = GeoDataFrame()

    return results


def compute_venue_stats(venues_data: dict[str, GeoDataFrame]) -> dict:
    stats: dict = {}
    for key, gdf in venues_data.items():
        if gdf.empty:
            stats[key] = {"total": 0, "types": {}}
            continue
        type_counts = {}
        if "venue_type" in gdf.columns:
            type_counts = gdf["venue_type"].value_counts().to_dict()
        stats[key] = {
            "total": len(gdf),
            "types": type_counts,
        }
    return stats
