"""Rutinas de entrenamiento y persistencia de modelos de Machine Learning."""

from pathlib import Path
from typing import Any

try:
    import joblib
except ImportError:
    import pickle as joblib  # type: ignore[no-redef]

import numpy as np

try:
    from sklearn.cluster import KMeans
    from sklearn.linear_model import LogisticRegression
except ImportError:
    KMeans = Any  # type: ignore[assignment,misc]
    LogisticRegression = Any  # type: ignore[assignment,misc]

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
    dummy_x = np.array([[10, 2], [20, 5], [5, 1], [30, 8], [15, 3]], dtype=float)
    dummy_y = np.array([0, 1, 0, 1, 0])

    churn_mdl = train_churn_model(dummy_x, dummy_y)
    save_model(churn_mdl, "churn_model.pkl")

    cluster_mdl = train_clustering_model(dummy_x, n_clusters=2)
    save_model(cluster_mdl, "clustering_model.pkl")


if __name__ == "__main__":
    bootstrap_default_models()
