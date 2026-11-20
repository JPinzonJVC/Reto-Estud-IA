"""Enrutador para endpoints del módulo de analítica."""

from typing import Any

from fastapi import APIRouter

from app.modules.analytics.service import AnalyticsService

analytics_router = APIRouter(
    prefix="/analytics",
    tags=["Analítica"],
)

analytics_service = AnalyticsService()


@analytics_router.get("/metrics", status_code=200)
def get_analytics_metrics() -> dict[str, Any]:
    """Retorna métricas cuantitativas globales de comportamiento y capa Gold.

    Returns:
        Diccionario con indicadores de participación, satisfacción y actividad.

    """
    return analytics_service.get_metrics()


@analytics_router.get("/satisfaction", status_code=200)
def get_analytics_satisfaction() -> list[dict[str, Any]]:
    """Retorna la agregación Gold de satisfacción de encuestas por modalidad y mes.

    Returns:
        Lista de registros de agg_satisfaccion_encuestas.

    """
    return analytics_service.get_satisfaction_breakdown()
