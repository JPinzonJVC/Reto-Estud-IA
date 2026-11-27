"""Persistencia idempotente de resultados descriptivos ACTHO en Gold."""

import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.modules.eda.ml.common.registry import (
    ModelManifest,
    ModelRegistration,
    artifacts_root_from_environment,
    load_approved_model,
    store_model_artifact,
    store_prediction_execution,
)
from app.modules.eda.ml.fidelity.dataset import load_fidelity_dataset
from app.modules.eda.ml.fidelity.features import (
    RFM_COMPONENTS,
    build_rfm_s_features,
    get_complete_rfm_s_cohort,
)
from app.modules.eda.ml.fidelity.predict import predict_fidelity_clusters
from app.modules.eda.ml.fidelity.train import (
    evaluate_fidelity_candidates,
    train_fidelity_model,
)
from app.modules.eda.ml.recommender.dataset import load_company_event_attendance
from app.modules.eda.ml.recommender.recommendation import recommend_historical_line
from app.modules.eda.models.gold_dim_empresa_360 import GoldDimEmpresa360

VERSION = "actho-descriptive-v1"
FIDELITY_MODEL_NAME = "fidelidad_rfm_s"
FIDELITY_SCHEMA_VERSION = "rfm_s_percentiles_v1"
APPROVAL_EXPERIMENTAL = "EXPERIMENTAL"


