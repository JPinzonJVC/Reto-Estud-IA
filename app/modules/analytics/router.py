"""Enrutador para endpoints del módulo de analítica."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.dashboard.repository import DashboardSilverRepository

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


@analytics_router.get("/silver/filters")
def get_silver_filters(db: Session = Depends(get_db)) -> dict[str, list[str]]:
    """Retorna filtros de participación disponibles en Silver.

    Args:
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Catálogos de línea de oferta, modalidad, periodo y ciudad de evento.

    """
    filters = DashboardSilverRepository(db).obtener_filtros()
    return {
        key: filters[key]
        for key in (
            "lineas_oferta",
            "modalidades_evento",
            "periodos_asistencia",
            "ciudades_evento",
        )
    }


@analytics_router.get("/silver/participation")
def get_silver_participation(
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    kam_id: str | None = None,
    ciudad_evento: str | None = None,
    linea_oferta: str | None = None,
    modalidad: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retorna participación Silver por evento, línea y modalidad.

    Args:
        fecha_desde: Fecha inicial ISO opcional de las asistencias.
        fecha_hasta: Fecha final ISO opcional de las asistencias.
        kam_id: Identificador opcional de la ejecutiva de cuenta.
        ciudad_evento: Ciudad en la que ocurrió el evento opcional.
        linea_oferta: Línea de oferta 2027 opcional.
        modalidad: Modalidad del evento opcional (Presencial, Virtual, Híbrido).
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Métricas de asistentes, empresas y personas distintas por evento.

    """
    return DashboardSilverRepository(db).obtener_participacion(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        kam_id=kam_id,
        ciudad_evento=ciudad_evento,
        linea_oferta=linea_oferta,
        modalidad=modalidad,
    )


@analytics_router.get("/silver/audience")
def get_silver_audience(
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    kam_id: str | None = None,
    ciudad_evento: str | None = None,
    linea_oferta: str | None = None,
    modalidad: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna desglose Silver por nivel de cargo, línea 2027 y modalidad.

    Args:
        fecha_desde: Fecha inicial ISO opcional.
        fecha_hasta: Fecha final ISO opcional.
        kam_id: Identificador opcional de la ejecutiva KAM.
        ciudad_evento: Ciudad del evento opcional.
        linea_oferta: Línea de oferta 2027 opcional.
        modalidad: Modalidad del evento opcional.
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Conteos por nivel de cargo, línea de oferta y modalidad.

    """
    return DashboardSilverRepository(db).obtener_audiencia(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        kam_id=kam_id,
        ciudad_evento=ciudad_evento,
        linea_oferta=linea_oferta,
        modalidad=modalidad,
    )


@analytics_router.get("/silver/satisfaction")
def get_silver_satisfaction(
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retorna satisfacción y NPS adaptado calculados desde Silver.

    Args:
        fecha_desde: Fecha inicial ISO opcional de las encuestas.
        fecha_hasta: Fecha final ISO opcional de las encuestas.
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Promedios de satisfacción y NPS adaptado por evento y periodo.

    """
    return DashboardSilverRepository(db).obtener_satisfaccion(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


@analytics_router.get("/silver/satisfaction-dimensions")
def get_silver_satisfaction_dimensions(
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna las 4 dimensiones Likert por modalidad y temarios sugeridos.

    Args:
        fecha_desde: Fecha inicial ISO opcional de las encuestas.
        fecha_hasta: Fecha final ISO opcional de las encuestas.
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Promedios por dimensión/modalidad y muestra de temarios sugeridos.

    """
    return DashboardSilverRepository(db).obtener_dimensiones_satisfaccion(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
