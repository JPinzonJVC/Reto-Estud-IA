"""Pruebas del score RFM-S y evaluación de segmentación descriptiva."""

import pandas as pd
import pytest

from app.modules.eda.ml.fidelity.features import (
    COMMUNITY_COLUMNS,
    RFM_COMPONENTS,
    build_rfm_s_features,
    get_complete_rfm_s_cohort,
)
from app.modules.eda.ml.fidelity.predict import predict_fidelity_clusters
from app.modules.eda.ml.fidelity.train import (
    evaluate_fidelity_candidates,
    train_fidelity_model,
)


def _fidelity_frame(rows: int = 30) -> pd.DataFrame:
    """Crea datos deterministas solo para pruebas unitarias."""
    frame = pd.DataFrame(
        {
            "id_empresa": [f"EMP-{index:04}" for index in range(rows)],
            "dias_sin_participacion": [index * 10 for index in range(rows)],
            "total_eventos_anio": [index % 8 for index in range(rows)],
            "total_asistencias_anio": [index % 10 for index in range(rows)],
            "personas_distintas_anio": [index % 5 for index in range(rows)],
            "total_ciclos_membresia": [index % 6 for index in range(rows)],
            "satisfaccion_promedio_1_5": [1.0 + (index % 5) for index in range(rows)],
        }
    )
    for column in COMMUNITY_COLUMNS:
        frame[column] = [index % 2 == 0 for index in range(rows)]
    return frame


def test_rfm_s_score_uses_observed_satisfaction_only() -> None:
    """No asigna score RFM-S a empresas sin satisfacción observada."""
    frame = _fidelity_frame()
    frame.loc[0:20, "satisfaccion_promedio_1_5"] = None
    result = build_rfm_s_features(frame)

    assert result.loc[0:20, "score_fidelidad_ml_0_100"].isna().all()
    assert result.loc[21:, "score_fidelidad_ml_0_100"].between(0, 100).all()
    assert len(get_complete_rfm_s_cohort(result)) == 9


def test_rfm_s_rejects_missing_satisfaction_for_all_companies() -> None:
    """Detiene el cálculo cuando la dimensión S no tiene valores observados."""
    frame = _fidelity_frame()
    frame["satisfaccion_promedio_1_5"] = None

    with pytest.raises(ValueError, match="No hay satisfacción observada"):
        build_rfm_s_features(frame)


def test_cluster_candidates_report_stability_and_quality_metrics() -> None:
    """Compara ambos algoritmos y reporta estabilidad entre semillas."""
    features = build_rfm_s_features(_fidelity_frame())
    cohort = get_complete_rfm_s_cohort(features)
    result = evaluate_fidelity_candidates(cohort, cluster_counts=(2,))

    assert {item["algorithm"] for item in result} == {"kmeans", "gaussian_mixture"}
    assert all(item["seeds_evaluated"] == 5 for item in result)
    assert all(0.0 <= item["ari_stability_mean"] <= 1.0 for item in result)
    assert all(set(RFM_COMPONENTS).issubset(cohort.columns) for _ in result)


def test_fidelity_inference_preserves_score_and_returns_cluster() -> None:
    """Mantiene separada la inferencia y exige features en escala conocida."""
    features = build_rfm_s_features(_fidelity_frame())
    cohort = get_complete_rfm_s_cohort(features)
    model = train_fidelity_model(cohort, algorithm="kmeans", clusters=2)

    predictions = predict_fidelity_clusters(cohort, model=model)

    assert len(predictions) == len(cohort)
    assert predictions["score_fidelidad_ml_0_100"].between(0, 100).all()
    assert predictions["cluster_id"].nunique() == 2
