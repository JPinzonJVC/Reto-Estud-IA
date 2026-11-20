"""Enrutador para endpoints del módulo de afiliados."""

from typing import Any

from fastapi import APIRouter

from app.modules.affiliates.service import AffiliatesService

affiliates_router = APIRouter(
    prefix="/affiliates",
    tags=["Afiliados"],
)

affiliates_service = AffiliatesService()


@affiliates_router.get("/summary", status_code=200)
def get_affiliates_summary() -> dict[str, Any]:
    """Retorna el resumen de desempeño de la red de afiliados desde capa Gold.

    Returns:
        Diccionario con conteo de afiliados activos, participación y fuente Gold.

    """
    return affiliates_service.get_summary()


@affiliates_router.get("/participation", status_code=200)
def get_affiliates_participation(limit: int = 20) -> list[dict[str, Any]]:
    """Retorna el listado de participación por empresa desde agg_participacion_empresa.

    Args:
        limit: Cantidad máxima de empresas a consultar.

    Returns:
        Lista de diccionarios con indicadores de participación por empresa.

    """
    return affiliates_service.get_participation_list(limit=limit)