def _dataset_hash(frame: pd.DataFrame) -> str:
    """Calcula hash determinista de los registros de features usados."""
    payload = frame.sort_values(list(frame.columns), kind="stable").to_json(
        orient="records", date_format="iso", double_precision=8
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _upsert_result(db: Session, row: dict[str, Any], execution_id: str) -> None:
    """Inserta o actualiza únicamente la misma versión y corte (idempotencia)."""
    # pylint: disable=import-outside-toplevel
    from app.modules.eda.models.gold_ml_resultado import GoldMlResultado

    row["id_ejecucion"] = execution_id
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "sqlite":
        sq_stmt = sqlite_insert(GoldMlResultado).values(**row)
        sq_fields = {
            key: getattr(sq_stmt.excluded, key)
            for key in (
                "estado_evaluacion",
                "metodo",
                "score",
                "segmento",
                "soporte",
                "justificacion",
                "metricas",
                "hash_dataset",
            )
        }
        sq_fields["actualizado_en"] = text("CURRENT_TIMESTAMP")
        db.execute(
            sq_stmt.on_conflict_do_update(
                index_elements=[
                    "caso_uso",
                    "id_empresa",
                    "version_modelo",
                    "fecha_corte",
                ],
                set_=sq_fields,
            )
        )
        return
    pg_stmt = pg_insert(GoldMlResultado).values(**row)
    pg_fields = {
        key: getattr(pg_stmt.excluded, key)
        for key in (
            "estado_evaluacion",
            "metodo",
            "score",
            "segmento",
            "soporte",
            "justificacion",
            "metricas",
            "hash_dataset",
        )
    }
    pg_fields["actualizado_en"] = text("CURRENT_TIMESTAMP")
    db.execute(
        pg_stmt.on_conflict_do_update(
            constraint="uq_gold_ml_resultado_caso_empresa_version_corte",
            set_=pg_fields,
        )
    )


def _get_or_export_fidelity_artifact(
    cohort: pd.DataFrame,
    *,
    cutoff_date: date,
    artifacts_root: Path,
    retrain: bool = False,
) -> tuple[Any, ModelManifest, bool]:
    """Reutiliza el artefacto aprobado de Fidelización o lo entrena y exporta."""
    version = f"{VERSION}-{cutoff_date.isoformat()}" if retrain else VERSION
    manifest_path = artifacts_root / FIDELITY_MODEL_NAME / version / "manifest.json"
    if manifest_path.is_file() and not retrain:
        try:
            model, manifest = load_approved_model(manifest_path)
            return model, manifest, True
        except ValueError:
            pass

    candidates = evaluate_fidelity_candidates(cohort, cluster_counts=(2, 3, 4, 5))
    best = next((item for item in candidates if item["algorithm"] == "kmeans"), None)
    if best is None:
        raise ValueError("No se encontró un candidato KMeans válido para RFM-S.")

    model = train_fidelity_model(
        cohort,
        algorithm="kmeans",
        clusters=int(best["clusters"]),
        seed=42,
    )
    validation_metrics: dict[str, float | int | str | bool | None] = {
        key: best[key]
        for key in (
            "clusters",
            "silhouette_mean",
            "davies_bouldin_mean",
            "calinski_harabasz_mean",
            "ari_stability_mean",
            "seeds_evaluated",
        )
    }
    target_version = version
    if (artifacts_root / FIDELITY_MODEL_NAME / target_version).exists():
        target_version = f"{version}-{uuid4().hex[:8]}"

    registration = ModelRegistration(
        model_name=FIDELITY_MODEL_NAME,
        model_version=target_version,
        algorithm="KMeans",
        training_date=datetime.now(timezone.utc),
        training_cutoff=cutoff_date,
        feature_schema_version=FIDELITY_SCHEMA_VERSION,
        training_samples=int(len(cohort)),
        validation_metrics=validation_metrics,
        approved=True,
    )
    manifest = store_model_artifact(
        model,
        registration,
        artifacts_root=artifacts_root,
    )
    return model, manifest, False


def generate_descriptive_results(
    db: Session,
    cutoff: date | None = None,
    *,
    artifacts_root: Path | None = None,
    retrain: bool = False,
) -> dict[str, Any]:
    # Esta función coordina cuatro cohortes; cada bloque conserva sus propias reglas.
    # pylint: disable=too-many-locals
    """Calcula y persiste segmentos, afinidad, churn heurístico y prioridad.

    Exporta o reutiliza el artefacto K-Means de Fidelización en el registro local
    para no re-entrenar en cada corrida si ya existe un manifiesto aprobado.
    """
    cutoff_date = cutoff or date.today()
    fecha_corte = cutoff_date.isoformat()
    execution_id = str(uuid4())
    effective_root = artifacts_root or artifacts_root_from_environment()
    counts: dict[str, Any] = {
        "fidelidad": 0,
        "recomendacion": 0,
        "churn_heuristico": 0,
        "lead_prioridad": 0,
    }

    raw = load_fidelity_dataset(db)
    if not raw.empty:
        features = build_rfm_s_features(raw)
        cohort = get_complete_rfm_s_cohort(features)
        if len(cohort) >= 20:
            model, manifest, reused = _get_or_export_fidelity_artifact(
                cohort,
                cutoff_date=cutoff_date,
                artifacts_root=effective_root,
                retrain=retrain,
            )
            predictions = predict_fidelity_clusters(cohort, model=model)
            cluster_map = dict(
                zip(
                    predictions["id_empresa"],
                    predictions["cluster_id"],
                )
            )
            cohort = cohort.copy()
            cohort["cluster"] = cohort["id_empresa"].map(cluster_map)
            dataset_hash = _dataset_hash(cohort)
            store_prediction_execution(
                manifest,
                artifacts_root=effective_root,
                input_rows=int(len(raw)),
                output_rows=int(len(cohort)),
                rejected_rows=int(len(raw) - len(cohort)),
                target="gold_ml_resultados_empresa",
            )
            metrics = {
                "tipo_score": "indice_rfm_s_descriptivo_0_100",
                "artifact_sha256": manifest.artifact_sha256,
                "artifact_reused": reused,
                **manifest.validation_metrics,
            }
            for record in cohort.to_dict(orient="records"):
                _upsert_result(
                    db,
                    {
                        "caso_uso": "fidelidad_rfm_s",
                        "id_empresa": record["id_empresa"],
                        "version_modelo": manifest.model_version,
                        "fecha_corte": fecha_corte,
                        "estado_evaluacion": APPROVAL_EXPERIMENTAL,
                        "metodo": (
                            "KMeans RFM-S (artefacto reutilizado)"
                            if reused
                            else "KMeans RFM-S (artefacto exportado)"
                        ),
                        "score": float(record["score_fidelidad_ml_0_100"]),
                        "segmento": f"CLUSTER_{int(record['cluster'])}",
                        "soporte": int(len(cohort)),
                        "justificacion": {
                            feature: float(record[feature]) for feature in RFM_COMPONENTS
                        },
                        "metricas": metrics,
                        "hash_dataset": dataset_hash,
                    },
                    execution_id,
                )
                counts["fidelidad"] += 1

    attendance = load_company_event_attendance(db)
    recommendations = recommend_historical_line(attendance)
    if not recommendations.empty:
        dataset_hash = _dataset_hash(attendance)
        totals = (
            attendance.dropna(subset=["id_empresa", "id_evento"])
            .groupby("id_empresa")["id_evento"]
            .nunique()
        )
        for record in recommendations.to_dict(orient="records"):
            company = record["id_empresa"]
            support = int(record["eventos_soporte"])
            denominator = int(totals.get(company, support))
            _upsert_result(
                db,
                {
                    "caso_uso": "recomendacion_linea",
                    "id_empresa": company,
                    "version_modelo": VERSION,
                    "fecha_corte": fecha_corte,
                    "estado_evaluacion": "DESCRIPTIVO",
                    "metodo": "Afinidad histórica por eventos distintos",
                    "score": round(100.0 * support / max(denominator, 1), 2),
                    "segmento": record["linea_2027_recomendada_baseline"],
                    "soporte": support,
                    "justificacion": {
                        "eventos_distintos_linea": support,
                        "eventos_distintos_total": denominator,
                    },
                    "metricas": {
                        "fecha_corte": fecha_corte,
                        "tipo_score": "afinidad_historica_pct",
                    },
                    "hash_dataset": dataset_hash,
                },
                execution_id,
            )
            counts["recomendacion"] += 1

    gold_rows = db.execute(select(GoldDimEmpresa360)).scalars().all()
    for company in gold_rows:
        is_active = company.tipo_relacion_actho == "AFILIADO_ACTIVO"
        score = company.puntaje_riesgo_heuristico if is_active else None
        if score is not None:
            _upsert_result(
                db,
                {
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
                        "alerta_baja_satisfaccion": bool(
                            company.alerta_baja_satisfaccion
                        ),
                        "alerta_monocontacto": bool(company.alerta_monocontacto),
                    },
                    "metricas": {
                        "es_probabilidad": False,
                        "tipo_score": "puntos_heuristicos_gold",
                    },
                    "hash_dataset": None,
                },
                execution_id,
            )
            counts["churn_heuristico"] += 1
        if company.tipo_relacion_actho == "PROSPECTO_NO_AFILIADO":
            engagement = int(company.total_eventos_anio or 0)
            if engagement:
                _upsert_result(
                    db,
                    {
                        "caso_uso": "lead_prioridad",
                        "id_empresa": company.id_empresa,
                        "version_modelo": VERSION,
                        "fecha_corte": fecha_corte,
                        "estado_evaluacion": "DESCRIPTIVO",
                        "metodo": "Priorización por interacción histórica observada",
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
                    },
                    execution_id,
                )
                counts["lead_prioridad"] += 1
    db.commit()
    return {"id_ejecucion": execution_id, **counts}


def list_results(
    db: Session, case: str, *, limit: int = 100, company_id: str | None = None
) -> list[dict[str, Any]]:
    """Devuelve resultados del corte vigente más reciente para consulta API."""
    # pylint: disable=import-outside-toplevel
    from app.modules.eda.models.gold_ml_resultado import GoldMlResultado

    latest = (
        db.query(GoldMlResultado.fecha_corte)
        .filter(GoldMlResultado.caso_uso == case)
        .order_by(GoldMlResultado.fecha_corte.desc())
        .limit(1)
        .scalar_subquery()
    )
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
    # pylint: disable=import-outside-toplevel
    from app.modules.eda.models.gold_ml_resultado import GoldMlResultado

    latest_cutoff = (
        db.query(func.max(GoldMlResultado.fecha_corte))
        .filter(GoldMlResultado.caso_uso == case)
        .scalar()
    )
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
    metadata = (
        db.query(GoldMlResultado)
        .filter(
            GoldMlResultado.caso_uso == case,
            GoldMlResultado.fecha_corte == latest_cutoff,
        )
        .order_by(GoldMlResultado.id.desc())
        .first()
    )
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
