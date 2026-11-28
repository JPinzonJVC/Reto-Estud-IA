"""Servicio de monitoreo Prefect y trazabilidad del DWH Medallion ACTHO 360."""

from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from app.env_vars import GoogleDriveEnvs, OrchestrationEnvs, ZohoEnvs
from app.modules.eda.models import (
    AuditCalidadDatos,
    AuditCarga,
    AuditEjecucionEtl,
    AuditHashFuenteBronze,
    AuditIngestionWatermark,
    AuditReconciliacionOrigenDestino,
    AuditRegistroRechazado,
)
from app.modules.eda.monitor_prefect_api import (
    actualizar_cron_prefect,
    calcular_proxima_ejecucion,
    consultar_prefect_live,
    describir_cron,
    disparar_corrida_prefect,
    formatear_delta_es,
    parsear_ts,
)
from app.modules.eda.postgres_loader import MAPA_NOMBRE_TABLA_SQL

ROOT_INPUT = Path(__file__).resolve().parents[3] / "input"
ALLOWED_OUTPUT_TABLES: frozenset[str] = frozenset(MAPA_NOMBRE_TABLA_SQL.values())

ETIQUETAS_ETAPAS_DWH: dict[str, tuple[str, str]] = {
    "dim_pais_departamento_ciudad": (
        "Construir jerarquía Geográfica 3NF",
        "Normalización País → Departamento → Ciudad con unicidad UK",
    ),
    "dim_ciudad": (
        "Construir jerarquía Geográfica 3NF",
        "Normalización País → Departamento → Ciudad con unicidad UK",
    ),
    "dim_kams": (
        "Construir dimensión Ejecutivas KAM",
        "Homologación de KAMs y separación de métricas precalculadas",
    ),
    "dim_empresas": (
        "Construir maestro Empresas 3NF",
        "Atributos corporativos, pilares estratégicos y FK ciudad",
    ),
    "membresias": (
        "Construir Catálogo y Ciclos de Membresía",
        "Separación de ciclos reales de afiliación vs. versiones CRM",
    ),
    "dim_personas": (
        "Construir maestro Personas 3NF",
        "Identidad limpia y resolución geográfica del contacto",
    ),
    "bridge_persona_empresa": (
        "Construir Puente Persona-Empresa (N:N)",
        "Trazabilidad de primera/última evidencia y vínculo actual",
    ),
    "dim_eventos": (
        "Construir dimensión Eventos 3NF",
        "Fechas inicio/fin, línea 2027, modalidad y ciudad sede",
    ),
    "fact_asistencias": (
        "Cargar hechos de Asistencias",
        "FK opcional a vínculo N:N, cargo al evento y Habeas Data",
    ),
    "fact_encuestas_satisfaccion": (
        "Cargar hechos de Encuestas",
        "4 calificaciones Likert 1–5 y entero nullable NPS 0–10",
    ),
    "fact_movimientos_crm": (
        "Cargar hechos de Movimientos CRM",
        "Renovaciones, cierres facturados y oportunidades en estado",
    ),
    "fact_asistencias_bi": (
        "Construir Gold: Hechos Asistencias BI",
        "Enriquecimiento dimensional para filtros cruzados",
    ),
    "fact_encuestas_bi": (
        "Construir Gold: Hechos Encuestas BI + NLP",
        "Separación Likert 1–5 vs. NPS 0–10 y taxonomía temática",
    ),
    "dim_empresa_360": (
        "Construir Gold: Dimensión Empresa 360",
        "Semáforo de riesgo, alertas preventivas y columnas ML",
    ),
    "dim_evento_kpis": (
        "Construir Gold: KPIs Estratégicos de Eventos",
        "Penetración en activos, liderazgo C-Level y % leads",
    ),
    "fact_evolucion_membresias_mes": (
        "Construir Gold: Evolución Mensual Membresías",
        "Serie aditiva de altas, vencimientos, renovaciones y retiros",
    ),
    "mart_segmentos_comunicaciones": (
        "Construir Gold: 8 Segmentos Comunicaciones",
        "Listas accionables con validación estricta Habeas Data",
    ),
}


