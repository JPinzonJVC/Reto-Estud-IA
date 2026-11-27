"""Cliente HTTP para Prefect Server y utilidades de programación Cron del monitor ETL."""

import json
import urllib.request
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.env_vars import OrchestrationEnvs

DIAS_SEMANA_ES: dict[int, str] = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


def _expandir_campo_cron(field: str, min_val: int, max_val: int) -> set[int]:
    """Expande un campo cron estándar (*, */n, a-b, a,b) a un conjunto de enteros."""
    result: set[int] = set()
    for raw_part in field.split(","):
        part = raw_part.strip()
        if not part:
            raise ValueError("Empty cron field")
        step = 1
        if "/" in part:
            base, step_str = part.split("/", 1)
            step = int(step_str)
            if step < 1:
                raise ValueError("Cron interval must be positive")
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
        if start < min_val or end > max_val or start > end:
            raise ValueError("Cron value out of range")
        for num in range(max(min_val, start), min(max_val, end) + 1, step):
            result.add(num)
    if not result:
        raise ValueError("Cron field has no values")
    return result


def calcular_proxima_ejecucion(cron_expr: str, tz_name: str) -> datetime | None:
    """Calcula la próxima fecha/hora de ejecución de una expresión cron de 5 campos."""
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return None
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")

    try:
        minutes = _expandir_campo_cron(parts[0], 0, 59)
        hours = _expandir_campo_cron(parts[1], 0, 23)
        doms = _expandir_campo_cron(parts[2], 1, 31)
        months = _expandir_campo_cron(parts[3], 1, 12)
        dows_raw = _expandir_campo_cron(parts[4], 0, 7)
        dows = {6 if d in (0, 7) else d - 1 for d in dows_raw}
    except (ValueError, IndexError):
        return None

    now = datetime.now(tz).replace(second=0, microsecond=0) + timedelta(minutes=1)
    cursor = now
    for _ in range(370 * 24):
        dom_wildcard = parts[2] == "*"
        dow_wildcard = parts[4] == "*"
        day_matches = (
            cursor.day in doms
            if dow_wildcard
            else (
                cursor.weekday() in dows
                if dom_wildcard
                else cursor.day in doms or cursor.weekday() in dows
            )
        )
        if cursor.month in months and day_matches and cursor.hour in hours:
            for minute in sorted(minutes):
                candidate = cursor.replace(minute=minute)
                if candidate >= now:
                    return candidate
        cursor = (cursor + timedelta(hours=1)).replace(minute=0)
    return None


def describir_cron(cron_expr: str) -> str:
    """Genera una etiqueta legible en español para expresiones cron habituales."""
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


def formatear_delta_es(seconds: float, *, future: bool = False) -> str:
    """Formatea una duración en segundos como 'hace Xh Ym' o 'en Xd Yh'."""
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


def parsear_ts(ts_str: str | None, tz: ZoneInfo) -> datetime | None:
    """Parsea timestamps ISO/auditoría y los convierte a la zona horaria objetivo."""
    if not ts_str:
        return None
    cleaned = str(ts_str).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(tz)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return (
                datetime.strptime(cleaned[:19], fmt)
                .replace(tzinfo=ZoneInfo("UTC"))
                .astimezone(tz)
            )
        except ValueError:
            continue
    return None


def _post_json(url: str, payload: dict[str, Any], timeout: float = 1.5) -> Any:
    """Ejecuta una petición POST JSON ligera con urllib."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else None


def consultar_prefect_live(
    api_url: str, deployment_name: str | None = None
) -> dict[str, Any]:
    """Consulta la API de Prefect Server (flow runs, task runs y deployment activo)."""
    candidatos = [api_url.rstrip("/")]
    if "localhost:4200" in candidatos[0] or "127.0.0.1:4200" in candidatos[0]:
        candidatos.append("http://prefect-server:4200/api")

    filtro_runs = {
        "flow_runs": {
            "state": {"type": {"any_": ["RUNNING", "COMPLETED", "FAILED", "CRASHED"]}}
        },
        "limit": 10,
        "sort": "START_TIME_DESC",
    }
    for base in candidatos:
        try:
            runs = _post_json(f"{base}/flow_runs/filter", filtro_runs, timeout=1.2)
            runs_list = runs if isinstance(runs, list) else []
            dep_id, sched_id, active_cron, active_tz = _leer_deployment_activo(
                base, deployment_name
            )
            active_run = next(
                (
                    r
                    for r in runs_list
                    if str(r.get("state_type", "")).upper()
                    in {"RUNNING", "COMPLETED", "FAILED", "CRASHED", "CANCELLED"}
                    and (not dep_id or r.get("deployment_id") == dep_id)
                ),
                None,
            )
            task_runs: list[dict[str, Any]] = []
            if active_run and active_run.get("id"):
                try:
                    t_res = _post_json(
                        f"{base}/task_runs/filter",
                        {
                            "task_runs": {"flow_run_id": {"any_": [active_run["id"]]}},
                            "limit": 20,
                        },
                        timeout=1.2,
                    )
                    if isinstance(t_res, list):
                        task_runs = t_res
                except Exception:
                    task_runs = []

            return {
                "connected": True,
                "api_url": base,
                "flow_runs": runs_list,
                "latest_executed_run": active_run,
                "task_runs": task_runs,
                "deployment_id": dep_id,
                "schedule_id": sched_id,
                "active_cron": active_cron,
                "active_timezone": active_tz,
            }
        except Exception:  # nosec B112
            continue

    return {
        "connected": False,
        "api_url": candidatos[0],
        "flow_runs": [],
        "latest_executed_run": None,
        "task_runs": [],
        "deployment_id": None,
        "schedule_id": None,
        "active_cron": None,
        "active_timezone": None,
    }


def _leer_deployment_activo(
    base_url: str,
    deployment_name: str | None = None,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Obtiene id de deployment, schedule, cron y zona horaria desde Prefect."""
    try:
        payload: dict[str, Any] = {"limit": 100}
        if deployment_name:
            payload["deployments"] = {"name": {"any_": [deployment_name]}}
        deps = _post_json(f"{base_url}/deployments/filter", payload, timeout=1.2)
        if isinstance(deps, list) and deps:
            dep = deps[0]
            dep_id = dep.get("id")
            scheds = dep.get("schedules") or []
            if scheds:
                sch = scheds[0].get("schedule") or {}
                return dep_id, scheds[0].get("id"), sch.get("cron"), sch.get("timezone")
            return dep_id, None, None, None
    except Exception:  # nosec B110
        pass
    return None, None, None, None


