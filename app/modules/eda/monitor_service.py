"""Servicio de monitoreo de Prefect y trazabilidad del pipeline Medallion."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from app.env_vars import GoogleDriveEnvs, OrchestrationEnvs, ZohoEnvs
from app.modules.eda.models.audit_calidad_datos import AuditCalidadDatos
from app.modules.eda.models.audit_carga import AuditCarga
from app.modules.eda.models.audit_ejecucion_etl import AuditEjecucionEtl
from app.modules.eda.models.audit_hash_fuente_bronze import AuditHashFuenteBronze
from app.modules.eda.models.audit_ingestion_watermark import AuditIngestionWatermark
from app.modules.eda.models.audit_reconciliacion_origen_destino import (
    AuditReconciliacionOrigenDestino,
)
from app.modules.eda.models.audit_registro_duplicado import AuditRegistroDuplicado
from app.modules.eda.models.audit_registro_rechazado import AuditRegistroRechazado
from app.modules.eda.postgres_loader import MAPA_NOMBRE_TABLA_SQL

DIAS_SEMANA_ES: dict[int, str] = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}

ALLOWED_OUTPUT_TABLES: frozenset[str] = frozenset(MAPA_NOMBRE_TABLA_SQL.values())


def _parse_cron_field(field: str, min_val: int, max_val: int) -> set[int]:
    """Expande un campo cron estándar (*, */n, a-b, a,b) a un conjunto de enteros."""
    result: set[int] = set()
    for part in field.split(","):
        part = part.strip()
        if not part:
            continue
        step = 1
        if "/" in part:
            base, step_str = part.split("/", 1)
            step = max(1, int(step_str))
        else:
            base = part
        if base == "*":
            start, end = min_val, max_val
        elif "-" in base:
            s_str, e_str = base.split("-", 1)
            start, end = int(s_str), int(e_str)
        else:
            val = int(base)
            start, end = val, val
        for num in range(max(min_val, start), min(max_val, end) + 1, step):
            result.add(num)
    return result


def calcular_proxima_ejecucion(cron_expr: str, tz_name: str) -> datetime | None:
    """Calcula la próxima ejecución de una expresión cron de 5 campos."""
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return None
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")

    try:
        minutes = _parse_cron_field(parts[0], 0, 59)
        hours = _parse_cron_field(parts[1], 0, 23)
        doms = _parse_cron_field(parts[2], 1, 31)
        months = _parse_cron_field(parts[3], 1, 12)
        dows_raw = _parse_cron_field(parts[4], 0, 7)
        # Cron: 0 o 7 = Domingo; Python weekday(): 0 = Lunes .. 6 = Domingo
        dows = {(d - 1) % 7 for d in dows_raw}
    except ValueError:
        return None

    now = datetime.now(tz).replace(second=0, microsecond=0) + timedelta(minutes=1)
    # Buscar hasta 370 días hacia adelante
    cursor = now
    for _ in range(370 * 24):
        if (
            cursor.month in months
            and cursor.day in doms
            and cursor.weekday() in dows
            and cursor.hour in hours
        ):
            for minute in sorted(minutes):
                candidate = cursor.replace(minute=minute)
                if candidate >= now:
                    return candidate
        cursor = (cursor + timedelta(hours=1)).replace(minute=0)
    return None


def describir_cron(cron_expr: str) -> str:
    """Genera una etiqueta legible en español para expresiones cron frecuentes."""
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return cron_expr
    minute, hour, dom, month, dow = parts
    if minute.isdigit() and hour.isdigit() and dom == "*" and month == "*":
        hora_txt = f"{int(hour):02d}:{int(minute):02d}"
        if dow == "*":
            return f"Diario · {hora_txt}"
        if dow.isdigit():
            dia_py = (int(dow) - 1) % 7
            return f"Semanal · {DIAS_SEMANA_ES.get(dia_py, dow)} {hora_txt}"
    return f"Cron · {cron_expr}"


def _format_delta_es(seconds: float, *, future: bool = False) -> str:
    """Formatea una duración en segundos como 'hace X h Y m' o 'en X d Y h'."""
    total = int(abs(seconds))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    if days > 0:
        body = f"{days}d {hours}h"
    elif hours > 0:
        body = f"{hours}h {mins}m"
    elif mins > 0:
        body = f"{mins}m {secs}s"
    else:
        body = f"{secs}s"
    return f"en {body}" if future else f"hace {body}"


def _parse_ts(ts_str: str | None, tz: ZoneInfo) -> datetime | None:
    """Parsea timestamps de auditoría a datetime con zona horaria."""
    if not ts_str:
        return None
    cleaned = ts_str.strip().replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned[:19], fmt).replace(tzinfo=tz)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(cleaned)
        return dt if dt.tzinfo else dt.replace(tzinfo=tz)
    except ValueError:
        return None


def _consultar_prefect_live(api_url: str) -> dict[str, Any]:
    """Consulta opcionalmente la API de Prefect Server con timeout corto."""
    candidatos = [api_url.rstrip("/")]
    if "localhost:4200" in candidatos[0] or "127.0.0.1:4200" in candidatos[0]:
        candidatos.append("http://prefect-server:4200/api")

    payload = json.dumps({"limit": 10, "sort": "START_TIME_DESC"}).encode("utf-8")
    for base in candidatos:
        url = f"{base}/flow_runs/filter"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                runs = json.loads(resp.read().decode("utf-8"))
                return {
                    "connected": True,
                    "api_url": base,
                    "flow_runs": runs if isinstance(runs, list) else [],
                }
        except Exception:
            continue
    return {"connected": False, "api_url": candidatos[0], "flow_runs": []}


def _resolver_tabla_desde_fuente(fuente: str) -> tuple[str, str, str | None]:
    """Extrae capa, nombre lógico y tabla SQL desde el texto 'origen -> destino'."""
    destino = fuente.split("->")[-1].strip()
    destino_limpio = destino.split("(")[0].strip()
    if "/" in destino_limpio:
        capa, tabla_logica = destino_limpio.split("/", 1)
    else:
        capa, tabla_logica = "silver", destino_limpio
    capa_up = capa.strip().upper()
    tabla_logica = tabla_logica.strip()
    sql_table = MAPA_NOMBRE_TABLA_SQL.get(tabla_logica)
    return capa_up, tabla_logica, sql_table


def _formatear_titulo_etapa(capa: str, tabla_logica: str) -> tuple[str, str]:
    """Genera título y subtítulo legibles para cada etapa de audit_cargas."""
    etiquetas: dict[str, tuple[str, str]] = {
        "dim_kams": ("Construir dimensión KAMs", "Homologación de ejecutivas y métricas de origen"),
        "dim_empresas": ("Construir dimensión Empresas (+SCD2)", "Normalización geográfica, sectorial e historial SCD2"),
        "dim_personas": ("Construir dimensión Personas", "Resolución de vínculo empresarial y cargos"),
        "dim_eventos": ("Construir catálogo de Eventos", "Homologación de oferta 2027 y modalidades"),
        "fact_asistencias": ("Cargar hechos de Asistencias", "Integridad referencial y conciliación con matriz general"),
        "fact_encuestas_satisfaccion": ("Cargar hechos de Encuestas", "Satisfacción 1–5 y clasificación NPS adaptado"),
        "fact_movimientos_crm": ("Cargar hechos de Movimientos CRM", "Afiliaciones, renovaciones y tratos en estado"),
        "agg_participacion_empresa": ("Agregar Gold: Participación por Empresa", "Ventanas móviles 90d, trimestres y recencia"),
        "agg_participacion_eventos": ("Agregar Gold: Participación por Evento", "Convocatoria por línea 2027, modalidad y leads"),
        "agg_satisfaccion_encuestas": ("Agregar Gold: Satisfacción y NPS", "Agregación mensual por modalidad y temarios"),
        "agg_retencion_empresa": ("Agregar Gold: Semáforo de Retención", "Puntaje heurístico de riesgo de no renovación"),
        "agg_segmentos_comunicaciones": ("Generar Gold: 8 Segmentos Comunicaciones", "Listas accionables con control de autorización de datos"),
    }
    if tabla_logica in etiquetas:
        return etiquetas[tabla_logica]
    return f"Transformar {tabla_logica}", f"Flujo hacia capa {capa}"


class EtlMonitorService:
    """Construye la vista operativa de Prefect y auditoría Medallion desde PostgreSQL."""

    def __init__(self, session: Session) -> None:
        """Inicializa el servicio con la sesión SQLAlchemy inyectada."""
        self.session = session

    def obtener_estado_pipeline(self, run_id: str | None = None) -> dict[str, Any]:
        """Retorna el estado integral del flujo Prefect, etapas ETL y programación."""
        orch = OrchestrationEnvs()
        drive_cfg = GoogleDriveEnvs()
        zoho_cfg = ZohoEnvs()
        try:
            tz = ZoneInfo(orch.schedule_timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        prefect_live = _consultar_prefect_live(orch.prefect_api_url)
        next_run_dt = calcular_proxima_ejecucion(orch.schedule_cron, orch.schedule_timezone)
        now_tz = datetime.now(tz)

        ejecuciones = (
            self.session.query(AuditEjecucionEtl)
            .order_by(desc(AuditEjecucionEtl.fecha_inicio))
            .limit(15)
            .all()
        )
        ejec_actual = None
        if run_id:
            ejec_actual = next((e for e in ejecuciones if e.id_ejecucion == run_id), None)
        if ejec_actual is None and ejecuciones:
            ejec_actual = ejecuciones[0]

        watermarks = {
            w.source_name: w
            for w in self.session.query(AuditIngestionWatermark).all()
        }
        hashes = self.session.query(AuditHashFuenteBronze).all()
        calidad_rows = self.session.query(AuditCalidadDatos).all()
        reconcil_map = {
            r.Tabla: r
            for r in self.session.query(AuditReconciliacionOrigenDestino).all()
        }

        steps: list[dict[str, Any]] = []
        order = 1

        # 01. Extractor Google Drive
        wm_drive = watermarks.get(drive_cfg.source_name)
        drive_status = (
            wm_drive.last_status
            if wm_drive
            else ("ENABLED" if drive_cfg.enabled else "SKIPPED")
        )
        steps.append(
            {
                "order": order,
                "step_id": "extract_google_drive",
                "title": "Extractor Google Drive",
                "subtitle": "Descarga incremental de Excel/CSV y conversión de hojas",
                "layer": "EXTRACT",
                "fuente": "google_drive -> input/raw_drive",
                "status": "COMPLETED" if drive_status == "SUCCESS" else drive_status,
                "duration_seconds": None,
                "registros_leidos": wm_drive.records_extracted if wm_drive else 0,
                "registros_procesados": wm_drive.records_extracted if wm_drive else 0,
                "registros_insertados": wm_drive.records_extracted if wm_drive else 0,
                "registros_actualizados": 0,
                "registros_rechazados": 0,
                "fecha_inicio": wm_drive.last_sync_at if wm_drive else None,
                "fecha_finalizacion": wm_drive.updated_at if wm_drive else None,
                "sql_table": None,
                "output_type": "watermark",
                "output_key": drive_cfg.source_name,
                "details": (
                    wm_drive.details
                    if wm_drive and wm_drive.details
                    else ("Habilitado" if drive_cfg.enabled else "Deshabilitado por entorno")
                ),
            }
        )
        order += 1

        # 02. Extractor Zoho CRM
        wm_zoho = watermarks.get(zoho_cfg.source_name)
        zoho_status = (
            wm_zoho.last_status
            if wm_zoho
            else ("ENABLED" if zoho_cfg.enabled else "SKIPPED")
        )
        steps.append(
            {
                "order": order,
                "step_id": "extract_zoho_crm",
                "title": "Extractor Zoho CRM",
                "subtitle": f"Sincronización OAuth2 ({', '.join(zoho_cfg.modules)})",
                "layer": "EXTRACT",
                "fuente": "zoho_crm -> input/raw_zoho",
                "status": "COMPLETED" if zoho_status == "SUCCESS" else zoho_status,
                "duration_seconds": None,
                "registros_leidos": wm_zoho.records_extracted if wm_zoho else 0,
                "registros_procesados": wm_zoho.records_extracted if wm_zoho else 0,
                "registros_insertados": wm_zoho.records_extracted if wm_zoho else 0,
                "registros_actualizados": 0,
                "registros_rechazados": 0,
                "fecha_inicio": wm_zoho.last_sync_at if wm_zoho else None,
                "fecha_finalizacion": wm_zoho.updated_at if wm_zoho else None,
                "sql_table": None,
                "output_type": "watermark",
                "output_key": zoho_cfg.source_name,
                "details": (
                    wm_zoho.details
                    if wm_zoho and wm_zoho.details
                    else ("Habilitado" if zoho_cfg.enabled else "Deshabilitado por entorno")
                ),
            }
        )
        order += 1

        # 03. Ingesta Bronze (SHA-256)
        bronze_filas = sum(int(h.filas_leidas or 0) for h in hashes)
        bronze_ok = all(bool(h.integridad_verificada) for h in hashes) if hashes else False
        steps.append(
            {
                "order": order,
                "step_id": "bronze_validation",
                "title": "Ingesta y verificación Bronze (SHA-256)",
                "subtitle": f"Validación inmutable de {len(hashes)} fuentes normalizadas",
                "layer": "BRONZE",
                "fuente": "input/normalizados -> input/bronze",
                "status": "COMPLETED" if (hashes and bronze_ok) else "PENDING",
                "duration_seconds": 1,
                "registros_leidos": bronze_filas,
                "registros_procesados": bronze_filas,
                "registros_insertados": len(hashes),
                "registros_actualizados": 0,
                "registros_rechazados": 0,
                "fecha_inicio": hashes[0].fecha_hora_ingesta if hashes else None,
                "fecha_finalizacion": hashes[-1].fecha_hora_ingesta if hashes else None,
                "sql_table": "audit_hashes_fuentes_bronze",
                "output_type": "table",
                "output_key": "audit_hashes_fuentes_bronze",
                "details": f"{len(hashes)} archivos verificados con SHA-256",
            }
        )
        order += 1

        # 04..N Etapas de carga Silver y Gold desde audit_cargas
        cargas: list[AuditCarga] = []
        if ejec_actual is not None:
            cargas = (
                self.session.query(AuditCarga)
                .filter(AuditCarga.id_ejecucion == ejec_actual.id_ejecucion)
                .order_by(AuditCarga.fecha_inicio, AuditCarga.fuente)
                .all()
            )
            if not cargas:
                cargas = (
                    self.session.query(AuditCarga)
                    .order_by(AuditCarga.fecha_inicio, AuditCarga.fuente)
                    .all()
                )

        # Orden canónico: Silver primero, luego Gold
        cargas.sort(
            key=lambda c: (
                0 if "-> silver/" in c.fuente else 1,
                c.fecha_inicio or "",
                c.fuente,
            )
        )

        for carga in cargas:
            capa, tabla_logica, sql_table = _resolver_tabla_desde_fuente(carga.fuente)
            titulo, subtitulo = _formatear_titulo_etapa(capa, tabla_logica)
            t_ini = _parse_ts(carga.fecha_inicio, tz)
            t_fin = _parse_ts(carga.fecha_finalizacion, tz)
            dur = (
                max(0, int((t_fin - t_ini).total_seconds()))
                if t_ini and t_fin
                else None
            )
            st = (
                "COMPLETED"
                if (carga.estado_ejecucion or "").upper() == "EXITOSO"
                else (carga.estado_ejecucion or "PENDING").upper()
            )
            rec = reconcil_map.get(tabla_logica)
            cal_cnt = sum(
                1 for q in calidad_rows if (q.tabla_analizada or "") == tabla_logica
            )
            steps.append(
                {
                    "order": order,
                    "step_id": f"stage_{tabla_logica}",
                    "title": titulo,
                    "subtitle": subtitulo,
                    "layer": capa,
                    "fuente": carga.fuente,
                    "status": st,
                    "duration_seconds": dur,
                    "registros_leidos": int(carga.registros_leidos or 0),
                    "registros_procesados": int(carga.registros_procesados or 0),
                    "registros_insertados": int(carga.registros_insertados or 0),
                    "registros_actualizados": int(carga.registros_actualizados or 0),
                    "registros_rechazados": int(carga.registros_rechazados or 0),
                    "fecha_inicio": carga.fecha_inicio,
                    "fecha_finalizacion": carga.fecha_finalizacion,
                    "sql_table": sql_table,
                    "output_type": "table" if sql_table else "audit",
                    "output_key": sql_table or tabla_logica,
                    "quality_rules_count": cal_cnt,
                    "reconciliation_diff": (
                        int(rec.Diferencia_Filas) if rec and rec.Diferencia_Filas is not None else None
                    ),
                }
            )
            order += 1

        # Calcular métricas globales de progreso y tiempos
        active_steps = [s for s in steps if s["status"] != "SKIPPED"]
        completed_steps = sum(1 for s in active_steps if s["status"] == "COMPLETED")
        total_active = max(len(active_steps), 1)
        progress_pct = int(round((completed_steps / total_active) * 100))

        last_start_dt = _parse_ts(ejec_actual.fecha_inicio, tz) if ejec_actual else None
        last_end_dt = _parse_ts(ejec_actual.fecha_finalizacion, tz) if ejec_actual else None
        elapsed_sec = (
            max(0, int((last_end_dt - last_start_dt).total_seconds()))
            if last_start_dt and last_end_dt
            else None
        )
        ago_label = (
            _format_delta_es((now_tz - last_end_dt).total_seconds(), future=False)
            if last_end_dt
            else "Sin ejecuciones"
        )
        next_in_label = (
            _format_delta_es((next_run_dt - now_tz).total_seconds(), future=True)
            if next_run_dt
            else "No programada"
        )

        # Verificar si Prefect reporta una corrida activa en este momento
        live_running = next(
            (
                r
                for r in prefect_live["flow_runs"]
                if str(r.get("state_type", "")).upper() == "RUNNING"
            ),
            None,
        )
        overall_status = (
            "RUNNING"
            if live_running
            else (
                "COMPLETED"
                if ejec_actual and ejec_actual.estado_ejecucion == "EXITOSO"
                else (ejec_actual.estado_ejecucion if ejec_actual else "PENDING")
            )
        )

        dup_count = self.session.query(AuditRegistroDuplicado).count()
        rej_count = self.session.query(AuditRegistroRechazado).count()

        return {
            "flow": {
                "name": "eda-medallion-weekly-pipeline",
                "deployment": orch.deployment_name,
                "schedule_cron": orch.schedule_cron,
                "schedule_timezone": orch.schedule_timezone,
                "schedule_label": describir_cron(orch.schedule_cron),
                "prefect_connected": prefect_live["connected"],
                "prefect_api_url": orch.prefect_api_url,
                "prefect_live_runs": len(prefect_live["flow_runs"]),
            },
            "timing": {
                "run_id": ejec_actual.id_ejecucion if ejec_actual else None,
                "status": overall_status,
                "last_run_start": ejec_actual.fecha_inicio if ejec_actual else None,
                "last_run_end": ejec_actual.fecha_finalizacion if ejec_actual else None,
                "last_run_ago": ago_label,
                "elapsed_seconds": elapsed_sec,
                "next_run_iso": (
                    next_run_dt.strftime("%Y-%m-%d %H:%M") if next_run_dt else None
                ),
                "next_run_in": next_in_label,
            },
            "progress": {
                "percent": progress_pct,
                "completed_steps": completed_steps,
                "total_steps": len(active_steps),
                "total_all_steps": len(steps),
                "archivos_procesados": (
                    int(ejec_actual.archivos_procesados or 0) if ejec_actual else 0
                ),
                "registros_leidos": (
                    int(ejec_actual.registros_leidos or 0) if ejec_actual else 0
                ),
                "registros_cargados": (
                    int(ejec_actual.registros_cargados or 0) if ejec_actual else 0
                ),
                "registros_rechazados": (
                    int(ejec_actual.registros_rechazados or 0) if ejec_actual else 0
                ),
                "duplicados_identificados": (
                    int(ejec_actual.duplicados_identificados or 0)
                    if ejec_actual
                    else dup_count
                ),
                "errores": ejec_actual.errores if ejec_actual else "NINGUNO",
            },
            "steps": steps,
            "history": [
                {
                    "id_ejecucion": e.id_ejecucion,
                    "fecha_inicio": e.fecha_inicio,
                    "fecha_finalizacion": e.fecha_finalizacion,
                    "archivos_procesados": int(e.archivos_procesados or 0),
                    "registros_leidos": int(e.registros_leidos or 0),
                    "registros_cargados": int(e.registros_cargados or 0),
                    "estado_ejecucion": e.estado_ejecucion,
                }
                for e in ejecuciones
            ],
            "quality_summary": {
                "reglas_calidad": len(calidad_rows),
                "duplicados_auditados": int(dup_count),
                "registros_rechazados": int(rej_count),
                "fuentes_bronze_verificadas": len(hashes),
            },
        }

    def obtener_salida_etapa(
        self,
        output_key: str,
        output_type: str = "table",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Consulta una muestra real de la salida ETL de una etapa específica."""
        if output_type == "watermark":
            wm = (
                self.session.query(AuditIngestionWatermark)
                .filter(AuditIngestionWatermark.source_name == output_key)
                .first()
            )
            if wm is None:
                return {
                    "output_key": output_key,
                    "output_type": "watermark",
                    "total_rows": 0,
                    "columns": [],
                    "rows": [],
                    "quality_rules": [],
                    "reconciliation": None,
                    "note": "Sin registro previo en audit_ingestion_watermarks.",
                }
            row_dict = {
                "source_name": wm.source_name,
                "last_status": wm.last_status,
                "last_sync_at": wm.last_sync_at,
                "records_extracted": wm.records_extracted,
                "last_cursor": wm.last_cursor,
                "details": wm.details,
                "updated_at": wm.updated_at,
            }
            return {
                "output_key": output_key,
                "output_type": "watermark",
                "total_rows": 1,
                "columns": list(row_dict.keys()),
                "rows": [row_dict],
                "quality_rules": [],
                "reconciliation": None,
            }

        if output_key not in ALLOWED_OUTPUT_TABLES:
            raise ValueError(f"Tabla de salida ETL no permitida: {output_key}")

        # Consulta segura usando nombre de tabla validado contra ALLOWED_OUTPUT_TABLES
        total_rows = int(
            self.session.execute(
                text(f"SELECT COUNT(*) FROM {output_key}")
            ).scalar()
            or 0
        )
        res = self.session.execute(
            text(f"SELECT * FROM {output_key} LIMIT :lim"), {"lim": limit}
        )
        columns = list(res.keys())
        rows = [
            {col: (None if val is None else str(val)) for col, val in zip(columns, r)}
            for r in res.fetchall()
        ]

        # Buscar reglas de calidad y reconciliación asociadas a la tabla lógica
        tabla_logica = next(
            (k for k, v in MAPA_NOMBRE_TABLA_SQL.items() if v == output_key),
            output_key,
        )
        calidad = (
            self.session.query(AuditCalidadDatos)
            .filter(AuditCalidadDatos.tabla_analizada == tabla_logica)
            .all()
        )
        rec = (
            self.session.query(AuditReconciliacionOrigenDestino)
            .filter(AuditReconciliacionOrigenDestino.Tabla == tabla_logica)
            .first()
        )
        return {
            "output_key": output_key,
            "tabla_logica": tabla_logica,
            "output_type": "table",
            "total_rows": total_rows,
            "columns": columns[:10],
            "total_columns": len(columns),
            "rows": [
                {c: row[c] for c in columns[:10]}
                for row in rows
            ],
            "quality_rules": [
                {
                    "id_incidencia": q.id_incidencia,
                    "campo": q.campo_afectado,
                    "tipo": q.tipo_inconsistencia,
                    "afectados": q.registros_afectados,
                    "estado": q.estado_resolucion,
                    "detalle": q.valor_corregido,
                }
                for q in calidad
            ],
            "reconciliation": (
                {
                    "filas_bronze": rec.Filas_Bronze,
                    "filas_silver": rec.Filas_Silver,
                    "filas_rechazadas": rec.Filas_Rechazadas,
                    "diferencia": rec.Diferencia_Filas,
                    "explicacion": rec.Explicacion_Reconciliacion,
                }
                if rec
                else None
            ),
        }
