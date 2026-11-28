"""Comparación temporalmente agnóstica de clustering descriptivo RFM-S."""

import json
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.database import get_session_factory
from app.modules.eda.ml.fidelity.dataset import load_fidelity_dataset
from app.modules.eda.ml.fidelity.features import (
    RFM_COMPONENTS,
    build_rfm_s_features,
    get_complete_rfm_s_cohort,
)

RANDOM_STATES = (42, 43, 44, 45, 46)


def build_fidelity_pipeline(algorithm: str, clusters: int, seed: int) -> Pipeline:
    """Crea un estimador reproducible para una solución de fidelidad candidata."""
    if clusters < 2:
        raise ValueError("Se requieren al menos dos clusters.")
    if algorithm == "kmeans":
        estimator = KMeans(n_clusters=clusters, random_state=seed, n_init=20)
    elif algorithm == "gaussian_mixture":
        estimator = GaussianMixture(
            n_components=clusters,
            covariance_type="full",
            random_state=seed,
            reg_covar=1e-5,
            n_init=3,
        )
    else:
        raise ValueError(f"Algoritmo de fidelidad no soportado: {algorithm}")
    return Pipeline([("scale", StandardScaler()), ("cluster", estimator)])


def train_fidelity_model(
    cohort: pd.DataFrame,
    *,
    algorithm: str,
    clusters: int,
    seed: int = 42,
) -> Pipeline:
    """Ajusta una solución RFM-S candidata sin escribir artefactos ni Gold."""
    if len(cohort) < 20:
        raise ValueError("Se requieren al menos 20 empresas para entrenar clusters.")
    model = build_fidelity_pipeline(algorithm, clusters, seed)
    model.fit(cohort[list(RFM_COMPONENTS)].astype(float))
    return model


def evaluate_fidelity_candidates(
    cohort: pd.DataFrame,
    *,
    cluster_counts: tuple[int, ...] = (2, 3, 4, 5, 6),
) -> list[dict[str, Any]]:
    """Mide calidad geométrica e indicadores de estabilidad por semilla.

    La estabilidad aquí compara soluciones sobre la misma cohorte al variar
    `random_state`; no reemplaza un análisis de estabilidad por bootstrap temporal.
    """
    if len(cohort) < 20:
        raise ValueError("Se requieren al menos 20 empresas para evaluar clusters.")
    features = cohort[list(RFM_COMPONENTS)].astype(float)
    reports: list[dict[str, Any]] = []

    for algorithm in ("kmeans", "gaussian_mixture"):
        for clusters in cluster_counts:
            if clusters >= len(cohort):
                continue
            labels_by_seed: list[np.ndarray] = []
            silhouettes: list[float] = []
            davies_bouldin: list[float] = []
            calinski_harabasz: list[float] = []
            for seed in RANDOM_STATES:
                pipeline = build_fidelity_pipeline(algorithm, clusters, seed)
                labels = pipeline.fit_predict(features)
                if len(np.unique(labels)) < 2 or len(np.unique(labels)) >= len(labels):
                    continue
                labels_by_seed.append(labels)
                scaled = pipeline.named_steps["scale"].transform(features)
                silhouettes.append(float(silhouette_score(scaled, labels)))
                davies_bouldin.append(float(davies_bouldin_score(scaled, labels)))
                calinski_harabasz.append(float(calinski_harabasz_score(scaled, labels)))

            if not labels_by_seed:
                continue
            stability = [
                adjusted_rand_score(labels_by_seed[left], labels_by_seed[right])
                for left, right in combinations(range(len(labels_by_seed)), 2)
            ]
            reports.append(
                {
                    "algorithm": algorithm,
                    "clusters": clusters,
                    "n_companies": int(len(cohort)),
                    "silhouette_mean": float(np.mean(silhouettes)),
                    "davies_bouldin_mean": float(np.mean(davies_bouldin)),
                    "calinski_harabasz_mean": float(np.mean(calinski_harabasz)),
                    "ari_stability_mean": (
                        float(np.mean(stability)) if stability else 1.0
                    ),
                    "seeds_evaluated": len(labels_by_seed),
                }
            )
    return sorted(
        reports,
        key=lambda item: (
            item["silhouette_mean"],
            item["ari_stability_mean"],
        ),
        reverse=True,
    )


def summarize_cluster_profiles(
    cohort: pd.DataFrame,
    *,
    algorithm: str,
    clusters: int,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Resume tamaños y promedios RFM-S sin divulgar identificadores de empresas."""
    pipeline = build_fidelity_pipeline(algorithm, clusters, seed)
    features = cohort[list(RFM_COMPONENTS)].astype(float)
    labels = pipeline.fit_predict(features)
    profiled = features.copy()
    profiled["cluster"] = labels
    grouped = profiled.groupby("cluster")[list(RFM_COMPONENTS)].agg(["mean", "median"])
    sizes = profiled["cluster"].value_counts().sort_index()
    profiles: list[dict[str, Any]] = []
    for cluster_id in grouped.index:
        cid_num = int(str(cluster_id))
        profile: dict[str, Any] = {
            "cluster_id": cid_num,
            "companies": int(sizes.loc[cluster_id]),
        }
        for component in RFM_COMPONENTS:
            profile[f"{component}_mean"] = round(
                float(grouped.loc[cluster_id, (component, "mean")]), 2
            )
            profile[f"{component}_median"] = round(
                float(grouped.loc[cluster_id, (component, "median")]), 2
            )
        profiles.append(profile)
    return profiles


def run_fidelity_audit() -> dict[str, Any]:
    """Construye el score candidato y evalúa clusters sin persistir en Gold."""
    session_factory = get_session_factory()
    with session_factory() as db:
        raw = load_fidelity_dataset(db)
    features = build_rfm_s_features(raw)
    cohort = get_complete_rfm_s_cohort(features)
    candidates = evaluate_fidelity_candidates(cohort)
    best_candidate = candidates[0] if candidates else None
    profiles = (
        summarize_cluster_profiles(
            cohort,
            algorithm=str(best_candidate["algorithm"]),
            clusters=int(best_candidate["clusters"]),
        )
        if best_candidate
        else []
    )
    return {
        "active_companies": int(len(raw)),
        "satisfaction_coverage": round(
            float(raw["satisfaccion_promedio_1_5"].notna().mean()), 4
        ),
        "rfm_s_score_coverage": int(features["score_fidelidad_ml_0_100"].notna().sum()),
        "cluster_cohort": int(len(cohort)),
        "nps_coverage": round(float(raw["nps_reciente_0_10"].notna().mean()), 4),
        "best_candidate": best_candidate,
        "cluster_profiles": profiles,
        "candidates": candidates,
        "approval_status": "EXPLORATORY_NOT_APPROVED",
        "persistence": "none",
    }


if __name__ == "__main__":
    print(json.dumps(run_fidelity_audit(), indent=2))