def actualizar_cron_prefect(
    cron_expr: str,
    timezone: str | None = None,
) -> dict[str, Any]:
    """Actualiza en caliente el cron del deployment activo en Prefect Server."""
    cleaned = " ".join(cron_expr.strip().split())
    if len(cleaned.split(" ")) != 5:
        raise ValueError("El cron debe tener exactamente 5 campos (ej. '*/5 * * * *').")
    orch = OrchestrationEnvs()
    tz_name = (timezone or orch.schedule_timezone).strip()
    next_dt = calcular_proxima_ejecucion(cleaned, tz_name)
    if next_dt is None:
        raise ValueError(f"Expresión cron inválida: '{cleaned}'.")

    try:
        ZoneInfo(tz_name)
    except Exception as exc:
        raise ValueError(f"Zona horaria IANA inválida: '{tz_name}'.") from exc
    live = consultar_prefect_live(orch.prefect_api_url, orch.deployment_name)
    if not live["connected"] or not live["deployment_id"]:
        raise RuntimeError(
            "No fue posible conectar con Prefect Server o no existe deployment activo."
        )

    base = str(live["api_url"]).rstrip("/")
    dep_id = live["deployment_id"]
    sched_id = live["schedule_id"]
    schedule_obj = {"cron": cleaned, "timezone": tz_name, "day_or": True}
    if sched_id:
        url = f"{base}/deployments/{dep_id}/schedules/{sched_id}"
        body = json.dumps({"active": True, "schedule": schedule_obj}).encode("utf-8")
        method = "PATCH"
    else:
        url = f"{base}/deployments/{dep_id}/schedules"
        body = json.dumps([{"active": True, "schedule": schedule_obj}]).encode("utf-8")
        method = "POST"

    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method=method
    )
    with urllib.request.urlopen(req, timeout=3.0) as resp:  # nosec B310
        if resp.status not in (200, 201, 204):
            raise RuntimeError(f"Prefect devolvió estado HTTP {resp.status}.")

    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    now_tz = datetime.now(tz)
    return {
        "status": "UPDATED",
        "cron": cleaned,
        "timezone": tz_name,
        "schedule_label": describir_cron(cleaned),
        "next_run_iso": next_dt.strftime("%Y-%m-%d %H:%M"),
        "next_run_in": formatear_delta_es(
            (next_dt - now_tz).total_seconds(), future=True
        ),
    }


def disparar_corrida_prefect(force_reprocess: bool = True) -> dict[str, Any]:
    """Crea un flow_run inmediato sobre el deployment activo en Prefect Server."""
    orch = OrchestrationEnvs()
    live = consultar_prefect_live(orch.prefect_api_url, orch.deployment_name)
    if not live["connected"] or not live["deployment_id"]:
        raise RuntimeError(
            "Prefect Server no tiene un deployment activo registrado todavía."
        )
    base = str(live["api_url"]).rstrip("/")
    dep_id = live["deployment_id"]
    res = _post_json(
        f"{base}/deployments/{dep_id}/create_flow_run",
        {"parameters": {"force_reprocess": force_reprocess}},
        timeout=3.0,
    )
    return {
        "modo": "prefect_deployment",
        "flow_run_id": res.get("id") if isinstance(res, dict) else None,
        "flow_run_name": res.get("name") if isinstance(res, dict) else None,
        "state": res.get("state_type") if isinstance(res, dict) else "SCHEDULED",
    }
