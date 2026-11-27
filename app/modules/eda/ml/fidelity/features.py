"""Construcción reproducible del índice RFM-S de fidelidad."""

import pandas as pd

RFM_COMPONENTS = ("recency", "frequency", "amplitude", "tenure", "satisfaction")
COMMUNITY_COLUMNS = (
    "vinculado_comunidades",
    "pilar_hr_estrategico",
    "pilar_mas_que_salario",
    "pilar_talento_que_elige",
    "pilar_gente_que_crece",
)


def build_rfm_s_features(
    frame: pd.DataFrame,
    *,
    recency_cap_days: int = 365,
) -> pd.DataFrame:
    """Calcula componentes percentiles y score compuesto de fidelidad 0–100.

    Las empresas sin asistencia observada reciben recencia mínima dentro de la
    ventana anual. Filas sin satisfacción quedan fuera del score RFM-S para no
    interpretar una respuesta ausente como una valoración neutra o negativa.
    """
    required = {
        "id_empresa",
        "dias_sin_participacion",
        "total_eventos_anio",
        "total_asistencias_anio",
        "personas_distintas_anio",
        "total_ciclos_membresia",
        "satisfaccion_promedio_1_5",
        *COMMUNITY_COLUMNS,
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Faltan columnas para RFM-S: {missing}")
    if frame.empty:
        raise ValueError("No hay empresas activas para construir RFM-S.")
    result = frame.copy()
    coverage = float(result["satisfaccion_promedio_1_5"].notna().mean())
    if coverage == 0.0:
        raise ValueError("No hay satisfacción observada para construir RFM-S.")

    recency = pd.to_numeric(result["dias_sin_participacion"], errors="coerce")
    result["_recency_days"] = recency.clip(lower=0, upper=recency_cap_days).fillna(
        recency_cap_days
    )
    result["_frequency_value"] = pd.to_numeric(
        result["total_eventos_anio"], errors="coerce"
    ).clip(lower=0)
    community_values = result[list(COMMUNITY_COLUMNS)].fillna(False).astype(bool)
    result["_amplitude_value"] = pd.to_numeric(
        result["personas_distintas_anio"], errors="coerce"
    ).fillna(0) + community_values.sum(axis=1)
    result["_tenure_value"] = pd.to_numeric(
        result["total_ciclos_membresia"], errors="coerce"
    ).clip(lower=0)
    result["_satisfaction_value"] = pd.to_numeric(
        result["satisfaccion_promedio_1_5"], errors="coerce"
    ).where(lambda values: values.between(1.0, 5.0))

    result["recency"] = 100.0 * (
        1.0 - result["_recency_days"].rank(method="average", pct=True)
    )
    for component, source in (
        ("frequency", "_frequency_value"),
        ("amplitude", "_amplitude_value"),
        ("tenure", "_tenure_value"),
        ("satisfaction", "_satisfaction_value"),
    ):
        result[component] = 100.0 * result[source].rank(method="average", pct=True)

    score_columns = list(RFM_COMPONENTS)
    result["rfm_s_component_count"] = result[score_columns].notna().sum(axis=1)
    result["score_fidelidad_ml_0_100"] = (
        result[score_columns]
        .mean(axis=1, skipna=True)
        .where(result["_satisfaction_value"].notna())
        .round(2)
    )
    return result


def get_complete_rfm_s_cohort(features: pd.DataFrame) -> pd.DataFrame:
    """Devuelve el subconjunto con las cinco dimensiones observadas para clustering."""
    columns = ["id_empresa", *RFM_COMPONENTS, "score_fidelidad_ml_0_100"]
    return features.dropna(subset=list(RFM_COMPONENTS))[columns].reset_index(drop=True)
