from __future__ import annotations

import osmnx as ox
from geopandas import GeoDataFrame
from loguru import logger

NIGHTLIFE_AMENITIES = ["bar", "pub", "nightclub"]


def fetch_nightlife_pois(
    city_name: str,
) -> dict[str, GeoDataFrame]:
    logger.info("Buscando pontos de atividade noturna em '{}'", city_name)
    results: dict[str, GeoDataFrame] = {}

    combined_tags = {"amenity": NIGHTLIFE_AMENITIES}
    try:
        gdf = ox.features_from_place(city_name, tags=combined_tags)
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
        for amenity_type in NIGHTLIFE_AMENITIES:
            mask = gdf.get("amenity") == amenity_type
            subset = gdf[mask] if mask is not None else GeoDataFrame()
            results[amenity_type] = subset
            logger.info(
                "Encontrados {} pontos do tipo '{}'",
                len(subset),
                amenity_type,
            )
    except Exception as e:
        logger.warning("Erro ao buscar nightlife combinado: {}", e)
        for amenity_type in NIGHTLIFE_AMENITIES:
            try:
                single_tag = {"amenity": amenity_type}
                gdf = ox.features_from_place(city_name, tags=single_tag)
                gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
                results[amenity_type] = gdf
                logger.info(
                    "Encontrados {} pontos do tipo '{}' (individual)",
                    len(gdf),
                    amenity_type,
                )
            except Exception as e2:
                logger.warning("Erro ao buscar '{}': {}", amenity_type, e2)
                results[amenity_type] = GeoDataFrame()

    total = sum(len(g) for g in results.values())
    logger.info(
        "Total de pontos de atividade noturna: {} ({} tipos)",
        total,
        len(results),
    )
    return results
