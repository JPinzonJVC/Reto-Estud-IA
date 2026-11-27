"""Baseline descriptivo de recomendación de línea sin propensión de asistencia."""

import pandas as pd


def recommend_historical_line(attendance: pd.DataFrame) -> pd.DataFrame:
    """Sugiere la línea con más eventos distintos observados por empresa.

    La función no estima asistencia y devuelve resultado solo para empresas con
    historial enlazado. Los empates se resuelven por nombre de línea para mantener
    el resultado reproducible.
    """
    required = {"id_empresa", "id_evento", "linea_oferta_2027"}
    missing = sorted(required - set(attendance.columns))
    if missing:
        raise ValueError(f"Faltan columnas de asistencia: {missing}")
    eligible = attendance.dropna(subset=list(required)).drop_duplicates(
        subset=["id_empresa", "id_evento", "linea_oferta_2027"]
    )
    if eligible.empty:
        return pd.DataFrame(
            columns=[
                "id_empresa",
                "linea_2027_recomendada_baseline",
                "eventos_soporte",
            ]
        )
    counts = (
        eligible.groupby(["id_empresa", "linea_oferta_2027"], as_index=False)
        .agg(eventos_soporte=("id_evento", "nunique"))
        .sort_values(
            ["id_empresa", "eventos_soporte", "linea_oferta_2027"],
            ascending=[True, False, True],
        )
    )
    best = counts.drop_duplicates(subset=["id_empresa"], keep="first")
    return best.rename(
        columns={"linea_oferta_2027": "linea_2027_recomendada_baseline"}
    ).reset_index(drop=True)
