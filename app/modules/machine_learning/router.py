"""Enrutador REST con espacios y contratos reservados para los 4 modelos ML."""

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.dashboard.data_store import SnapshotDWH, cargar_snapshot_dwh
from app.modules.eda.ml.persistence import list_result_page, list_results
from app.modules.eda.ml.common.registry import (
    ModelManifest,
    artifacts_root_from_environment,
)
from app.modules.machine_learning.schemas import (
    EstadoEspacioMLResponse,
    PaginaResultadosMlResponse,
    ResumenMlResponse,
    SlotModeloML,
)

ml_router = APIRouter(prefix="/ml", tags=["Machine Learning"])

MODELS_DIR = Path(__file__).resolve().parent / "models"
ML_CASES = (
    "fidelidad_rfm_s",
    "recomendacion_linea",
    "churn_heuristico",
    "lead_prioridad",
)


@ml_router.get("/resumen", response_model=ResumenMlResponse)
def get_ml_overview(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Resume cobertura, corte, estado y artefactos aprobados disponibles."""
    result_types = {
        "fidelidad_rfm_s": "No supervisado / exploratorio",
        "recomendacion_linea": "Afinidad histórica",
        "churn_heuristico": "Heurístico",
        "lead_prioridad": "Priorización descriptiva",
    }
    cases: list[dict[str, Any]] = []
    for case in ML_CASES:
        page = (
            list_result_page(db, case, limit=1)
            if _result_table_exists(db)
            else {"fecha_corte": None, "version": None, "total": 0, "items": []}
        )
        item = page["items"][0] if page["items"] else None
        cases.append(
            {
                "caso_uso": case,
                "fecha_corte": page["fecha_corte"],
                "version": page["version"],
                "estado": item["estado"] if item else "SIN_RESULTADOS",
                "empresas_procesadas": page["total"],
                "resultados_disponibles": page["total"],
                "tipo_resultado": result_types[case],
            }
        )
    return {
        "fecha_corte": max(
            (case["fecha_corte"] for case in cases if case["fecha_corte"]),
            default=None,
        ),
        "resultados_totales": sum(
            case["resultados_disponibles"] for case in cases
        ),
        "modelos_aprobados_disponibles": _approved_model_count(),
        "casos_uso": cases,
    }


def _result_table_exists(db: Session) -> bool:
    """Comprueba si la migración ML está instalada sin crear el modelo en metadata."""
    return inspect(db.get_bind()).has_table("gold_ml_resultados_empresa")


def _approved_model_count() -> int:
    """Cuenta manifiestos aprobados en el registro externo configurado."""
    try:
        artifacts_root = artifacts_root_from_environment()
    except RuntimeError:
        return 0
    approved = 0
    for manifest_path in artifacts_root.glob("*/*/manifest.json"):
        try:
            manifest = ModelManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            continue
        approved += int(manifest.approved)
    return approved


# FastAPI representa los filtros como argumentos tipados de query.
# pylint: disable=too-many-positional-arguments
@ml_router.get(
    "/resultados/{caso_uso}", response_model=PaginaResultadosMlResponse
)
def get_ml_results(
    caso_uso: str,
    id_empresa: str | None = None,
    buscar_empresa: str | None = Query(default=None, max_length=64),
    segmento: str | None = Query(default=None, max_length=128),
    estado: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Consulta resultados Gold descriptivos del corte más reciente."""
    cases = {
        "fidelidad_rfm_s", "recomendacion_linea", "churn_heuristico",
        "lead_prioridad",
    }
    if caso_uso not in cases:
        raise HTTPException(status_code=404, detail="Caso de uso ML desconocido.")
    if not _result_table_exists(db):
        raise HTTPException(
            status_code=503,
            detail="Resultados ML no disponibles; aplica primero la migración Alembic.",
        )
    return list_result_page(
        db,
        caso_uso,
        limit=limit,
        offset=offset,
        company_search=buscar_empresa or id_empresa,
        segment=segmento,
        status=estado,
    )


def _contar_no_nulos(df: pd.DataFrame, col: str) -> int:
    """Cuenta valores poblados en una columna reservada de Gold."""
    if df.empty or col not in df.columns:
        return 0
    return int(df[col].notna().sum())


def _construir_slots_ml(snap: SnapshotDWH) -> list[SlotModeloML]:
    """Evalúa dinámicamente si la rama ML ya pobló cada columna reservada."""
    emp = snap.dim_empresa_360
    n_act = (
        int((emp["tipo_relacion_actho"] == "AFILIADO_ACTIVO").sum())
        if not emp.empty
        else 0
    )
    n_tot = int(len(emp))
    definiciones = (
        (
            "fidelidad",
            "1. Modelo de Detección y Predicción de Fidelidad",
            "RFM-S + K-Means / Clasificador Multiclase",
            "score_fidelidad_ml_0_100",
            n_act,
            "/ml/fidelidad",
        ),
        (
            "publico_eventos",
            "2. ML Público Interesado y Potencial Asistencia a Eventos",
            "Filtrado Híbrido por Línea 2027 + Gradient Boosting",
            "prob_asistencia_prox_evento_ml",
            n_tot,
            "/ml/publico-eventos",
        ),
        (
            "uso_permanencia",
            "3. ML Relación Uso/Asistencia con Permanencia o Renovación",
            "Regresión Logística Penalizada + Importancia SHAP",
            "probabilidad_churn_ml",
            n_act,
            "/ml/uso-permanencia",
        ),
        (
            "riesgo_renovacion",
            "4. Semáforo Híbrido y Riesgo Predictivo de No Renovación",
            "HistGradientBoosting Calibrado + Reglas de Negocio",
            "probabilidad_churn_ml",
            n_act,
            "/ml/riesgo-renovacion",
        ),
    )
    slots: list[SlotModeloML] = []
    for clave, nombre, algo, col, universo, ruta in definiciones:
        poblados = _contar_no_nulos(emp, col)
        slots.append(
            SlotModeloML(
                clave_modelo=clave,
                nombre_modelo=nombre,
                algoritmo_recomendado=algo,
                estado="MODELO_ACTIVO" if poblados > 0 else "ESPACIO_RESERVADO",
                columna_gold_objetivo=col,
                registros_poblandose=poblados,
                total_universo_elegible=universo,
                ruta_endpoint=ruta,
            )
        )
    return slots


@ml_router.get("/status", response_model=EstadoEspacioMLResponse)
def get_ml_status(db: Session = Depends(get_db)) -> EstadoEspacioMLResponse:
    """Retorna el estado de los 4 espacios reservados para la rama de modelos ML."""
    snap = cargar_snapshot_dwh(db)
    artefactos = [p.name for p in MODELS_DIR.glob("*.pkl")] if MODELS_DIR.exists() else []
    return EstadoEspacioMLResponse(
        fuente_datos=snap.fuente,
        rama_entrenamiento_separada=len(artefactos) == 0,
        insumos_listos={
            "empresas_360": int(len(snap.dim_empresa_360)),
            "eventos_kpis": int(len(snap.dim_evento_kpis)),
            "asistencias_bi": int(len(snap.fact_asistencias_bi)),
            "encuestas_bi": int(len(snap.fact_encuestas_bi)),
            "evolucion_mensual": int(len(snap.fact_evolucion_mes)),
        },
        modelos=_construir_slots_ml(snap),
        notas_integracion={
            "directorio_artefactos": "app/modules/machine_learning/models/",
            "artefactos_detectados": artefactos,
            "tabla_destino_gold": "gold_dim_empresa_360",
        },
    )


@ml_router.get("/fidelidad")
def get_ml_fidelidad(
    limit: int = Query(default=25, ge=5, le=200),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Espacio reservado para el Modelo de Fidelidad sobre afiliados activos."""
    results = (
        list_results(db, "fidelidad_rfm_s", limit=limit)
        if _result_table_exists(db)
        else []
    )
    if results:
        return {
            "estado": "EXPERIMENTAL",
            "nota": "Segmentos descriptivos; no representan probabilidad de retención.",
            "total_resultados": len(results),
            "distribucion_arquetipos": {},
            "items": results,
        }
    snap = cargar_snapshot_dwh(db)
    emp = snap.dim_empresa_360
    act = emp[emp["es_membresia_activa"].eq(True)].copy() if not emp.empty else emp
    activo_ml = _contar_no_nulos(act, "score_fidelidad_ml_0_100") > 0

    arquetipos = (
        act["arquetipo_fidelidad_ml"].dropna().value_counts().to_dict()
        if activo_ml
        else {}
    )
    orden_col = "score_fidelidad_ml_0_100" if activo_ml else "total_eventos_anio"
    muestra = (
        act.sort_values(orden_col, ascending=False)
        .head(limit)[
            [
                "id_empresa",
                "kam_id",
                "nivel_membresia",
                "total_eventos_anio",
                "personas_distintas_anio",
                "satisfaccion_promedio_1_5",
                "score_fidelidad_ml_0_100",
                "arquetipo_fidelidad_ml",
            ]
        ]
        .where(lambda d: pd.notna(d), None)
        .to_dict(orient="records")
        if not act.empty
        else []
    )
    return {
        "estado": "MODELO_ACTIVO" if activo_ml else "ESPACIO_RESERVADO",
        "total_afiliados_activos": int(len(act)),
        "distribucion_arquetipos": arquetipos,
        "features_base_disponibles": [
            "total_eventos_anio",
            "personas_distintas_anio",
            "dias_sin_participacion",
            "satisfaccion_promedio_1_5",
            "total_ciclos_membresia",
        ],
        "items": muestra,
    }


@ml_router.get("/publico-eventos")
def get_ml_publico_eventos(
    limit: int = Query(default=25, ge=5, le=200),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Espacio reservado para ML de Público Interesado y Potencial Asistencia."""
    if _result_table_exists(db):
        recommendations = list_results(db, "recomendacion_linea", limit=limit)
        priorities = list_results(db, "lead_prioridad", limit=limit)
    else:
        recommendations = []
        priorities = []
    if recommendations or priorities:
        return {
            "estado": "AFINIDAD_HISTORICA_DESCRIPTIVA",
            "nota": "No representa probabilidad de asistencia ni de conversión.",
            "recomendaciones": recommendations,
            "priorizacion_prospectos": priorities,
        }
    snap = cargar_snapshot_dwh(db)
    emp = snap.dim_empresa_360
    activo_ml = _contar_no_nulos(emp, "prob_asistencia_prox_evento_ml") > 0

    afinidad_hist = (
        emp["linea_2027_mayor_participacion"].dropna().value_counts().to_dict()
        if not emp.empty
        else {}
    )
    leads = (
        emp[emp["tipo_relacion_actho"] == "PROSPECTO_NO_AFILIADO"]
        .sort_values("total_asistencias_anio", ascending=False)
        .head(limit)[
            [
                "id_empresa",
                "sector_economico",
                "total_eventos_anio",
                "total_asistencias_anio",
                "linea_2027_mayor_participacion",
                "linea_2027_recomendada_ml",
                "prob_asistencia_prox_evento_ml",
                "score_conversion_lead_ml_0_100",
            ]
        ]
        .where(lambda d: pd.notna(d), None)
        .to_dict(orient="records")
        if not emp.empty
        else []
    )
    return {
        "estado": "MODELO_ACTIVO" if activo_ml else "ESPACIO_RESERVADO",
        "afinidad_historica_linea_2027": {
            str(k): int(v) for k, v in afinidad_hist.items()
        },
        "prospectos_alta_interaccion": leads,
    }


@ml_router.get("/uso-permanencia")
def get_ml_uso_permanencia(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Espacio reservado para ML de Relación entre Uso/Asistencia y Permanencia."""
    snap = cargar_snapshot_dwh(db)
    emp = snap.dim_empresa_360
    crm = (
        emp[emp["tipo_relacion_actho"].isin(["AFILIADO_ACTIVO", "EX_AFILIADO"])].copy()
        if not emp.empty
        else emp
    )
    tramos: list[dict[str, Any]] = []
    if not crm.empty:
        ev = pd.to_numeric(crm["total_eventos_anio"], errors="coerce").fillna(0)
        crm["_tramo_uso"] = pd.cut(
            ev,
            bins=[-1, 0, 2, 5, 1000],
            labels=["0 eventos", "1-2 eventos", "3-5 eventos", "6+ eventos"],
        )
        for etiqueta, sub in crm.groupby("_tramo_uso", observed=False):
            n_tot = int(len(sub))
            n_act = int((sub["tipo_relacion_actho"] == "AFILIADO_ACTIVO").sum())
            tramos.append(
                {
                    "tramo_uso": str(etiqueta),
                    "empresas_crm": n_tot,
                    "permanecen_activas": n_act,
                    "tasa_permanencia_pct": (
                        round(n_act / n_tot * 100.0, 1) if n_tot > 0 else 0.0
                    ),
                }
            )
    activo_ml = _contar_no_nulos(emp, "probabilidad_churn_ml") > 0
    return {
        "estado": "MODELO_ACTIVO" if activo_ml else "ESPACIO_RESERVADO",
        "curva_empirica_uso_vs_permanencia": tramos,
        "importancia_variables_ml": [],
    }


@ml_router.get("/riesgo-renovacion")
def get_ml_riesgo_renovacion(
    limit: int = Query(default=25, ge=5, le=200),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Espacio reservado para Probabilidad ML de No Renovación y Semáforo."""
    snap = cargar_snapshot_dwh(db)
    emp = snap.dim_empresa_360
    act = emp[emp["es_membresia_activa"].eq(True)].copy() if not emp.empty else emp
    activo_ml = _contar_no_nulos(act, "probabilidad_churn_ml") > 0
    sem = (
        act["semaforo_riesgo_renovacion"].value_counts().to_dict()
        if not act.empty
        else {}
    )
    top_riesgo = (
        act.sort_values("puntaje_riesgo_heuristico", ascending=False)
        .head(limit)[
            [
                "id_empresa",
                "kam_id",
                "nivel_membresia",
                "fecha_fin_vigencia",
                "puntaje_riesgo_heuristico",
                "probabilidad_churn_ml",
                "semaforo_riesgo_renovacion",
            ]
        ]
        .where(lambda d: pd.notna(d), None)
        .to_dict(orient="records")
        if not act.empty
        else []
    )
    return {
        "estado": "MODELO_ACTIVO" if activo_ml else "ESPACIO_RESERVADO",
        "semaforo_actual": {
            "ROJO": int(sem.get("ROJO", 0)),
            "AMARILLO": int(sem.get("AMARILLO", 0)),
            "VERDE": int(sem.get("VERDE", 0)),
        },
        "cuentas_prioritarias": top_riesgo,
    }
