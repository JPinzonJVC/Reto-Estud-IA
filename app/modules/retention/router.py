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
    """Obtiene el resumen general de indicadores de retención desde la capa Gold.

    Returns:
        Diccionario con indicadores clave de retención y empresas en riesgo.

    """
    return service.get_retention_overview()


@retention_router.get("/companies", status_code=200)
def get_retention_companies(
    semaforo: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    """Lista las empresas de agg_retencion_empresa según su semáforo de riesgo.

    Args:
        semaforo: Categoría opcional del semáforo heurístico.
        limit: Cantidad máxima de empresas a retornar.

    Returns:
        Lista de registros de retención por empresa.

    """
    return service.get_companies_by_risk(semaforo=semaforo, limit=limit)


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
