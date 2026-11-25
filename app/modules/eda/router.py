"""Enrutador FastAPI para el monitor visual de Prefect y salidas del ETL Medallion."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.eda.monitor_service import EtlMonitorService

eda_monitor_router = APIRouter(
    prefix="/etl/monitor",
    tags=["Orquestación Prefect & ETL"],
)


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
