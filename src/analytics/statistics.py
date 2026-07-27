from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler


def compute_pca_vulnerability(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
) -> dict[str, Any]:
    if feature_cols is None:
        feature_cols = [
            "crime_count",
            "lighting_density",
            "dist_nearest_lit",
            "bus_stop_density",
            "metro_density",
            "camera_count",
            "nightlife_density",
        ]

    available = [c for c in feature_cols if c in df.columns]
    if len(available) < 3:
        logger.warning("Colunas insuficientes para PCA: {}", available)
        return {"scores": pd.Series(dtype=float), "loadings": {}, "variance_explained": []}

    data = df[available].copy()
    data = data.fillna(0)

    scaler = StandardScaler()
    scaled = scaler.fit_transform(data)

    pca = PCA()
    pca.fit(scaled)

    scores = pca.transform(scaled)[:, 0]

    max_val = scores.max()
    min_val = scores.min()
    if max_val > min_val:
        scores_norm = (scores - min_val) / (max_val - min_val)
    else:
        scores_norm = np.zeros_like(scores)

    loadings = {}
    for i, col in enumerate(available):
        loadings[col] = round(float(pca.components_[0][i]), 4)

    variance = [round(float(v), 4) for v in pca.explained_variance_ratio_]

    logger.info(
        "PCA: PC1 explica {:.1f}% da variancia | loadings: {}",
        variance[0] * 100,
        {k: v for k, v in loadings.items()},
    )

    return {
        "scores": pd.Series(scores_norm, index=df.index),
        "loadings": loadings,
        "variance_explained": variance,
        "n_components": pca.n_components_,
        "feature_names": available,
    }


