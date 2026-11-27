"""Enrutador para endpoints del módulo de afiliados."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.dashboard.repository import DashboardSilverRepository

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


@affiliates_router.get("/silver/filters")
def get_silver_filters(db: Session = Depends(get_db)) -> dict[str, list[str]]:
    """Retorna filtros de afiliación disponibles en Silver.

    Args:
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Catálogos de KAM, nivel, sector, tamaño, estado de membresía y ciudad.

    """
    filters = DashboardSilverRepository(db).obtener_filtros()
    return {
        key: filters[key]
        for key in (
            "kams",
            "niveles_membresia",
            "sectores",
            "subsectores",
            "tamanos_empresa",
            "rangos_empleados",
            "estados_membresia",
            "ciudades",
            "paises",
            "semaforos_riesgo",
        )
    }


@affiliates_router.get("/silver/portfolio")
def get_silver_portfolio(
    kam_id: str | None = None,
    nivel_membresia: str | None = None,
    sector: str | None = None,
    subsector: str | None = None,
    tamano_empresa: str | None = None,
    rango_empleados: str | None = None,
    estado_membresia: str | None = None,
    ciudad: str | None = None,
    pais: str | None = None,
    semaforo: str | None = None,
    solo_activos: bool = True,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Lista cartera de afiliados desde el DWH con filtros comerciales."""
    return DashboardSilverRepository(db).listar_afiliados(
        kam_id=kam_id,
        nivel_membresia=nivel_membresia,
        sector=sector,
        subsector=subsector,
        tamano_empresa=tamano_empresa,
        rango_empleados=rango_empleados,
        estado_membresia=estado_membresia,
        ciudad=ciudad,
        pais=pais,
        semaforo=semaforo,
        solo_activos=solo_activos,
        offset=offset,
        limit=limit,
    )


@affiliates_router.get("/silver/renewals")
def get_silver_renewals(
    periodo_desde: str | None = None,
    periodo_hasta: str | None = None,
    kam_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retorna movimientos CRM, renovaciones y cierres Silver.

    Args:
        periodo_desde: Periodo mensual inicial ISO opcional.
        periodo_hasta: Periodo mensual final ISO opcional.
        kam_id: Identificador opcional de la ejecutiva de cuenta.
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Agregados de movimientos, renovaciones y cierres facturados por KAM.

    """
    return DashboardSilverRepository(db).obtener_renovaciones(
        periodo_desde=periodo_desde,
        periodo_hasta=periodo_hasta,
        kam_id=kam_id,
    )


@affiliates_router.get("/silver/pillars")
def get_silver_pillars(
    kam_id: str | None = None,
    nivel_membresia: str | None = None,
    sector: str | None = None,
    pais: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna adopción de pilares estratégicos, comunidades y diversidad Silver.

    Args:
        kam_id: Identificador opcional de la ejecutiva KAM.
        nivel_membresia: Nivel de membresía opcional.
        sector: Sector económico opcional.
        pais: País de la empresa opcional.
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Adopción de pilares y promedio de participación femenina en activos.

    """
    return DashboardSilverRepository(db).obtener_pilares_y_comunidades(
        kam_id=kam_id,
        nivel_membresia=nivel_membresia,
        sector=sector,
        pais=pais,
    )


@affiliates_router.get("/silver/kam-summary")
def get_silver_kam_summary(
    fecha_referencia: date = Query(default=date(2026, 11, 13)),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retorna comparativa de cartera, participación y renovaciones por KAM."""
    return DashboardSilverRepository(db).obtener_resumen_kams(fecha_referencia)


@affiliates_router.get("/silver/distribution")
def get_silver_distribution(
    fecha_referencia: date = Query(default=date(2026, 11, 13)),
    kam_id: str | None = None,
    nivel_membresia: str | None = None,
    sector: str | None = None,
    subsector: str | None = None,
    tamano_empresa: str | None = None,
    rango_empleados: str | None = None,
    ciudad: str | None = None,
    pais: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna distribución de activos y curva de vencimientos 30/60/90 días."""
    return DashboardSilverRepository(db).obtener_distribucion_afiliados(
        fecha_referencia=fecha_referencia,
        kam_id=kam_id,
        nivel_membresia=nivel_membresia,
        sector=sector,
        subsector=subsector,
        tamano_empresa=tamano_empresa,
        rango_empleados=rango_empleados,
        ciudad=ciudad,
        pais=pais,
    )
