from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from esda import Moran, Moran_Local
from libpysal.weights import W
from loguru import logger


def compute_moran_global(
    values: np.ndarray,
    weights: W,
    permutations: int = 999,
) -> dict[str, Any]:
    logger.info("Calculando Indice de Moran Global")
    moran = Moran(values, weights, permutations=permutations)
    result = {
        "moran_i": moran.I,
        "expected_i": moran.EI,
        "p_value": moran.p_sim,
        "z_score": moran.z_sim,
        "significant": bool(moran.p_sim < 0.05),
    }
    logger.info(
        "Moran's I: {:.4f} | p-value: {:.4f} | Significante: {}",
        moran.I,
        moran.p_sim,
        result["significant"],
    )
    return result


def compute_moran_local(
    values: np.ndarray,
    weights: W,
    permutations: int = 999,
) -> dict[str, np.ndarray]:
    import warnings

    logger.info("Calculando Indice de Moran Local (LISA)")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        local_moran = Moran_Local(values, weights, permutations=permutations)
    result = {
        "is": local_moran.Is,
        "p_sim": local_moran.p_sim,
        "q": local_moran.q,
    }
    return result


def classify_lisa_clusters(q: np.ndarray, p_sim: np.ndarray, alpha: float = 0.05) -> list[str]:
    mapping = {
        1: "HH",
        2: "LH",
        3: "LL",
        4: "HL",
    }
    clusters: list[str] = []
    for q_val, p_val in zip(q, p_sim):
        if p_val < alpha:
            clusters.append(mapping.get(int(q_val), "NS"))
        else:
            clusters.append("NS")
    return clusters


def build_spatial_weights(
    gdf: pd.DataFrame,
    h3_column: str = "h3_index",
) -> W | None:
    import h3

    h3_indices = gdf[h3_column].tolist()
    index_map = {idx: i for i, idx in enumerate(h3_indices)}

    neighbors: dict[int, list[int]] = {i: [] for i in range(len(h3_indices))}

    for idx in h3_indices:
        i = index_map[idx]
        try:
            ring = h3.grid_disk(idx, 1)
            for neighbor in ring:
                if neighbor in index_map and neighbor != idx:
                    neighbors[i].append(index_map[neighbor])
        except Exception:
            continue

    island_count = sum(1 for v in neighbors.values() if not v)
    if island_count:
        logger.info(
            "{} ilhas (sem vizinhos) em {} celulas totais",
            island_count,
            len(neighbors),
        )

    has_neighbors = any(v for v in neighbors.values())
    if not has_neighbors:
        logger.warning("Nenhuma vizinhanca encontrada para construcao de pesos")
        return None

    return W(neighbors, silence_warnings=True)