def _prepare_numeric_df(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    available = [c for c in columns if c in df.columns]
    data = df[available].copy()
    for col in data.columns:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    all_nan_cols = [c for c in data.columns if data[c].isna().all()]
    data = data.drop(columns=all_nan_cols, errors="ignore")
    data = data.fillna(0)
    return data


def compute_correlation_matrix(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    if columns is None:
        columns = [
            "crime_count",
            "lighting_density",
            "dist_nearest_lit",
            "bus_stop_density",
            "metro_density",
            "camera_count",
            "nightlife_density",
            "vulnerability_score",
        ]

    data = _prepare_numeric_df(df, columns)
    if len(data) < 5 or len(data.columns) < 3:
        return {"matrix": pd.DataFrame(), "p_values": pd.DataFrame()}

    corr = data.corr(method="pearson")

    p_vals = pd.DataFrame(
        np.ones((len(data.columns), len(data.columns))),
        index=data.columns,
        columns=data.columns,
    )
    for i, col1 in enumerate(data.columns):
        for j, col2 in enumerate(data.columns):
            if i != j:
                r, p = stats.pearsonr(data[col1], data[col2])
                p_vals.iloc[i, j] = p

    return {"matrix": corr, "p_values": p_vals}


def compute_spearman_matrix(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    if columns is None:
        columns = [
            "crime_count",
            "lighting_density",
            "dist_nearest_lit",
            "bus_stop_density",
            "metro_density",
            "camera_count",
            "nightlife_density",
        ]

    data = _prepare_numeric_df(df, columns)
    if len(data) < 5 or len(data.columns) < 3:
        return {"matrix": pd.DataFrame(), "p_values": pd.DataFrame()}

    corr = data.corr(method="spearman")

    p_vals = pd.DataFrame(
        np.ones((len(data.columns), len(data.columns))),
        index=data.columns,
        columns=data.columns,
    )
    for i, col1 in enumerate(data.columns):
        for j, col2 in enumerate(data.columns):
            if i != j:
                rho, p = stats.spearmanr(data[col1], data[col2])
                p_vals.iloc[i, j] = p

    return {"matrix": corr, "p_values": p_vals}


def run_ols_regression(
    df: pd.DataFrame,
    dependent: str = "crime_count",
    independent: list[str] | None = None,
) -> dict[str, Any]:
    if independent is None:
        independent = [
            "lighting_density",
            "dist_nearest_lit",
            "bus_stop_density",
            "metro_density",
            "camera_count",
            "nightlife_density",
        ]

    data = _prepare_numeric_df(df, [dependent] + independent)
    if dependent not in data.columns:
        return {"error": f"Dependent variable '{dependent}' not found"}
    if len(data.columns) < 3:
        return {"error": "Insufficient columns"}
    if len(data) < 10:
        return {"error": "Insufficient data points (< 10)"}

    feature_cols = [c for c in data.columns if c != dependent]
    feature_cols = [
        c for c in feature_cols
        if data[c].std() > 1e-10 and data[c].nunique() > 1
    ]
    if not feature_cols:
        return {"error": "No varying features after filtering"}

    y = data[dependent].values
    X = data[feature_cols].values

    X_with_const = np.column_stack([np.ones(len(X)), X])
    try:
        beta = np.linalg.lstsq(X_with_const, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return {"error": "Singular matrix"}

    y_pred = X_with_const @ beta
    residuals = y - y_pred

    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    n = len(y)
    k = X_with_const.shape[1]
    adj_r_squared = (
        1 - ((1 - r_squared) * (n - 1) / (n - k - 1)) if n > k + 1 else r_squared
    )

    mse = ss_res / (n - k) if n > k else ss_res
    try:
        var_beta = mse * np.linalg.inv(X_with_const.T @ X_with_const)
        se = np.sqrt(np.maximum(np.diag(var_beta), 0))
    except np.linalg.LinAlgError:
        se = np.zeros(k)

    t_vals = beta / se if np.all(se > 0) else np.zeros_like(beta)
    p_vals = 2 * (1 - stats.t.cdf(np.abs(t_vals), df=n - k))

    features = ["intercept"] + feature_cols
    coefficients = {}
    for name, b, t, p in zip(features, beta, t_vals, p_vals):
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        coefficients[name] = {
            "coef": round(float(b), 4),
            "t_stat": round(float(t), 4),
            "p_value": round(float(p), 6),
            "significant": p < 0.05,
            "stars": sig,
        }

    f_stat = (
        ((ss_tot - ss_res) / (k - 1)) / (ss_res / (n - k)) if n > k + 1 else 0
    )
    f_p = 1 - stats.f.cdf(f_stat, k - 1, n - k) if n > k + 1 else 1

    return {
        "r_squared": round(float(r_squared), 4),
        "adj_r_squared": round(float(adj_r_squared), 4),
        "f_statistic": round(float(f_stat), 4),
        "f_p_value": round(float(f_p), 6),
        "n_obs": n,
        "coefficients": coefficients,
        "residuals": pd.Series(residuals),
    }


def compute_random_forest_importance(
    df: pd.DataFrame,
    target: str = "crime_count",
    features: list[str] | None = None,
) -> dict[str, Any]:
    if features is None:
        features = [
            "lighting_density",
            "dist_nearest_lit",
            "bus_stop_density",
            "metro_density",
            "camera_count",
            "nightlife_density",
            "dist_nearest_metro",
        ]

    data = _prepare_numeric_df(df, [target] + features)
    if target not in data.columns:
        return {"error": "Target not found"}
    available = [c for c in data.columns if c != target]
    if len(available) < 2 or len(data) < 20:
        return {"error": "Insufficient data for Random Forest"}

    X = data[available].values
    y = data[target].values

    rf = RandomForestRegressor(
        n_estimators=100, max_depth=10, random_state=42, n_jobs=-1,
    )
    rf.fit(X, y)

    importances = rf.feature_importances_
    indices = np.argsort(importances)[::-1]

    result_features = []
    for idx in indices:
        result_features.append({
            "feature": available[idx],
            "importance": round(float(importances[idx]), 4),
        })

    return {
        "r_squared_train": round(float(rf.score(X, y)), 4),
        "features": result_features,
        "n_trees": rf.n_estimators,
    }


def compute_vif(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    if columns is None:
        columns = [
            "crime_count",
            "lighting_density",
            "dist_nearest_lit",
            "bus_stop_density",
            "metro_density",
            "camera_count",
            "nightlife_density",
        ]

    data = _prepare_numeric_df(df, columns)
    if len(data.columns) < 3 or len(data) < 10:
        return {"vif": {}}

    vif_data = {}
    for i, col in enumerate(data.columns):
        y = data[col].values
        X_other = data.drop(columns=[col]).values
        X_with_const = np.column_stack([np.ones(len(X_other)), X_other])

        try:
            beta = np.linalg.lstsq(X_with_const, y, rcond=None)[0]
            y_pred = X_with_const @ beta
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            vif = 1 / (1 - r2) if r2 < 1 else float("inf")
        except Exception:
            vif = float("inf")

        vif_data[col] = round(float(vif), 2)

    return {"vif": vif_data}


def compute_autocorrelation(
    values: np.ndarray,
    max_lag: int = 12,
) -> list[dict[str, Any]]:
    results = []
    n = len(values)
    mean = np.mean(values)
    var = np.var(values)

    if var == 0:
        return results

    for lag in range(1, min(max_lag + 1, n)):
        if lag >= n:
            break
        c = np.sum((values[:n - lag] - mean) * (values[lag:] - mean)) / n
        acf = c / var

        se = 1 / np.sqrt(n)
        sig = abs(acf) > 1.96 * se

        results.append({
            "lag": lag,
            "acf": round(float(acf), 4),
            "significant": sig,
        })

    return results


def run_durbin_watson(residuals: np.ndarray) -> dict[str, Any]:
    diff = np.diff(residuals)
    dw = np.sum(diff ** 2) / np.sum(residuals ** 2)

    if dw < 1.5:
        interpretation = "Autocorrelacao positiva"
    elif dw > 2.5:
        interpretation = "Autocorrelacao negativa"
    else:
        interpretation = "Sem autocorrelacao significativa"

    return {
        "durbin_watson": round(float(dw), 4),
        "interpretation": interpretation,
    }


def train_risk_predictor(
    df: pd.DataFrame,
    target: str = "crime_count",
    features: list[str] | None = None,
) -> dict[str, Any]:
    if features is None:
        features = [
            "lighting_density",
            "dist_nearest_lit",
            "bus_stop_density",
            "metro_density",
            "camera_count",
            "nightlife_density",
            "dist_nearest_metro",
        ]

    data = _prepare_numeric_df(df, [target] + features)
    if target not in data.columns:
        return {"error": "Target not found"}

    available = [c for c in data.columns if c != target]
    available = [
        c for c in available
        if data[c].std() > 1e-10 and data[c].nunique() > 1
    ]
    if len(available) < 2 or len(data) < 20:
        return {"error": "Dados insuficientes para modelo preditivo (< 20 obs ou < 2 features)"}

    X = data[available].values
    y = data[target].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42,
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    models = {
        "Random Forest": RandomForestRegressor(
            n_estimators=200, max_depth=12, random_state=42, n_jobs=-1,
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42,
        ),
    }

    results = {}
    best_model_name = None
    best_r2 = -float("inf")

    for name, model in models.items():
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)

        r2 = r2_score(y_test, y_pred)
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mae = float(mean_absolute_error(y_test, y_pred))

        cv_scores = cross_val_score(model, X_train_s, y_train, cv=5, scoring="r2")

        importances = model.feature_importances_
        feat_importance = [
            {"feature": available[i], "importance": round(float(importances[i]), 4)}
            for i in np.argsort(importances)[::-1]
        ]

        results[name] = {
            "r2_test": round(float(r2), 4),
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "r2_cv_mean": round(float(cv_scores.mean()), 4),
            "r2_cv_std": round(float(cv_scores.std()), 4),
            "feature_importance": feat_importance,
            "n_train": len(X_train),
            "n_test": len(X_test),
        }

        if r2 > best_r2:
            best_r2 = r2
            best_model_name = name

    best = results[best_model_name]
    y_pred_best = models[best_model_name].predict(X_test_s)

    residuals = y_test - y_pred_best

    logger.info(
        "Modelo preditivo: melhor={}, R2_test={:.3f}, RMSE={:.2f}",
        best_model_name,
        best["r2_test"],
        best["rmse"],
    )

    return {
        "best_model": best_model_name,
        "models": results,
        "residuals": residuals.tolist(),
        "y_test": y_test.tolist(),
        "y_pred": y_pred_best.tolist(),
        "feature_names": available,
    }


def cluster_crime_patterns(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    n_clusters: int = 4,
    dbscan_eps: float = 0.5,
    dbscan_min_samples: int = 5,
) -> dict[str, Any]:
    if feature_cols is None:
        feature_cols = [
            "crime_count",
            "lighting_density",
            "bus_stop_density",
            "metro_density",
            "camera_count",
            "nightlife_density",
        ]

    data = _prepare_numeric_df(df, feature_cols)
    if len(data.columns) < 2 or len(data) < 10:
        return {"error": "Dados insuficientes para clusterizacao (< 10 obs ou < 2 features)"}

    available = [c for c in data.columns if data[c].std() > 1e-10]
    if len(available) < 2:
        return {"error": "Colunas com variancia insuficiente"}

    X = data[available].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    inertia_range = []
    k_range = range(2, min(8, len(data) // 3 + 1))
    for k in k_range:
        km_temp = KMeans(n_clusters=k, random_state=42, n_init=10)
        km_temp.fit(X_scaled)
        inertia_range.append({"k": k, "inertia": round(float(km_temp.inertia_), 2)})

    actual_k = min(n_clusters, len(data) // 3)
    actual_k = max(actual_k, 2)
    kmeans = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    kmeans_labels = kmeans.fit_predict(X_scaled)

    db = DBSCAN(eps=dbscan_eps, min_samples=min(dbscan_min_samples, len(data) // 5 + 1))
    db_labels = db.fit_predict(X_scaled)
    n_db_clusters = len(set(db_labels)) - (1 if -1 in db_labels else 0)
    n_db_noise = int((db_labels == -1).sum())

    centroids = {}
    for c in range(actual_k):
        mask = kmeans_labels == c
        cluster_data = data[mask]
        centroids[f"Cluster {c}"] = {
            "size": int(mask.sum()),
            "means": {
                col: round(float(cluster_data[col].mean()), 4)
                for col in available
            },
        }

    silhouette = 0.0
    if actual_k >= 2 and len(data) > actual_k:
        from sklearn.metrics import silhouette_score
        silhouette = float(silhouette_score(X_scaled, kmeans_labels))

    result_df = (
        df[feature_cols].copy()
        if all(c in df.columns for c in feature_cols)
        else data.copy()
    )
    result_df = result_df.iloc[data.index].reset_index(drop=True)
    result_df["kmeans_cluster"] = kmeans_labels[:len(result_df)]
    result_df["dbscan_cluster"] = db_labels[:len(result_df)]

    cluster_names = {
        0: "Baixo risco",
        1: "Risco medio",
        2: "Alto risco",
        3: "Critico",
    }
    if actual_k <= len(cluster_names):
        mean_crimes = []
        for c in range(actual_k):
            mask = kmeans_labels == c
            mean_crimes.append((c, float(data.loc[data.index[mask], "crime_count"].mean())))
        mean_crimes.sort(key=lambda x: x[1])
        name_map = {}
        level_names = ["Baixo risco", "Risco moderado", "Alto risco", "Critico",
                       "Muito alto", "Extremo", "Severo"]
        for rank, (c, _) in enumerate(mean_crimes):
            name_map[c] = level_names[min(rank, len(level_names) - 1)]
        centroids_renamed = {}
        for c_str, vals in centroids.items():
            c_num = int(c_str.split()[-1])
            centroids_renamed[name_map.get(c_num, c_str)] = vals
        centroids = centroids_renamed

    logger.info(
        "Clusterizacao: K-Means k={}, silhouette={:.3f} | DBSCAN {} clusters, {} noise",
        actual_k,
        silhouette,
        n_db_clusters,
        n_db_noise,
    )

    return {
        "n_clusters_kmeans": actual_k,
        "n_clusters_dbscan": n_db_clusters,
        "n_noise_dbscan": n_db_noise,
        "silhouette_score": round(silhouette, 4),
        "centroids": centroids,
        "inertia_curve": inertia_range,
        "kmeans_labels": kmeans_labels.tolist(),
        "dbscan_labels": db_labels.tolist(),
        "feature_names": available,
    }


def compute_sinistrality_index(
    crime_count: int,
    population: int,
    period_years: float = 1.0,
) -> dict[str, Any]:
    if population <= 0:
        return {
            "sinistrality_index": 0.0,
            "rate_per_100k": 0.0,
            "crime_count": crime_count,
            "population": population,
            "period_years": period_years,
            "interpretation": "Populacao invalida",
        }

    rate = crime_count / period_years
    rate_per_100k = (rate / population) * 100_000

    if rate_per_100k > 5000:
        level = "Muito alto"
    elif rate_per_100k > 2000:
        level = "Alto"
    elif rate_per_100k > 1000:
        level = "Medio"
    elif rate_per_100k > 500:
        level = "Baixo"
    else:
        level = "Muito baixo"

    logger.info(
        "Sinistralidade: {:.1f} crimes/100k hab ({} em {} hab)",
        rate_per_100k,
        crime_count,
        population,
    )

    return {
        "sinistrality_index": round(float(rate_per_100k), 2),
        "rate_per_100k": round(float(rate_per_100k), 2),
        "crime_count": crime_count,
        "population": population,
        "period_years": period_years,
        "level": level,
    }


def compute_sinistrality_by_category(
    df: pd.DataFrame,
    population: int,
    category_col: str = "crime_category",
    period_years: float = 1.0,
) -> dict[str, Any]:
    if population <= 0:
        return {"error": "Populacao invalida"}

    if category_col not in df.columns:
        return {"error": f"Coluna '{category_col}' nao encontrada"}

    results = {}
    for cat, count in df[category_col].value_counts().items():
        results[cat] = compute_sinistrality_index(
            int(count), population, period_years,
        )

    total = compute_sinistrality_index(len(df), population, period_years)

    return {
        "by_category": results,
        "total": total,
    }
