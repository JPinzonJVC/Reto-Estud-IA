"""Enrutador de alto nivel del Dashboard sobre el Data Warehouse ACTHO 360."""

import csv
import io
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.dashboard.repository import DashboardSilverRepository

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

MAPA_SEGMENTOS_EXPORT: dict[str, str] = {
    "sin_participacion": "AFILIADOS_SIN_PARTICIPACION",
    "vencimientos_90d": "VENCIMIENTOS_PROXIMOS_90D",
    "detractores": "DETRACTORES_RECIENTES",
    "promotores": "PROMOTORES_TESTIMONIOS",
    "leads": "ASISTENTES_NO_AFILIADOS_LEADS",
    "monocontacto": "AFILIADOS_UN_SOLO_CONTACTO",
    "interes_tema": "INTERES_POR_TEMA_Y_LINEA",
    "nuevos_afiliados": "NUEVOS_AFILIADOS_ONBOARDING",
}


def _repository(session: Session) -> DashboardSilverRepository:
    """Construye el repositorio DWH inyectando la sesión activa."""
    return DashboardSilverRepository(session)


@dashboard_router.get("/filters")
def get_dashboard_filters(db: Session = Depends(get_db)) -> dict[str, list[str]]:
    """Retorna todos los catálogos de filtros disponibles en el Data Warehouse."""
    return _repository(db).obtener_filtros()


@dashboard_router.get("/overview")
def get_overview(
    fecha_referencia: date = Query(default=date(2026, 11, 13)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Compone los indicadores ejecutivos, semáforo de riesgo y vencimientos."""
    return _repository(db).obtener_resumen(fecha_referencia)


@dashboard_router.get("/membership-evolution")
def get_membership_evolution(
    kam_id: str | None = None,
    anio: int | None = None,
    ultimos_meses: int = Query(default=18, ge=3, le=60),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna la evolución mensual de altas, renovaciones y retiros Gold."""
    return _repository(db).obtener_evolucion_membresias(
        kam_id=kam_id, anio=anio, ultimos_meses=ultimos_meses
    )


@dashboard_router.get("/segment-kpis")
def get_segment_kpis(
    dimension: str = Query(default="sector_economico"),
    kam_id: str | None = None,
    pais: str | None = None,
    top_n: int = Query(default=15, ge=3, le=50),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna KPIs por sector, subsector, tamaño de empresa, empleados o nivel."""
    return _repository(db).obtener_kpis_segmentos_empresariales(
        dimension=dimension, kam_id=kam_id, pais=pais, top_n=top_n
    )


@dashboard_router.get("/event-kpis")
def get_event_kpis(
    linea_oferta: str | None = None,
    modalidad: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna KPIs consolidados por línea de oferta 2027, modalidad y evento."""
    return _repository(db).obtener_kpis_tipo_evento(
        linea_oferta=linea_oferta, modalidad=modalidad
    )


@dashboard_router.get("/communication-segments")
def get_communication_segments(
    segmento_codigo: str | None = None,
    kam_id: str | None = None,
    solo_aptos: bool = False,
    limit: int = Query(default=150, ge=10, le=2000),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Consulta los 8 segmentos accionables Gold con filtro Habeas Data."""
    return _repository(db).obtener_mart_segmentos(
        segmento_codigo=segmento_codigo,
        kam_id=kam_id,
        solo_aptos=solo_aptos,
        limit=limit,
    )


@dashboard_router.get("/satisfaction-topics")
def get_satisfaction_topics(
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna dimensiones Likert 1-5, clasificación NLP de temas y estado NPS 0-10."""
    return _repository(db).obtener_dimensiones_satisfaccion(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )


@dashboard_router.get("/export/{segmento}")
def export_dashboard_segment_csv(
    segmento: str,
    kam_id: str | None = None,
    solo_aptos: bool = False,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Exporta en CSV UTF-8 con BOM cualquiera de los 8 segmentos de comunicaciones."""
    repo = _repository(db)
    codigo = MAPA_SEGMENTOS_EXPORT.get(segmento, segmento.upper())
    res = repo.obtener_mart_segmentos(
        segmento_codigo=codigo, kam_id=kam_id, solo_aptos=solo_aptos, limit=5000
    )
    codigos_validos = {s["segmento_codigo"] for s in res["resumen_segmentos"]}
    if codigos_validos and codigo not in codigos_validos:
        lista_cods = sorted(codigos_validos)
        raise HTTPException(
            status_code=400,
            detail=f"Segmento inválido '{segmento}'. Usa uno de: {lista_cods}",
        )

    rows = res["items"]
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        buffer.write("sin_registros\n")

    content = ("\ufeff" + buffer.getvalue()).encode("utf-8")
    nombre_csv = f"actho_segmento_{codigo.lower()}.csv"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre_csv}"'},
    )
