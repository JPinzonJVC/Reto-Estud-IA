"""Inferencia de clusters de fidelidad sin consultar ni modificar Silver/Gold."""

import pandas as pd
from sklearn.pipeline import Pipeline

from app.modules.eda.ml.fidelity.features import RFM_COMPONENTS


def predict_fidelity_clusters(
    prepared_cohort: pd.DataFrame,
    *,
    model: Pipeline,
) -> pd.DataFrame:
    """Asigna clusters a features RFM-S ya normalizadas con la referencia del modelo.

    `prepared_cohort` debe haber sido transformado con el mismo esquema y referencia
    de percentiles usados durante el entrenamiento. La función no recalcula percentiles
    para evitar que cambie la escala entre entrenamiento e inferencia.
    """
    required = {"id_empresa", "score_fidelidad_ml_0_100", *RFM_COMPONENTS}
    missing = sorted(required - set(prepared_cohort.columns))
    if missing:
        raise ValueError(f"Faltan columnas RFM-S para inferencia: {missing}")
    eligible = prepared_cohort.dropna(subset=list(RFM_COMPONENTS)).copy()
    if eligible.empty:
        return pd.DataFrame(
            columns=["id_empresa", "score_fidelidad_ml_0_100", "cluster_id"]
        )
    labels = model.predict(eligible[list(RFM_COMPONENTS)].astype(float))
    return pd.DataFrame(
        {
            "id_empresa": eligible["id_empresa"].to_numpy(),
            "score_fidelidad_ml_0_100": eligible["score_fidelidad_ml_0_100"].to_numpy(),
            "cluster_id": labels.astype(int),
        }
    )
