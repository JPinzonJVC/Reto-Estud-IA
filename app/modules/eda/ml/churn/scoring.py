"""Semáforo híbrido heurístico independiente de la probabilidad ML de churn."""

from collections.abc import Mapping
from math import isfinite
from typing import Any

import pandas as pd

SATISFACTION_THRESHOLD = 3.75
RED_PROBABILITY_THRESHOLD = 0.65
YELLOW_PROBABILITY_THRESHOLD = 0.35


def _number(value: Any) -> float | None:
    """Convierte un valor numérico nullable y descarta infinitos."""
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return number if isfinite(number) else None


def _has_signal(row: Mapping[str, Any]) -> tuple[int, list[str], bool]:
    """Calcula puntos y motivos, evitando duplicar dos señales de inactividad."""
    points = 0
    flags: list[str] = []
    days_to_expiry = _number(row.get("days_to_expiry"))
    if days_to_expiry is not None:
        if days_to_expiry <= 30:
            points += 3
            flags.append("EXPIRY_0_30D")
        elif days_to_expiry <= 60:
            points += 2
            flags.append("EXPIRY_31_60D")
        elif days_to_expiry <= 90:
            points += 1
            flags.append("EXPIRY_61_90D")

    attendance_count = _number(row.get("attendances_last_90d"))
    days_since_attendance = _number(row.get("days_since_attendance"))
    participation_points = 0
    if attendance_count == 0:
        participation_points = 3
        flags.append("NO_ATTENDANCE_LAST_90D")
    elif days_since_attendance is not None and days_since_attendance > 90:
        participation_points = 2
        flags.append("NO_ATTENDANCE_OVER_90D")
    if attendance_count == 0 and days_since_attendance is not None:
        if days_since_attendance > 90 and "NO_ATTENDANCE_OVER_90D" not in flags:
            flags.append("NO_ATTENDANCE_OVER_90D")
    points += participation_points

    satisfaction = _number(row.get("satisfaction"))
    satisfaction_low = satisfaction is not None and satisfaction < SATISFACTION_THRESHOLD
    if satisfaction_low:
        points += 3
        flags.append("LOW_SATISFACTION")

    nps = _number(row.get("nps"))
    nps_detractor = nps is not None and nps <= 6
    if nps_detractor:
        points += 3
        flags.append("NPS_DETRACTOR")

    participants = _number(row.get("distinct_participants"))
    if participants == 1:
        points += 1
        flags.append("SINGLE_PARTICIPANT")

    critical = (
        days_to_expiry is not None
        and 0 <= days_to_expiry <= 30
        and participation_points > 0
        and (satisfaction_low or nps_detractor)
    )
    return points, flags, critical


def score_renewal_risk(frame: pd.DataFrame) -> pd.DataFrame:
    """Calcula score heurístico y semáforo sin inferir etiquetas ni persistir Gold.

    Participation signals are mutually exclusive: zero attendance in the last
    90 days contributes three points; long recency contributes two only when the
    quarterly count is not zero. This prevents double counting the same inactivity.
    """
    required = {
        "id_empresa",
        "is_active_member",
        "days_to_expiry",
        "attendances_last_90d",
        "days_since_attendance",
        "satisfaction",
        "nps",
        "distinct_participants",
        "churn_probability",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Faltan columnas para el score de renovación: {missing}")

    results: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        if row["is_active_member"] is not True:
            results.append(
                {
                    "id_empresa": row["id_empresa"],
                    "puntaje_riesgo_heuristico": None,
                    "semaforo_riesgo_renovacion": "NO_APLICA",
                    "risk_flags": [],
                }
            )
            continue

        points, flags, critical = _has_signal(row)
        probability = _number(row.get("churn_probability"))
        if probability is not None and not 0.0 <= probability <= 1.0:
            raise ValueError("`churn_probability` debe estar entre 0 y 1.")

        red = critical or (
            probability is not None and probability >= RED_PROBABILITY_THRESHOLD
        )
        yellow = bool(flags) or (
            probability is not None and probability >= YELLOW_PROBABILITY_THRESHOLD
        )
        traffic_light = "ROJO" if red else "AMARILLO" if yellow else "VERDE"
        results.append(
            {
                "id_empresa": row["id_empresa"],
                "puntaje_riesgo_heuristico": points,
                "semaforo_riesgo_renovacion": traffic_light,
                "risk_flags": flags,
            }
        )
    return pd.DataFrame(results)
