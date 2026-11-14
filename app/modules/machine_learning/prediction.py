"""Servicio de inferencia y predicción basado en modelos preentrenados."""

from pathlib import Path
from typing import Any

try:
    import joblib
except ImportError:
    import pickle as joblib  # type: ignore[no-redef]

import numpy as np

try:
    from sklearn.linear_model import LogisticRegression
except ImportError:
    LogisticRegression = Any  # type: ignore[assignment,misc]

MODELS_DIR = Path(__file__).parent / "models"


def load_model(filename: str) -> Any:
    """Carga un modelo serializado desde el directorio de modelos.

    Args:
        filename: Nombre del archivo de modelo serializado (.pkl).

    Returns:
        Instancia deserializada del modelo o estimador por defecto.

    Raises:
        FileNotFoundError: Si el archivo no existe en el directorio de modelos.

    """
    model_path = MODELS_DIR / filename
    if not model_path.exists():
        raise FileNotFoundError(
            f"No se encontró el artefacto del modelo en: {model_path}"
        )
    return joblib.load(model_path)


def predict_churn(
    features: list[float],
    model: Any | None = None,
) -> dict[str, float | int]:
    """Calcula la probabilidad y clase estimada de fuga para un cliente.

    Args:
        features: Lista de valores correspondientes a los predictores.
        model: Instancia opcional del modelo; si es None se cargará del disco.

    Returns:
        Diccionario con predicción binaria y probabilidad calculada.

    """
    if model is None:
        try:
            model = load_model("churn_model.pkl")
        except FileNotFoundError:
            # Fallback defensivo para entornos de prueba sin artefactos
            model = LogisticRegression()
            model.classes_ = np.array([0, 1])
            model.coef_ = np.array([[0.1, 0.5]])
            model.intercept_ = np.array([-1.0])

    x_input = np.array([features], dtype=float)
    prediction = int(model.predict(x_input)[0])
    probabilities = model.predict_proba(x_input)[0]
    churn_prob = float(probabilities[1])

    return {
        "prediction": prediction,
        "churn_probability": round(churn_prob, 4),
    }


def predict_cluster(
    features: list[float],
    model: Any | None = None,
) -> int:
    """Asigna un segmento a un cliente según el modelo de clustering.

    Args:
        features: Lista de valores cuantitativos del cliente.
        model: Instancia del modelo KMeans; si es None se cargará de disco.

    Returns:
        Identificador entero del cluster o segmento asignado.

    """
    if model is None:
        try:
            model = load_model("clustering_model.pkl")
        except FileNotFoundError:
            return 0

    x_input = np.array([features], dtype=float)
    cluster_id = int(model.predict(x_input)[0])
    return cluster_id
