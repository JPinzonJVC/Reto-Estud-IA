"""Enrutador FastAPI para ejecutar y monitorear el pipeline ETL Medallion."""

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, status

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
    tags=["ETL Medallion"],
)

etl_service = EtlService()


@eda_router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EtlRunAcceptedResponse,
)
def run_etl_pipeline(
    background_tasks: BackgroundTasks,
    request: EtlRunRequest = Body(default_factory=EtlRunRequest),
) -> EtlRunAcceptedResponse:
    """Inicia la ejecución del pipeline ETL Medallion en segundo plano.

    Args:
        background_tasks: Gestor de tareas asíncronas de FastAPI.
        request: Parámetros opcionales de persistencia y fecha de corte.

    Returns:
        Identificador de ejecución y estado inicial EN_PROGRESO.

    """
    try:
        return etl_service.iniciar_ejecucion(request, background_tasks)
    except EtlAlreadyRunningError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except EtlInputNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
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
    """Consulta el estado y métricas de una ejecución ETL por su identificador.

    Args:
        run_id: Identificador único de la ejecución del pipeline ETL.

    Returns:
        Modelo EtlRunSummary con el estado y conteos de la ejecución.

    """
    try:
        return etl_service.obtener_ejecucion(run_id)
    except EtlRunNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
