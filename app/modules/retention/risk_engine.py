"""Motor de evaluación de riesgo y priorización de acciones de retención."""

from typing import Any

from app.modules.machine_learning.prediction import predict_churn


def evaluate_risk_level(churn_probability: float) -> str:
    """Clasifica el nivel de riesgo según el umbral de probabilidad de fuga.

    Args:
        churn_probability: Valor decimal entre 0 y 1 con la probabilidad.

    Returns:
        Etiqueta de riesgo: 'Bajo', 'Medio', 'Alto' o 'Crítico'.

    """
    if churn_probability < 0.25:
        return "Bajo"
    if churn_probability < 0.50:
        return "Medio"
    if churn_probability < 0.75:
        return "Alto"
    return "Crítico"


def recommend_retention_action(risk_level: str, cluster_id: int) -> str:
    """Sugiere una acción comercial personalizada según el riesgo y segmento.

    Args:
        risk_level: Nivel de riesgo ('Bajo', 'Medio', 'Alto', 'Crítico').
        cluster_id: Identificador del segmento del cliente.

    Returns:
        Descripción de la estrategia de retención recomendada.

    """
    if risk_level in ("Alto", "Crítico"):
        if cluster_id == 1:
            return "Oferta personalizada de fidelización VIP con descuento"
        return "Contacto proactivo de soporte y asesoría prioritaria"
    if risk_level == "Medio":
        return "Campaña de nutrición por correo electrónico con incentivos"
    return "Monitoreo pasivo y encuestas de satisfacción periódicas"


def assess_customer_profile(
    customer_id: str,
    features: list[float],
    cluster_id: int = 0,
) -> dict[str, Any]:
    """Evalúa de forma integral el perfil de riesgo de un cliente.

    Args:
        customer_id: Identificador único del cliente analizado.
        features: Lista de predictores cuantitativos.
        cluster_id: Identificador del segmento KMeans.

    Returns:
        Diccionario con métricas de probabilidad, nivel de riesgo y acción.

    """
    prediction_result = predict_churn(features)
    prob = float(prediction_result["churn_probability"])
    risk = evaluate_risk_level(prob)
    action = recommend_retention_action(risk, cluster_id)

    return {
        "customer_id": customer_id,
        "churn_probability": prob,
        "risk_level": risk,
        "cluster_id": cluster_id,
        "recommended_action": action,
    }
