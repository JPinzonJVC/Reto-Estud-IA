"""Enrutador de API y vistas para el módulo de retención."""

import csv
import io
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.dashboard.repository import DashboardSilverRepository
from app.modules.retention.service import RetentionService

retention_router = APIRouter(
    prefix="/retention",
    tags=["Retención de Clientes"],
)

service = RetentionService()


class CustomerEvaluationRequest(BaseModel):
    """Esquema de solicitud para evaluar el riesgo de un cliente."""

    customer_id: str
    """Identificador alfanumérico del cliente."""

    features: list[float]
    """Vector de características numéricas para el modelo predictivo."""

    model_config = ConfigDict(from_attributes=True)


@retention_router.get("/overview", status_code=200)
def get_overview() -> dict[str, Any]:
    """Obtiene el resumen general de indicadores de retención desde la capa Gold.

    Returns:
        Diccionario con indicadores clave de retención y empresas en riesgo.

    """
    return service.get_retention_overview()


@retention_router.get("/companies", status_code=200)
def get_retention_companies(
    semaforo: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    """Lista las empresas de agg_retencion_empresa según su semáforo de riesgo.

    Args:
        semaforo: Categoría opcional del semáforo heurístico.
        limit: Cantidad máxima de empresas a retornar.

    Returns:
        Lista de registros de retención por empresa.

    """
    return service.get_companies_by_risk(semaforo=semaforo, limit=limit)


@retention_router.post("/evaluate", status_code=200)
def evaluate_customer(payload: CustomerEvaluationRequest) -> dict[str, Any]:
    """Evalúa el nivel de riesgo de fuga de un cliente específico.

    Args:
        payload: Objeto con customer_id y lista de predictores.

    Returns:
        Resultado del análisis de riesgo con recomendaciones personalizadas.

    """
    return service.analyze_customer(
        customer_id=payload.customer_id,
        features=payload.features,
    )


@retention_router.get("/silver/segments")
def get_silver_segments(
    fecha_referencia: date = Query(default_factory=date.today),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna segmentos de acción temprana disponibles desde Silver.

    Args:
        fecha_referencia: Fecha base para determinar vencimientos próximos.
        limit: Máximo de registros por segmento.
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Segmentos de vencimientos, inactividad y asistentes no afiliados.

    """
    return DashboardSilverRepository(db).obtener_segmentos(fecha_referencia, limit)


@retention_router.get("/silver/engagement-risk")
def get_silver_engagement_risk(
    kam_id: str | None = None,
    nivel_membresia: str | None = None,
    sector: str | None = None,
    pais: str | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna conteos y listas Silver de sin participación y monocontacto.

    Args:
        kam_id: Identificador opcional de la ejecutiva KAM.
        nivel_membresia: Nivel de membresía opcional.
        sector: Sector económico opcional.
        pais: País de la empresa opcional.
        limit: Máximo de registros por lista.
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Resumen y listas de afiliados activos sin participación y monocontacto.

    """
    return DashboardSilverRepository(db).obtener_riesgo_participacion_silver(
        kam_id=kam_id,
        nivel_membresia=nivel_membresia,
        sector=sector,
        pais=pais,
        limit=limit,
    )


@retention_router.get("/silver/export/{segmento}")
def export_silver_segment_csv(
    segmento: str,
    kam_id: str | None = None,
    nivel_membresia: str | None = None,
    sector: str | None = None,
    pais: str | None = None,
    fecha_referencia: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Exporta en CSV directo desde Silver una lista accionable de retención.

    Args:
        segmento: Clave del segmento ('sin_participacion', 'monocontacto', 'vencimientos_90d').
        kam_id: Identificador opcional de la ejecutiva KAM.
        nivel_membresia: Nivel de membresía opcional.
        sector: Sector económico opcional.
        pais: País de la empresa opcional.
        fecha_referencia: Fecha base para vencimientos próximos a 90 días.
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Archivo CSV descargable en codificación UTF-8 con BOM para Excel.

    Raises:
        HTTPException: Si el segmento solicitado no es válido.

    """
    repo = DashboardSilverRepository(db)
    if segmento in ("sin_participacion", "monocontacto"):
        data = repo.obtener_riesgo_participacion_silver(
            kam_id=kam_id,
            nivel_membresia=nivel_membresia,
            sector=sector,
            pais=pais,
            limit=2000,
        )
        rows = (
            data["lista_sin_participacion"]
            if segmento == "sin_participacion"
            else data["lista_monocontacto"]
        )
    elif segmento == "vencimientos_90d":
        seg = repo.obtener_segmentos(fecha_referencia, limit=2000)
        rows = seg["vencimientos_proximos"]
    else:
        raise HTTPException(
            status_code=400,
            detail="Segmento inválido. Usa sin_participacion, monocontacto o vencimientos_90d.",
        )

    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        buffer.write("sin_registros\n")

    content = ("\ufeff" + buffer.getvalue()).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="actho_silver_{segmento}.csv"'
        },
    )
