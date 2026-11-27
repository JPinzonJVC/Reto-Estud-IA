"""Persistencia idempotente de resultados descriptivos ACTHO en Gold."""

from datetime import date
import hashlib
from typing import Any
from uuid import uuid4

import pandas as pd
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.eda.ml.fidelity.dataset import load_fidelity_dataset
from app.modules.eda.ml.fidelity.features import (
    RFM_COMPONENTS,
    build_rfm_s_features,
    get_complete_rfm_s_cohort,
)
from app.modules.eda.ml.fidelity.train import (
    evaluate_fidelity_candidates,
    train_fidelity_model,
)
from app.modules.eda.ml.recommender.dataset import load_company_event_attendance
from app.modules.eda.ml.recommender.recommendation import recommend_historical_line
from app.modules.eda.models.gold_dim_empresa_360 import GoldDimEmpresa360

VERSION = "actho-descriptive-v1"
APPROVAL_EXPERIMENTAL = "EXPERIMENTAL"


def _dataset_hash(frame: pd.DataFrame) -> str:
    """Calcula hash determinista de los registros de features usados."""
    payload = frame.sort_values(list(frame.columns), kind="stable").to_json(
        orient="records", date_format="iso", double_precision=8
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _upsert_result(
    db: Session, row: dict[str, Any], execution_id: str
) -> None:
    """Inserta o actualiza únicamente la misma versión y corte (idempotencia)."""
    from app.modules.eda.models.gold_ml_resultado import GoldMlResultado

    row["id_ejecucion"] = execution_id
    statement = insert(GoldMlResultado).values(**row)
    update_fields = {
        key: getattr(statement.excluded, key)
        for key in (
            "estado_evaluacion", "metodo", "score", "segmento", "soporte",
            "justificacion", "metricas", "hash_dataset",
        )
    }
    update_fields["actualizado_en"] = text("CURRENT_TIMESTAMP")
    db.execute(
        statement.on_conflict_do_update(
            constraint="uq_gold_ml_resultado_caso_empresa_version_corte",
            set_=update_fields,
        )
    )


def generate_descriptive_results(
    db: Session, cutoff: date | None = None
) -> dict[str, Any]:
    # Esta función coordina cuatro cohortes; cada bloque conserva sus propias reglas.
    # pylint: disable=too-many-locals
    """Calcula y persiste segmentos, afinidad, churn heurístico y prioridad.

    Los resultados quedan explícitamente experimentales/descriptivos; esta función
    nunca escribe columnas de probabilidad ni promueve artefactos a producción.
    """
    fecha_corte = (cutoff or date.today()).isoformat()
    execution_id = str(uuid4())
    counts = {
        "fidelidad": 0,
        "recomendacion": 0,
        "churn_heuristico": 0,
        "lead_prioridad": 0,
    }

    raw = load_fidelity_dataset(db)
    if not raw.empty:
        features = build_rfm_s_features(raw)
        cohort = get_complete_rfm_s_cohort(features)
        candidates = evaluate_fidelity_candidates(cohort, cluster_counts=(2, 3, 4, 5))
        best = next(
            (item for item in candidates if item["algorithm"] == "kmeans"), None
        )
        if best:
            model = train_fidelity_model(
                cohort,
                algorithm="kmeans",
                clusters=int(best["clusters"]),
                seed=42,
            )
            labels = model.predict(cohort[list(RFM_COMPONENTS)].astype(float))
            cohort = cohort.copy()
            cohort["cluster"] = labels
            dataset_hash = _dataset_hash(cohort)
            metrics = {
                "tipo_score": "indice_rfm_s_descriptivo_0_100",
                **{
                    key: best[key]
                    for key in (
                        "clusters", "silhouette_mean", "davies_bouldin_mean",
                        "calinski_harabasz_mean", "ari_stability_mean",
                        "seeds_evaluated",
                    )
                },
            }
            for record in cohort.to_dict(orient="records"):
                _upsert_result(db, {
                    "caso_uso": "fidelidad_rfm_s",
                    "id_empresa": record["id_empresa"],
                    "version_modelo": VERSION,
                    "fecha_corte": fecha_corte,
                    "estado_evaluacion": APPROVAL_EXPERIMENTAL,
                    "metodo": "KMeans RFM-S; percentiles de cohorte; cluster descriptivo",
                    "score": float(record["score_fidelidad_ml_0_100"]),
                    "segmento": f"CLUSTER_{int(record['cluster'])}",
                    "soporte": int(len(cohort)),
                    "justificacion": {
                        feature: float(record[feature]) for feature in RFM_COMPONENTS
                    },
                    "metricas": metrics,
                    "hash_dataset": dataset_hash,
                }, execution_id)
                counts["fidelidad"] += 1

    attendance = load_company_event_attendance(db)
    recommendations = recommend_historical_line(attendance)
    if not recommendations.empty:
        dataset_hash = _dataset_hash(attendance)
        totals = attendance.dropna(subset=["id_empresa", "id_evento"]).groupby(
            "id_empresa"
        )["id_evento"].nunique()
        for record in recommendations.to_dict(orient="records"):
            company = record["id_empresa"]
            support = int(record["eventos_soporte"])
            denominator = int(totals.get(company, support))
            _upsert_result(db, {
                "caso_uso": "recomendacion_linea",
                "id_empresa": company,
                "version_modelo": VERSION,
                "fecha_corte": fecha_corte,
                "estado_evaluacion": "DESCRIPTIVO",
                "metodo": "Afinidad histórica por eventos distintos; sin probabilidad",
                "score": round(100.0 * support / max(denominator, 1), 2),
                "segmento": record["linea_2027_recomendada_baseline"],
                "soporte": support,
                "justificacion": {"eventos_distintos_linea": support,
                                  "eventos_distintos_total": denominator},
                "metricas": {
                    "fecha_corte": fecha_corte,
                    "tipo_score": "afinidad_historica_pct",
                },
                "hash_dataset": dataset_hash,
            }, execution_id)
            counts["recomendacion"] += 1

    gold_rows = db.execute(select(GoldDimEmpresa360)).scalars().all()
    for company in gold_rows:
        is_active = company.tipo_relacion_actho == "AFILIADO_ACTIVO"
        score = company.puntaje_riesgo_heuristico if is_active else None
        if score is not None:
            _upsert_result(db, {
                "caso_uso": "churn_heuristico",
                "id_empresa": company.id_empresa,
                "version_modelo": VERSION,
                "fecha_corte": fecha_corte,
                "estado_evaluacion": "HEURISTICO",
                "metodo": "Semáforo heurístico calculado por ETL Gold",
                "score": float(score),
                "segmento": company.semaforo_riesgo_renovacion,
                "soporte": None,
                "justificacion": {
                    "alerta_vencimiento_90d": bool(company.alerta_vencimiento_90d),
                    "alerta_sin_participacion_trimestre": bool(
                        company.alerta_sin_participacion_trimestre
                    ),
                    "alerta_baja_satisfaccion": bool(company.alerta_baja_satisfaccion),
                    "alerta_monocontacto": bool(company.alerta_monocontacto),
                },
                "metricas": {
                    "es_probabilidad": False,
                    "tipo_score": "puntos_heuristicos_gold",
                },
                "hash_dataset": None,
            }, execution_id)
            counts["churn_heuristico"] += 1
        if company.tipo_relacion_actho == "PROSPECTO_NO_AFILIADO":
            engagement = int(company.total_eventos_anio or 0)
            if engagement:
                _upsert_result(db, {
                    "caso_uso": "lead_prioridad",
                    "id_empresa": company.id_empresa,
                    "version_modelo": VERSION,
                    "fecha_corte": fecha_corte,
                    "estado_evaluacion": "DESCRIPTIVO",
                    "metodo": "Priorización por interacción histórica; no es propensión",
                    "score": None,
                    "segmento": "INTERACCION_HISTORICA_OBSERVADA",
                    "soporte": engagement,
                    "justificacion": {
                        "eventos_distintos_observados": engagement,
                        "criterio": "interaccion positiva observada",
                    },
                    "metricas": {
                        "probabilidad_conversion": None,
                        "tipo_score": "prioridad_sin_score",
                    },
                    "hash_dataset": None,
                }, execution_id)
                counts["lead_prioridad"] += 1
    db.commit()
    return {"id_ejecucion": execution_id, **counts}


def list_results(
    db: Session, case: str, *, limit: int = 100, company_id: str | None = None
) -> list[dict[str, Any]]:
    """Devuelve resultados del corte vigente más reciente para consulta API."""
    from app.modules.eda.models.gold_ml_resultado import GoldMlResultado

    latest = db.query(GoldMlResultado.fecha_corte).filter(
        GoldMlResultado.caso_uso == case
    ).order_by(GoldMlResultado.fecha_corte.desc()).limit(1).scalar_subquery()
    query = db.query(GoldMlResultado).filter(
        GoldMlResultado.caso_uso == case,
        GoldMlResultado.fecha_corte == latest,
    )
    if company_id:
        query = query.filter(GoldMlResultado.id_empresa == company_id)
    if case == "lead_prioridad":
        query = query.order_by(
            GoldMlResultado.soporte.desc().nullslast(), GoldMlResultado.id_empresa
        )
    else:
        query = query.order_by(GoldMlResultado.id_empresa)
    rows = query.limit(limit).all()
    return [
        {
            "id_empresa": row.id_empresa,
            "id_ejecucion": row.id_ejecucion,
            "caso_uso": row.caso_uso,
            "version": row.version_modelo,
            "fecha_corte": row.fecha_corte,
            "estado": row.estado_evaluacion,
            "metodo": row.metodo,
            "score": row.score,
            "segmento_o_linea": row.segmento,
            "soporte": row.soporte,
            "justificacion": row.justificacion,
            "metricas": row.metricas,
        }
        for row in rows
    ]


def list_result_page(
    db: Session,
    case: str,
    *,
    limit: int = 50,
    offset: int = 0,
    company_search: str | None = None,
    segment: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Consulta una página del último corte y conserva el total filtrado."""
    from app.modules.eda.models.gold_ml_resultado import GoldMlResultado

    latest_cutoff = db.query(func.max(GoldMlResultado.fecha_corte)).filter(
        GoldMlResultado.caso_uso == case
    ).scalar()
    query = db.query(GoldMlResultado).filter(GoldMlResultado.caso_uso == case)
    if latest_cutoff is not None:
        query = query.filter(GoldMlResultado.fecha_corte == latest_cutoff)
    else:
        return {
            "caso_uso": case,
            "fecha_corte": None,
            "version": None,
            "id_ejecucion": None,
            "total": 0,
            "limit": limit,
            "offset": offset,
            "items": [],
        }
    if company_search:
        query = query.filter(GoldMlResultado.id_empresa.ilike(f"%{company_search}%"))
    if segment:
        query = query.filter(GoldMlResultado.segmento == segment)
    if status:
        query = query.filter(GoldMlResultado.estado_evaluacion == status)

    total = int(query.count())
    if case == "lead_prioridad":
        query = query.order_by(
            GoldMlResultado.soporte.desc().nullslast(), GoldMlResultado.id_empresa
        )
    else:
        query = query.order_by(GoldMlResultado.id_empresa)
    rows = query.offset(offset).limit(limit).all()
    metadata = db.query(GoldMlResultado).filter(
        GoldMlResultado.caso_uso == case,
        GoldMlResultado.fecha_corte == latest_cutoff,
    ).order_by(GoldMlResultado.id.desc()).first()
    return {
        "caso_uso": case,
        "fecha_corte": latest_cutoff,
        "version": metadata.version_modelo if metadata else None,
        "id_ejecucion": metadata.id_ejecucion if metadata else None,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id_empresa": row.id_empresa,
                "id_ejecucion": row.id_ejecucion,
                "caso_uso": row.caso_uso,
                "version": row.version_modelo,
                "fecha_corte": row.fecha_corte,
                "estado": row.estado_evaluacion,
                "metodo": row.metodo,
                "score": row.score,
                "segmento_o_linea": row.segmento,
                "soporte": row.soporte,
                "justificacion": row.justificacion,
                "metricas": row.metricas,
            }
            for row in rows
        ],
    }
