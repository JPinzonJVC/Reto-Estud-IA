"""Validaciones comunes para datasets y resultados de Machine Learning."""

from collections.abc import Sequence

import numpy as np
import pandas as pd


class DatasetValidationError(ValueError):
    """Error al incumplir el contrato de un dataset de Machine Learning."""


def validate_supervised_dataset(
    frame: pd.DataFrame,
    *,
    feature_columns: Sequence[str],
    target_column: str,
    key_columns: Sequence[str] = (),
    minimum_per_class: int = 2,
) -> None:
    """Valida columnas, llaves y clases antes de ajustar un estimador.

    Args:
        frame: Dataset tabular con features y etiqueta ya resuelta.
        feature_columns: Lista explícita de variables predictoras permitidas.
        target_column: Columna binaria objetivo.
        key_columns: Columnas que identifican una observación.
        minimum_per_class: Observaciones mínimas requeridas por cada clase.

    Raises:
        DatasetValidationError: Si falta una columna, hay llaves duplicadas o una
            clase no alcanza el tamaño mínimo.
    """
    required = set(feature_columns) | {target_column} | set(key_columns)
    missing = sorted(required - set(frame.columns))
    if missing:
        raise DatasetValidationError(f"Faltan columnas requeridas: {missing}")
    if frame.empty:
        raise DatasetValidationError("El dataset está vacío.")
    if not feature_columns:
        raise DatasetValidationError("Debe definirse al menos una feature.")
    if frame[target_column].isna().any():
        raise DatasetValidationError("La etiqueta contiene valores nulos o censurados.")

    classes = set(frame[target_column].unique())
    if not classes.issubset({0, 1}) or len(classes) != 2:
        raise DatasetValidationError(
            "La etiqueta debe contener ambas clases binarias 0 y 1."
        )

    counts = frame[target_column].value_counts()
    if int(counts.min()) < minimum_per_class:
        raise DatasetValidationError(
            f"Cada clase requiere al menos {minimum_per_class} observaciones."
        )
    if key_columns and frame.duplicated(list(key_columns)).any():
        raise DatasetValidationError("La llave de observación contiene duplicados.")


def validate_probabilities(values: Sequence[float] | np.ndarray) -> None:
    """Rechaza scores de probabilidad nulos, infinitos o fuera de [0, 1]."""
    probabilities = np.asarray(values, dtype=float)
    if probabilities.size == 0:
        raise DatasetValidationError("No se recibieron probabilidades.")
    if not np.isfinite(probabilities).all():
        raise DatasetValidationError("Las probabilidades deben ser valores finitos.")
    if ((probabilities < 0.0) | (probabilities > 1.0)).any():
        raise DatasetValidationError("Las probabilidades deben estar entre 0 y 1.")
