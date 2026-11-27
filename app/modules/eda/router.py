"""Enrutador FastAPI para ejecutar el ETL y monitorear la orquestación en Prefect."""

from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.eda.monitor_service import (
    EtlMonitorService,
    actualizar_cron_prefect,
    disparar_corrida_prefect,
)
from app.modules.eda.schemas import (
    EtlRunAcceptedResponse,
    EtlRunRequest,
    EtlRunSummary,
)
from app.modules.eda.service import (
    EtlAlreadyRunningError,
    EtlInputNotFoundError,
    EtlRunNotFoundError,
    EtlService,
)

eda_router = APIRouter(
    prefix="/etl",
    tags=["Orquestación Prefect & ETL"],
)

etl_service = EtlService()


class ScheduleUpdateRequest(BaseModel):
    """Solicitud para actualizar el cron del deployment activo en Prefect."""

    cron: str
    """Expresión cron de 5 campos (ej. '*/5 * * * *' o '0 6 * * 1')."""

    timezone: str | None = None
    """Zona horaria IANA opcional (ej. 'America/Bogota')."""

    model_config = ConfigDict(from_attributes=True)


@eda_router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EtlRunAcceptedResponse,
)
def run_etl_pipeline(
    background_tasks: BackgroundTasks,
    request: EtlRunRequest = Body(default_factory=EtlRunRequest),
) -> EtlRunAcceptedResponse:
    """Inicia la ejecución del pipeline ETL Medallion en segundo plano."""
    try:
        return etl_service.iniciar_ejecucion(request, background_tasks)
    except EtlAlreadyRunningError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except EtlInputNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@eda_router.get(
    "/runs",
    status_code=status.HTTP_200_OK,
    response_model=list[EtlRunSummary],
)
def list_etl_runs() -> list[EtlRunSummary]:
    """Lista el historial de ejecuciones del pipeline ETL."""
    return etl_service.listar_ejecuciones()


@eda_router.get(
    "/runs/{run_id}",
    status_code=status.HTTP_200_OK,
    response_model=EtlRunSummary,
)
def get_etl_run(run_id: str) -> EtlRunSummary:
    """Consulta el estado y métricas de una ejecución ETL por su identificador."""
    try:
        return etl_service.obtener_ejecucion(run_id)
    except EtlRunNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@eda_router.get("/monitor/status")
def get_etl_monitor_status(
    run_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna el estado en vivo del flujo Prefect, etapas DWH y programación."""
    return EtlMonitorService(db).obtener_estado_pipeline(run_id=run_id)


@eda_router.get("/monitor/step-output")
def get_etl_step_output(
    output_key: str = Query(..., description="Tabla SQL o fuente watermark"),
    output_type: str = Query(default="table", description="'table' o 'watermark'"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Consulta la salida real de una etapa del DWH (muestra, calidad y cuadre)."""
    try:
        return EtlMonitorService(db).obtener_salida_etapa(
            output_key=output_key,
            output_type=output_type,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@eda_router.put("/monitor/schedule")
def update_etl_schedule(payload: ScheduleUpdateRequest) -> dict[str, Any]:
    """Actualiza el cron del deployment de Prefect directamente desde el tablero."""
    try:
        return actualizar_cron_prefect(payload.cron, payload.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@eda_router.post("/monitor/trigger")
def trigger_etl_from_monitor(
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Dispara inmediatamente el flujo en Prefect Server o en segundo plano local."""
    try:
        return disparar_corrida_prefect(force_reprocess=True)
    except Exception:
        accepted = etl_service.iniciar_ejecucion(
            EtlRunRequest(persistir_en_db=True), background_tasks
        )
        return {
            "modo": "background_local",
            "run_id": accepted.run_id,
            "state": accepted.estado_inicial,
        }
