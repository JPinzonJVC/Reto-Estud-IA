"""Enrutador para endpoints del módulo de analítica."""

from typing import Any

from fastapi import APIRouter

analytics_router = APIRouter(
    prefix="/analytics",
    tags=["Analítica"],
)


@analytics_router.get("/metrics", status_code=200)
def get_analytics_metrics() -> dict[str, Any]:
    """Retorna métricas cuantitativas globales de comportamiento de usuarios.

    Returns:
        Diccionario con indicadores de sesiones, conversiones y actividad.

    """
    return {
        "daily_active_users": 3420,
        "weekly_retention_rate": 0.82,
        "conversion_funnel": {
            "views": 15000,
            "signups": 2100,
            "active_subscriptions": 1450,
        },
    }
