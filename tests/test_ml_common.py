"""Pruebas para validaciones y componentes comunes de Machine Learning."""

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.modules.eda.ml.common.metrics import evaluate_binary_predictions
from app.modules.eda.ml.common.preprocessing import build_tabular_preprocessor
from app.modules.eda.ml.common.temporal import split_by_time
from app.modules.eda.ml.common.validation import (
    DatasetValidationError,
    validate_probabilities,
    validate_supervised_dataset,
)


def _valid_temporal_frame() -> pd.DataFrame:
    """Crea una muestra sintética solo para probar contratos, no para entrenar ACTHO."""
    return pd.DataFrame(
        {
            "company_id": ["A", "B", "C", "D", "E", "F", "G", "H"],
            "observed_at": [
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
                "2024-02-01",
                "2024-02-02",
                "2024-02-03",
                "2024-02-04",
            ],
            "usage": [1, 2, 3, 4, 5, 6, 7, 8],
            "segment": ["a", "b", "a", "b", "a", "b", "a", "b"],
            "target": [0, 1, 0, 1, 0, 1, 0, 1],
        }
    )


def test_validate_supervised_dataset_rejects_duplicate_keys() -> None:
    """Evita observaciones repetidas en la granularidad declarada."""
    frame = _valid_temporal_frame()
    frame.loc[1, "company_id"] = "A"

    with pytest.raises(DatasetValidationError, match="duplicados"):
        validate_supervised_dataset(
            frame,
            feature_columns=["usage"],
            target_column="target",
            key_columns=["company_id"],
        )


def test_validate_supervised_dataset_rejects_unverified_labels() -> None:
    """No permite nulos ni una sola clase en la etiqueta."""
    frame = _valid_temporal_frame()
    frame.loc[0, "target"] = np.nan

    with pytest.raises(DatasetValidationError, match="nulos"):
        validate_supervised_dataset(
            frame,
            feature_columns=["usage"],
            target_column="target",
        )


def test_temporal_split_keeps_future_rows_out_of_train() -> None:
    """Ubica el corte temporal entre particiones sin mezclar fechas futuras."""
    frame = _valid_temporal_frame()
    split = split_by_time(
        frame,
        date_column="observed_at",
        cutoff="2024-02-01",
        feature_columns=["usage", "segment"],
        target_column="target",
        key_columns=["company_id"],
    )

    assert split.train["observed_at"].max() < split.cutoff
    assert split.validation["observed_at"].min() >= split.cutoff
    assert set(split.train["company_id"]).isdisjoint(split.validation["company_id"])


def test_tabular_preprocessor_fits_inside_pipeline() -> None:
    """El pipeline soporta nulos y categorías desconocidas en inferencia."""
    frame = _valid_temporal_frame()
    frame.loc[0, "usage"] = np.nan
    pipeline = Pipeline(
        steps=[
            (
                "preprocess",
                build_tabular_preprocessor(
                    numeric_features=["usage"],
                    categorical_features=["segment"],
                ),
            ),
            ("estimator", LogisticRegression(random_state=42)),
        ]
    )
    pipeline.fit(frame.loc[:5, ["usage", "segment"]], frame.loc[:5, "target"])

    probabilities = pipeline.predict_proba(
        pd.DataFrame({"usage": [9.0], "segment": ["new_category"]})
    )
    assert probabilities.shape == (1, 2)


def test_probability_validation_and_binary_metrics() -> None:
    """Valida el rango de probabilidades y produce métricas requeridas."""
    report = evaluate_binary_predictions(
        np.array([0, 0, 1, 1]), np.array([0.1, 0.4, 0.6, 0.9])
    )

    assert report["roc_auc"] == 1.0
    assert report["pr_auc"] == 1.0
    assert "brier_score" in report
    assert len(report["confusion_matrix"]) == 2
    with pytest.raises(DatasetValidationError):
        validate_probabilities(np.array([0.2, np.nan]))
