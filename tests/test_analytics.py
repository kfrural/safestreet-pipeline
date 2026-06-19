from __future__ import annotations

import numpy as np
from libpysal.weights import W

from src.analytics import classify_lisa_clusters, compute_moran_global


def test_compute_moran_global() -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    weights = W({0: [1], 1: [0, 2], 2: [1, 3], 3: [2, 4], 4: [3]})
    result = compute_moran_global(values, weights, permutations=99)
    assert "moran_i" in result
    assert "p_value" in result
    assert "significant" in result


def test_classify_lisa_clusters() -> None:
    q = np.array([1, 2, 3, 4, 1])
    p_sim = np.array([0.01, 0.02, 0.03, 0.04, 0.50])
    clusters = classify_lisa_clusters(q, p_sim, alpha=0.05)
    assert clusters == ["HH", "LH", "LL", "HL", "NS"]