def _resolver_tabla_desde_fuente(fuente: str) -> tuple[str, str, str | None]:
    """Extrae capa, nombre lógico y tabla SQL desde el texto 'origen -> destino'."""
    destino = fuente.split("->")[-1].strip().split("(")[0].strip()
    if "/" in destino:
        capa, tabla_logica = destino.split("/", 1)
    else:
        capa, tabla_logica = "silver", destino
    capa_up = capa.strip().upper()
    tabla_limpia = tabla_logica.strip()
    if tabla_limpia == "dim_pais_departamento_ciudad":
        return capa_up, "dim_ciudad", "silver_dim_ciudad"
    return capa_up, tabla_limpia, MAPA_NOMBRE_TABLA_SQL.get(tabla_limpia)


def _sesion_tiene_auditoria(session: Session | None) -> bool:
    """Comprueba si PostgreSQL está activo y posee registros en audit_ejecuciones_etl."""
    if session is None:
        return False
    try:
        return bool(
            int(session.query(AuditEjecucionEtl.id_ejecucion).limit(1).count()) > 0
        )
    except Exception:
        return False


def _leer_parquet_seguro(carpeta: str, nombre: str) -> pd.DataFrame:
    """Lee un archivo Parquet local devolviendo DataFrame vacío si no existe."""
    ruta = ROOT_INPUT / carpeta / f"{nombre}.parquet"
    return pd.read_parquet(ruta) if ruta.exists() else pd.DataFrame()


def _cargar_insumos_auditoria(session: Session | None) -> dict[str, Any]:
    """Carga tablas de auditoría desde PostgreSQL o respaldo Parquet local."""
    if _sesion_tiene_auditoria(session):
        assert session is not None
        ejec = (
            session.query(AuditEjecucionEtl)
            .order_by(desc(AuditEjecucionEtl.fecha_inicio))
            .limit(15)
            .all()
        )
        return {
            "fuente": "postgresql",
            "ejecuciones": [
                {c.name: getattr(r, c.name) for c in AuditEjecucionEtl.__table__.columns}
                for r in ejec
            ],
            "watermarks": {
                w.source_name: {
                    c.name: getattr(w, c.name)
                    for c in AuditIngestionWatermark.__table__.columns
                }
                for w in session.query(AuditIngestionWatermark).all()
            },
            "hashes": [
                {
                    c.name: getattr(h, c.name)
                    for c in AuditHashFuenteBronze.__table__.columns
                }
                for h in session.query(AuditHashFuenteBronze).all()
            ],
            "cargas": [
                {c.name: getattr(cg, c.name) for c in AuditCarga.__table__.columns}
                for cg in session.query(AuditCarga).all()
            ],
            "calidad": [
                {c.name: getattr(q, c.name) for c in AuditCalidadDatos.__table__.columns}
                for q in session.query(AuditCalidadDatos).all()
            ],
            "reconcil": {
                r.Tabla: {
                    c.name: getattr(r, c.name)
                    for c in AuditReconciliacionOrigenDestino.__table__.columns
                }
                for r in session.query(AuditReconciliacionOrigenDestino).all()
            },
            "rechazados_cnt": int(session.query(AuditRegistroRechazado).count()),
        }

    df_ej = _leer_parquet_seguro("audit", "audit_ejecuciones_etl")
    if not df_ej.empty:
        df_ej = df_ej.sort_values("fecha_inicio", ascending=False).head(15)
    df_rec = _leer_parquet_seguro("audit", "audit_reconciliacion_origen_destino")
    return {
        "fuente": "parquet",
        "ejecuciones": df_ej.to_dict(orient="records"),
        "watermarks": {},
        "hashes": _leer_parquet_seguro("audit", "audit_hashes_fuentes_bronze").to_dict(
            orient="records"
        ),
        "cargas": _leer_parquet_seguro("audit", "audit_cargas").to_dict(orient="records"),
        "calidad": _leer_parquet_seguro("audit", "audit_calidad_datos").to_dict(
            orient="records"
        ),
        "reconcil": {str(r["Tabla"]): r for r in df_rec.to_dict(orient="records")},
        "rechazados_cnt": int(
            len(_leer_parquet_seguro("audit", "audit_registros_rechazados"))
        ),
    }


