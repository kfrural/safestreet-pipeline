from __future__ import annotations

from geopandas import GeoDataFrame, sjoin
from loguru import logger


def spatial_join_crimes_to_infrastructure(
    crimes: GeoDataFrame,
    infrastructure: GeoDataFrame,
    distance: float = 100,
) -> GeoDataFrame:
    logger.info(
        "Executando join espacial: crimes -> infraestrutura (distância={}m)", distance
    )
    infra_buffered = infrastructure.copy()
    infra_buffered.geometry = infra_buffered.geometry.buffer(distance)
    infra_buffered = infra_buffered.set_crs(infrastructure.crs, allow_override=True)

    result = sjoin(
        crimes,
        infra_buffered[["geometry"]],
        how="left",
        predicate="intersects",
    )
    logger.info("Join espacial concluído: {} registros", len(result))
    return result


def count_crimes_by_h3(crimes: GeoDataFrame, h3_column: str = "h3_index") -> GeoDataFrame:
    return (
        crimes.groupby(h3_column)
        .size()
        .reset_index(name="crime_count")
    )
