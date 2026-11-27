"""Rutinas de entrenamiento y persistencia de modelos de Machine Learning."""

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression

MODELS_DIR = Path(__file__).parent / "models"


def train_churn_model(
    x_train: np.ndarray,
    y_train: np.ndarray,
) -> LogisticRegression:
    """Entrena un modelo de clasificación para predecir fuga (churn).

    Args:
        x_train: Matriz con las variables predictoras procesadas.
        y_train: Vector binario con las etiquetas objetivo de fuga.

    Returns:
        Instancia entrenada del modelo de regresión logística.

    """
    model = LogisticRegression(random_state=42, max_iter=200)
    model.fit(x_train, y_train)
    return model


def train_clustering_model(
    x_train: np.ndarray,
    n_clusters: int = 3,
) -> KMeans:
    """Entrena un modelo no supervisado KMeans para segmentación.

    Args:
        x_train: Matriz de características cuantitativas.
        n_clusters: Cantidad de grupos a formar en la segmentación.

    Returns:
        Instancia entrenada de KMeans.

    """
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans.fit(x_train)
    return kmeans


def save_model(model: Any, filename: str) -> Path:
    """Guarda un modelo entrenado en formato joblib/pickle en disco.

    Args:
        model: Objeto del estimador entrenado compatible con pickle.
        filename: Nombre del archivo de destino con extensión .pkl.

    Returns:
        Ruta absoluta donde quedó almacenado el artefacto.

    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    destination = MODELS_DIR / filename
    joblib.dump(model, destination)
    return destination


def bootstrap_default_models() -> None:
    """Genera artefactos de modelo básicos para desarrollo y pruebas."""
    raise RuntimeError(
        "Bootstrap deshabilitado: los datos sintéticos no son modelos de producción."
    )


if __name__ == "__main__":
    bootstrap_default_models()
