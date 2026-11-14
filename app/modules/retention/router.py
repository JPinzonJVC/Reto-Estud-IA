"""Enrutador de API y vistas para el módulo de retención."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.modules.retention.service import RetentionService

retention_router = APIRouter(
    prefix="/retention",
    tags=["Retención de Clientes"],
)

service = RetentionService()


class CustomerEvaluationRequest(BaseModel):
    """Esquema de solicitud para evaluar el riesgo de un cliente."""

    customer_id: str
    """Identificador alfanumérico del cliente."""

    features: list[float]
    """Vector de características numéricas para el modelo predictivo."""

    model_config = ConfigDict(from_attributes=True)


@retention_router.get("/overview", status_code=200)
def get_overview() -> dict[str, Any]:
    """Obtiene el resumen general de indicadores de retención.

    Returns:
        Diccionario con indicadores clave de retención y clientes en riesgo.

    """
    return service.get_retention_overview()


@retention_router.post("/evaluate", status_code=200)
def evaluate_customer(payload: CustomerEvaluationRequest) -> dict[str, Any]:
    """Evalúa el nivel de riesgo de fuga de un cliente específico.

    Args:
        payload: Objeto con customer_id y lista de predictores.

    Returns:
        Resultado del análisis de riesgo con recomendaciones personalizadas.

    """
    return service.analyze_customer(
        customer_id=payload.customer_id,
        features=payload.features,
    )
