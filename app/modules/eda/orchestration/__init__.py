"""Paquete de orquestación Prefect para el pipeline EDA Medallion."""

from typing import Any

from app.modules.eda.orchestration.settings import OrchestrationSettings

__all__ = [
    "OrchestrationSettings",
    "eda_medallion_flow",
    "serve_eda_pipeline",
]


def __getattr__(name: str) -> Any:
    """Carga los flujos bajo demanda sin interferir con ``python -m``.

    Al ejecutar ``python -m app.modules.eda.orchestration.flows``, Python carga
    primero este paquete. Importar ``flows`` aquí de forma ansiosa hacía que el
    módulo ya existiera en ``sys.modules`` antes de ejecutarse como principal.
    """
    if name in {"eda_medallion_flow", "serve_eda_pipeline"}:
        from app.modules.eda.orchestration import flows

        return getattr(flows, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