def _construir_paso_extractor(
    order: int,
    step_id: str,
    title: str,
    subtitle: str,
    *,
    fuente: str,
    source_name: str,
    enabled: bool,
    wm: dict[str, Any] | None,
) -> dict[str, Any]:
    """Construye el descriptor de estado para un extractor (Drive o Zoho)."""
    st = wm["last_status"] if wm else ("ENABLED" if enabled else "SKIPPED")
    rec = int(wm["records_extracted"] or 0) if wm else 0
    return {
        "order": order,
        "step_id": step_id,
        "title": title,
        "subtitle": subtitle,
        "layer": "EXTRACT",
        "fuente": fuente,
        "status": "COMPLETED" if st == "SUCCESS" else st,
        "duration_seconds": None,
        "registros_leidos": rec,
        "registros_procesados": rec,
        "registros_insertados": rec,
        "registros_actualizados": 0,
        "registros_rechazados": 0,
        "fecha_inicio": wm.get("last_sync_at") if wm else None,
        "fecha_finalizacion": wm.get("updated_at") if wm else None,
        "sql_table": None,
        "output_type": "watermark",
        "output_key": source_name,
        "details": (
            wm["details"]
            if wm and wm.get("details")
            else ("Habilitado" if enabled else "Deshabilitado por entorno")
        ),
    }


