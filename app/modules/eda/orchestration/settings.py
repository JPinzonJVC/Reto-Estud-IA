"""Configuración del orquestador Prefect parametrizada por variables de entorno."""

from app.env_vars import (
    DEFAULT_TIMEZONE,
    DEFAULT_WEEKLY_CRON,
    OrchestrationEnvs,
)

OrchestrationSettings = OrchestrationEnvs

__all__ = [
    "DEFAULT_TIMEZONE",
    "DEFAULT_WEEKLY_CRON",
    "OrchestrationEnvs",
    "OrchestrationSettings",
]
