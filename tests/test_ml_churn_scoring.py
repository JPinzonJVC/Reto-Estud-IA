"""Pruebas de reglas de renovación sin etiquetas ni predicciones sintéticas."""

import pandas as pd
import pytest

from app.modules.eda.ml.churn.scoring import score_renewal_risk


def _risk_frame(**overrides: object) -> pd.DataFrame:
    """Crea una fila de prueba para el score heurístico de renovación."""
    row: dict[str, object] = {
        "id_empresa": "EMP-TEST",
        "is_active_member": True,
        "days_to_expiry": 200,
        "attendances_last_90d": 1,
        "days_since_attendance": 30,
        "satisfaction": 4.0,
        "nps": None,
        "distinct_participants": 4,
        "churn_probability": None,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_risk_score_combines_signals_without_double_counting_inactivity() -> None:
    """Cero asistencias en trimestre no suma otra vez la recencia >90 días."""
    result = score_renewal_risk(
        _risk_frame(
            days_to_expiry=20,
            attendances_last_90d=0,
            days_since_attendance=140,
            satisfaction=3.5,
            nps=6,
            distinct_participants=1,
        )
    ).iloc[0]

    assert result["puntaje_riesgo_heuristico"] == 13
    assert result["semaforo_riesgo_renovacion"] == "ROJO"
    assert "NO_ATTENDANCE_OVER_90D" in result["risk_flags"]
    assert result["risk_flags"].count("NO_ATTENDANCE_LAST_90D") == 1


def test_risk_score_uses_yellow_for_preventive_signal() -> None:
    """Una alerta preventiva sin probabilidad alta queda en amarillo."""
    result = score_renewal_risk(_risk_frame(days_to_expiry=80)).iloc[0]

    assert result["puntaje_riesgo_heuristico"] == 1
    assert result["semaforo_riesgo_renovacion"] == "AMARILLO"


def test_risk_score_marks_non_members_not_applicable() -> None:
    """No calcula riesgo de renovación para prospectos/ex-afiliados."""
    result = score_renewal_risk(_risk_frame(is_active_member=False)).iloc[0]

    assert pd.isna(result["puntaje_riesgo_heuristico"])
    assert result["semaforo_riesgo_renovacion"] == "NO_APLICA"


def test_risk_score_rejects_invalid_probability() -> None:
    """Detiene probabilidades inválidas antes de derivar un semáforo."""
    with pytest.raises(ValueError, match="entre 0 y 1"):
        score_renewal_risk(_risk_frame(churn_probability=1.5))
