"""Ingeniería y extracción de características para los modelos."""

import pandas as pd


def compute_recency_frequency(
    data: pd.DataFrame,
    current_day: int = 365,
) -> pd.DataFrame:
    """Calcula métricas de recurrencia y frecuencia de clientes.

    Args:
        data: DataFrame con historial de transacciones o interacciones.
        current_day: Día de corte de referencia para cálculo de recencia.

    Returns:
        DataFrame con nuevas columnas calculadas de recency y frequency.

    """
    df = data.copy()
    if "last_interaction_day" in df.columns:
        df["recency"] = current_day - df["last_interaction_day"]
    else:
        df["recency"] = 0

    if "interaction_count" in df.columns:
        df["frequency"] = df["interaction_count"]
    else:
        df["frequency"] = 1

    return df


def calculate_interaction_ratio(
    total_actions: int,
    session_count: int,
) -> float:
    """Calcula el ratio promedio de acciones por sesión de usuario.

    Args:
        total_actions: Número total de eventos o acciones registradas.
        session_count: Total de sesiones iniciadas por el usuario.

    Returns:
        Valor decimal que representa el promedio de acciones por sesión.

    """
    if session_count <= 0:
        return 0.0
    return round(float(total_actions) / float(session_count), 2)
