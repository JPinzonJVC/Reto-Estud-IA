"""Enrutador REST con espacios y contratos reservados para los 4 modelos ML."""

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.dashboard.data_store import SnapshotDWH, cargar_snapshot_dwh
from app.modules.machine_learning.schemas import (
    EstadoEspacioMLResponse,
    SlotModeloML,
)

ml_router = APIRouter(prefix="/ml", tags=["Machine Learning"])

MODELS_DIR = Path(__file__).resolve().parent / "models"


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
