"""Enrutador FastAPI para el monitor visual de Prefect y salidas del ETL Medallion."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.eda.monitor_service import EtlMonitorService, actualizar_cron_prefect

eda_monitor_router = APIRouter(
    prefix="/etl/monitor",
    tags=["Orquestación Prefect & ETL"],
)


class ScheduleUpdateRequest(BaseModel):
    """Solicitud para actualizar el cron del deployment activo en Prefect."""

    cron: str
    """Expresión cron de 5 campos (ej. '*/5 * * * *' o '0 6 * * 1')."""

    timezone: str | None = None
    """Zona horaria IANA opcional (ej. 'America/Bogota')."""


@eda_monitor_router.put("/schedule")
def update_etl_schedule(payload: ScheduleUpdateRequest) -> dict[str, Any]:
    """Actualiza el cron del deployment de Prefect directamente desde el frontend.

    Args:
        payload: Objeto con la nueva expresión cron y zona horaria opcional.

    Returns:
        Confirmación con el nuevo cron, etiqueta legible y próxima ejecución.

    Raises:
        HTTPException: 400 si el cron es inválido o 503 si Prefect no responde.

    """
    try:
        return actualizar_cron_prefect(payload.cron, payload.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@eda_monitor_router.get("/status")
def get_etl_monitor_status(
    run_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna el estado actual del flujo Prefect, etapas ETL y programación.

    Args:
        run_id: Identificador opcional de una ejecución ETL histórica a inspeccionar.
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Estado del flujo, tiempos, etapas de ejecución, historial y resumen de calidad.

    """
    return EtlMonitorService(db).obtener_estado_pipeline(run_id=run_id)


@eda_monitor_router.get("/step-output")
def get_etl_step_output(
    output_key: str = Query(..., description="Nombre de tabla SQL o fuente watermark"),
    output_type: str = Query(default="table", description="'table' o 'watermark'"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Consulta la salida real de un paso del ETL (muestra de filas y auditoría).

    Args:
        output_key: Nombre de la tabla destino Medallion o fuente watermark.
        output_type: Tipo de salida ('table' o 'watermark').
        limit: Máximo de filas de muestra a devolver.
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Conteo total, muestra de columnas/filas, reglas de calidad y reconciliación.

    Raises:
        HTTPException: Si la tabla solicitada no pertenece al catálogo Medallion.

    """
    try:
        return EtlMonitorService(db).obtener_salida_etapa(
            output_key=output_key,
            output_type=output_type,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
