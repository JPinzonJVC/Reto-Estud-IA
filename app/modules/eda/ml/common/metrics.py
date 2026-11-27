"""Métricas comunes para evaluación binaria fuera de muestra."""

from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from app.modules.eda.ml.common.validation import validate_probabilities


def evaluate_binary_predictions(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Calcula métricas de clase y calibración para probabilidades fuera de muestra.

    Args:
        y_true: Etiquetas binarias verificadas.
        probabilities: Probabilidad de la clase positiva para cada observación.
        threshold: Umbral de decisión documentado para derivar la clase.

    Returns:
        Métricas serializables, incluyendo precisión, recall, F1, ROC/PR-AUC,
        Brier score y matriz de confusión.
    """
    raw_labels = np.asarray(y_true)
    scores = np.asarray(probabilities, dtype=float)
    if raw_labels.ndim != 1 or scores.ndim != 1 or len(raw_labels) != len(scores):
        raise ValueError(
            "Etiquetas y probabilidades deben ser vectores del mismo tamaño."
        )
    if not set(np.unique(raw_labels)).issubset({0, 1}):
        raise ValueError("Las etiquetas de evaluación deben ser binarias (0 o 1).")
    labels = raw_labels.astype(int)
    if len(labels) == 0 or set(np.unique(labels)) != {0, 1}:
        raise ValueError("La evaluación requiere ambas clases binarias observadas.")
    if not 0.0 < threshold < 1.0:
        raise ValueError("El umbral debe estar estrictamente entre 0 y 1.")
    validate_probabilities(scores)

    predicted = (scores >= threshold).astype(int)
    matrix = confusion_matrix(labels, predicted, labels=[0, 1])
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(labels, predicted, zero_division=0)),
        "recall": float(recall_score(labels, predicted, zero_division=0)),
        "f1": float(f1_score(labels, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "pr_auc": float(average_precision_score(labels, scores)),
        "brier_score": float(brier_score_loss(labels, scores)),
        "confusion_matrix": matrix.tolist(),
        "n_samples": int(len(labels)),
    }