class EtlMonitorService:
    """Construye la vista operativa de Prefect y auditoría del DWH Medallion."""

    def __init__(self, session: Session | None = None) -> None:
        """Inicializa el servicio con sesión SQLAlchemy opcional."""
        self.session = session

    def obtener_estado_pipeline(  # pylint: disable=too-many-locals
        self, run_id: str | None = None
    ) -> dict[str, Any]:
        """Retorna el estado integral del flujo Prefect, etapas DWH y programación."""
        orch = OrchestrationEnvs()
        drive_cfg = GoogleDriveEnvs()
        zoho_cfg = ZohoEnvs()
        prefect_live = consultar_prefect_live(orch.prefect_api_url, orch.deployment_name)
        eff_cron = str(prefect_live.get("active_cron") or orch.schedule_cron)
        eff_tz = str(prefect_live.get("active_timezone") or orch.schedule_timezone)
        try:
            tz = ZoneInfo(eff_tz)
        except Exception:
            tz = ZoneInfo("UTC")

        next_run_dt = calcular_proxima_ejecucion(eff_cron, eff_tz)
        now_tz = datetime.now(tz)
        aud = _cargar_insumos_auditoria(self.session)
        ejecuciones = aud["ejecuciones"]
        ejec_act = (
            next((e for e in ejecuciones if e["id_ejecucion"] == run_id), None)
            if run_id
            else (ejecuciones[0] if ejecuciones else None)
        )
        if ejec_act is None and ejecuciones:
            ejec_act = ejecuciones[0]

        steps = self._armar_etapas_dwh(aud, ejec_act, drive_cfg, zoho_cfg, tz)
        act_steps = [s for s in steps if s["status"] != "SKIPPED"]
        comp_steps = sum(1 for s in act_steps if s["status"] == "COMPLETED")
        prog_pct = int(round(comp_steps / max(len(act_steps), 1) * 100))

        last_s = parsear_ts(ejec_act["fecha_inicio"], tz) if ejec_act else None
        last_e = parsear_ts(ejec_act["fecha_finalizacion"], tz) if ejec_act else None
        p_run = prefect_live.get("latest_executed_run")
        p_state = str(p_run.get("state_type", "")).upper() if p_run else ""
        p_start = parsear_ts(p_run.get("start_time"), tz) if p_run else None
        p_end = parsear_ts(p_run.get("end_time"), tz) if p_run else None
        p_newer = bool(p_start and (last_e is None or p_start > last_e))
        eff_last = (p_end or p_start) if p_newer and (p_end or p_start) else last_e

        overall, prog_pct = self._resolver_estado_global(
            p_state, p_newer, prefect_live.get("task_runs") or [], ejec_act, prog_pct
        )
        return {
            "flow": {
                "name": "eda-medallion-weekly-pipeline",
                "deployment": orch.deployment_name,
                "schedule_cron": eff_cron,
                "schedule_timezone": eff_tz,
                "schedule_label": describir_cron(eff_cron),
                "prefect_connected": prefect_live["connected"],
                "prefect_api_url": orch.prefect_api_url,
                "prefect_live_runs": len(prefect_live["flow_runs"]),
                "prefect_latest_run_name": p_run.get("name") if p_run else None,
                "prefect_latest_state": p_state or None,
                "prefect_latest_run_id": p_run.get("id") if p_run else None,
                "prefect_latest_run_start": p_run.get("start_time") if p_run else None,
                "prefect_latest_run_end": p_run.get("end_time") if p_run else None,
                "prefect_latest_message": (
                    str((p_run.get("state") or {}).get("message") or "")
                    if p_run and isinstance(p_run.get("state"), dict)
                    else None
                ),
                "prefect_skipped_no_changes": bool(p_newer and p_state == "COMPLETED"),
                "fuente_auditoria": aud["fuente"],
            },
            "timing": {
                "run_id": ejec_act["id_ejecucion"] if ejec_act else None,
                "status": overall,
                "last_run_start": (
                    last_s.strftime("%Y-%m-%d %H:%M:%S") if last_s else None
                ),
                "last_run_end": (
                    eff_last.strftime("%Y-%m-%d %H:%M:%S") if eff_last else None
                ),
                "last_medallion_end": (
                    last_e.strftime("%Y-%m-%d %H:%M:%S") if last_e else None
                ),
                "last_run_ago": (
                    formatear_delta_es((now_tz - eff_last).total_seconds())
                    if eff_last
                    else "Sin ejecuciones"
                ),
                "elapsed_seconds": (
                    max(0, int((last_e - last_s).total_seconds()))
                    if last_s and last_e
                    else None
                ),
                "next_run_iso": (
                    next_run_dt.strftime("%Y-%m-%d %H:%M") if next_run_dt else None
                ),
                "next_run_in": (
                    formatear_delta_es(
                        (next_run_dt - now_tz).total_seconds(), future=True
                    )
                    if next_run_dt
                    else "No programada"
                ),
            },
            "progress": {
                "percent": prog_pct,
                "completed_steps": comp_steps,
                "total_steps": len(act_steps),
                "total_all_steps": len(steps),
                "archivos_procesados": (
                    int(ejec_act["archivos_procesados"] or 0) if ejec_act else 0
                ),
                "registros_leidos": (
                    int(ejec_act["registros_leidos"] or 0) if ejec_act else 0
                ),
                "registros_cargados": (
                    int(ejec_act["registros_cargados"] or 0) if ejec_act else 0
                ),
                "registros_rechazados": (
                    int(ejec_act["registros_rechazados"] or 0) if ejec_act else 0
                ),
                "errores": ejec_act["errores"] if ejec_act else "NINGUNO",
            },
            "steps": steps,
            "history": [
                {
                    "id_ejecucion": e["id_ejecucion"],
                    "fecha_inicio": e["fecha_inicio"],
                    "fecha_finalizacion": e["fecha_finalizacion"],
                    "archivos_procesados": int(e["archivos_procesados"] or 0),
                    "registros_leidos": int(e["registros_leidos"] or 0),
                    "registros_cargados": int(e["registros_cargados"] or 0),
                    "estado_ejecucion": e["estado_ejecucion"],
                }
                for e in ejecuciones
            ],
            "quality_summary": {
                "reglas_calidad": len(aud["calidad"]),
                "registros_rechazados": aud["rechazados_cnt"],
                "fuentes_bronze_verificadas": len(aud["hashes"]),
            },
        }

    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    def _armar_etapas_dwh(
        self,
        aud: dict[str, Any],
        ejec_act: dict[str, Any] | None,
        drive_cfg: GoogleDriveEnvs,
        zoho_cfg: ZohoEnvs,
        tz: ZoneInfo,
    ) -> list[dict[str, Any]]:
        """Construye la lista secuencial Extract -> Bronze -> Silver 3NF -> Gold."""
        wms = aud["watermarks"]
        hashes = aud["hashes"]
        steps = [
            _construir_paso_extractor(
                1,
                "extract_google_drive",
                "Extractor Google Drive",
                "Descarga incremental de Excel/CSV y conversión de hojas",
                fuente="google_drive -> input/raw_drive",
                source_name=drive_cfg.source_name,
                enabled=drive_cfg.enabled,
                wm=wms.get(drive_cfg.source_name),
            ),
            _construir_paso_extractor(
                2,
                "extract_zoho_crm",
                "Extractor Zoho CRM",
                f"Sincronización OAuth2 ({', '.join(zoho_cfg.modules)})",
                fuente="zoho_crm -> input/raw_zoho",
                source_name=zoho_cfg.source_name,
                enabled=zoho_cfg.enabled,
                wm=wms.get(zoho_cfg.source_name),
            ),
        ]
        b_filas = sum(int(h.get("filas_leidas") or 0) for h in hashes)
        b_ok = all(bool(h.get("integridad_verificada")) for h in hashes) and bool(hashes)
        steps.append(
            {
                "order": 3,
                "step_id": "bronze_validation",
                "title": "Ingesta y verificación Bronze (SHA-256)",
                "subtitle": f"Validación criptográfica de {len(hashes)} fuentes base",
                "layer": "BRONZE",
                "fuente": "input/normalizados -> input/bronze",
                "status": "COMPLETED" if b_ok else "PENDING",
                "duration_seconds": 1,
                "registros_leidos": b_filas,
                "registros_procesados": b_filas,
                "registros_insertados": len(hashes),
                "registros_actualizados": 0,
                "registros_rechazados": 0,
                "fecha_inicio": hashes[0]["fecha_hora_ingesta"] if hashes else None,
                "fecha_finalizacion": (
                    hashes[-1]["fecha_hora_ingesta"] if hashes else None
                ),
                "sql_table": "audit_hashes_fuentes_bronze",
                "output_type": "table",
                "output_key": "audit_hashes_fuentes_bronze",
                "details": f"{len(hashes)} archivos verificados con SHA-256",
            }
        )

        cargas = [
            c
            for c in aud["cargas"]
            if not ejec_act or c.get("id_ejecucion") == ejec_act["id_ejecucion"]
        ] or list(aud["cargas"])
        cargas.sort(
            key=lambda c: (
                0 if "-> silver/" in str(c.get("fuente")) else 1,
                str(c.get("fecha_inicio") or ""),
            )
        )
        order = 4
        for cg in cargas:
            capa, t_log, sql_t = _resolver_tabla_desde_fuente(str(cg["fuente"]))
            tit, sub = ETIQUETAS_ETAPAS_DWH.get(
                t_log, (f"Transformar {t_log}", f"Flujo hacia capa {capa}")
            )
            t_ini = parsear_ts(cg.get("fecha_inicio"), tz)
            t_fin = parsear_ts(cg.get("fecha_finalizacion"), tz)
            rec = aud["reconcil"].get(t_log)
            steps.append(
                {
                    "order": order,
                    "step_id": f"stage_{t_log}",
                    "title": tit,
                    "subtitle": sub,
                    "layer": capa,
                    "fuente": cg["fuente"],
                    "status": (
                        "COMPLETED"
                        if str(cg.get("estado_ejecucion", "")).upper() == "EXITOSO"
                        else str(cg.get("estado_ejecucion") or "PENDING").upper()
                    ),
                    "duration_seconds": (
                        max(0, int((t_fin - t_ini).total_seconds()))
                        if t_ini and t_fin
                        else None
                    ),
                    "registros_leidos": int(cg.get("registros_leidos") or 0),
                    "registros_procesados": int(cg.get("registros_procesados") or 0),
                    "registros_insertados": int(cg.get("registros_insertados") or 0),
                    "registros_actualizados": int(cg.get("registros_actualizados") or 0),
                    "registros_rechazados": int(cg.get("registros_rechazados") or 0),
                    "fecha_inicio": cg.get("fecha_inicio"),
                    "fecha_finalizacion": cg.get("fecha_finalizacion"),
                    "sql_table": sql_t,
                    "output_type": "table" if sql_t else "audit",
                    "output_key": sql_t or t_log,
                    "reconciliation_diff": (
                        int(rec["Diferencia_Filas"])
                        if rec and pd.notna(rec.get("Diferencia_Filas"))
                        else None
                    ),
                }
            )
            order += 1
        return steps

    @staticmethod
    def _resolver_estado_global(
        p_state: str,
        p_newer: bool,
        p_tasks: list[dict[str, Any]],
        ejec_act: dict[str, Any] | None,
        prog_pct: int,
    ) -> tuple[str, int]:
        """Determina el estado global combinando Prefect live y auditoría DWH."""
        done_t = sum(
            1 for t in p_tasks if str(t.get("state_type", "")).upper() == "COMPLETED"
        )
        if p_state == "RUNNING":
            return "RUNNING", min(95, max(15, int(round((done_t / 4) * 100))))
        if p_newer and p_state in {"FAILED", "CRASHED", "CANCELLED"}:
            return "FAILED", min(90, max(10, int(round((done_t / 4) * 100))))
        if ejec_act and ejec_act.get("estado_ejecucion") == "EXITOSO":
            return "COMPLETED", prog_pct
        return (
            str(ejec_act.get("estado_ejecucion")) if ejec_act else "PENDING"
        ), prog_pct

    def obtener_salida_etapa(
        self,
        output_key: str,
        output_type: str = "table",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Consulta una muestra real de la salida de una etapa (SQL o Parquet)."""
        if output_type == "watermark":
            aud = _cargar_insumos_auditoria(self.session)
            wm = aud["watermarks"].get(output_key)
            if not wm:
                return {
                    "output_key": output_key,
                    "output_type": "watermark",
                    "total_rows": 0,
                    "columns": [],
                    "rows": [],
                    "quality_rules": [],
                    "reconciliation": None,
                    "note": "Sin ejecuciones incrementales previas registradas.",
                }
            return {
                "output_key": output_key,
                "output_type": "watermark",
                "total_rows": 1,
                "columns": list(wm.keys()),
                "rows": [wm],
                "quality_rules": [],
                "reconciliation": None,
            }

        if output_key not in ALLOWED_OUTPUT_TABLES:
            raise ValueError(f"Tabla de salida ETL no permitida: {output_key}")

        tabla_logica = next(
            (k for k, v in MAPA_NOMBRE_TABLA_SQL.items() if v == output_key),
            output_key,
        )
        total_rows, columns, rows = self._leer_muestra_tabla(
            output_key, tabla_logica, limit
        )
        aud = _cargar_insumos_auditoria(self.session)
        calidad = [
            {
                "id_incidencia": q["id_incidencia"],
                "campo": q["campo_afectado"],
                "tipo": q["tipo_inconsistencia"],
                "afectados": q["registros_afectados"],
                "estado": q["estado_resolucion"],
                "detalle": q["valor_corregido"],
            }
            for q in aud["calidad"]
            if q.get("tabla_analizada") == tabla_logica
        ]
        rec = aud["reconcil"].get(tabla_logica)
        return {
            "output_key": output_key,
            "tabla_logica": tabla_logica,
            "output_type": "table",
            "total_rows": total_rows,
            "columns": columns[:10],
            "total_columns": len(columns),
            "rows": [{c: row[c] for c in columns[:10]} for row in rows],
            "quality_rules": calidad,
            "reconciliation": (
                {
                    "filas_bronze": int(rec["Filas_Bronze"]),
                    "filas_silver": int(rec["Filas_Silver"]),
                    "filas_rechazadas": int(rec["Filas_Rechazadas"]),
                    "diferencia": int(rec["Diferencia_Filas"]),
                    "explicacion": rec["Explicacion_Reconciliacion"],
                }
                if rec
                else None
            ),
        }

    def _leer_muestra_tabla(
        self, sql_table: str, tabla_logica: str, limit: int
    ) -> tuple[int, list[str], list[dict[str, Any]]]:
        """Obtiene conteo total y muestra desde PostgreSQL o Parquet local."""
        if _sesion_tiene_auditoria(self.session):
            assert self.session is not None
            total = int(
                self.session.execute(
                    text(f"SELECT COUNT(*) FROM {sql_table}")  # nosec B608
                ).scalar()
                or 0
            )
            res = self.session.execute(
                text(f"SELECT * FROM {sql_table} LIMIT :lim"),  # nosec B608
                {"lim": limit},
            )
            cols = list(res.keys())
            filas = [
                {col: (None if val is None else str(val)) for col, val in zip(cols, r)}
                for r in res.fetchall()
            ]
            return total, cols, filas

        carpeta = (
            "silver"
            if sql_table.startswith("silver_")
            else ("gold" if sql_table.startswith("gold_") else "audit")
        )
        df = _leer_parquet_seguro(carpeta, tabla_logica)
        if df.empty:
            return 0, [], []
        cols = list(df.columns)
        sub = df.head(limit)
        filas = [
            {c: (None if pd.isna(r[c]) else str(r[c])) for c in cols}
            for _, r in sub.iterrows()
        ]
        return int(len(df)), cols, filas


__all__ = ["EtlMonitorService", "actualizar_cron_prefect", "disparar_corrida_prefect"]
