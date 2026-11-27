"""Clasificación temática de encuestas y reserva de columnas ML en capa Gold."""

import re
from typing import Any

import numpy as np
import pandas as pd

REGLAS_TEMAS_NLP: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Derecho Laboral y Reforma",
        (
            "reforma",
            "laboral",
            "decreto",
            "ley",
            "sindic",
            "fuero",
            "pension",
            "disciplinari",
            "juridic",
            "jurídic",
            "contrataci",
            "nomina",
            "nómina",
            "tercerizaci",
            "incapacidad",
            "inspecci",
        ),
    ),
    (
        "IA y Tecnología HR",
        (
            r"\bia\b",
            "inteligencia artificial",
            "automatizaci",
            "chatbot",
            "people analytics",
            "analitica",
            "analítica",
            "tecnolog",
            "agentes",
            "metaverso",
            "microsoft",
        ),
    ),
    (
        "Bienestar y Salud Mental",
        (
            "bienestar",
            "salud mental",
            "burnout",
            "emocion",
            "felicidad",
            "cuidado",
            "espiritual",
            "sismo",
        ),
    ),
    (
        "Compensación y Desempeño",
        (
            "salario",
            "compensaci",
            "beneficio",
            "desempeño",
            "desempeno",
            "remuneraci",
            "finanzas para hr",
        ),
    ),
    (
        "Diversidad e Inclusión",
        (
            "discapacidad",
            "inclusi",
            "genero",
            "género",
            "transgenero",
            "transgénero",
            "generacion",
        ),
    ),
    (
        "Liderazgo y Cultura",
        (
            "liderazgo",
            "cultura",
            "cambio",
            "equipo",
            "marca empleadora",
            "retenci",
            "rotaci",
            "talento",
            "formaci",
            "capacitaci",
            "innovaci",
        ),
    ),
)

COMENTARIOS_NO_TEMATICOS: frozenset[str] = frozenset(
    {
        "",
        ".",
        "-",
        "na",
        "n/a",
        "n a",
        "ninguno",
        "ninguna",
        "no",
        "gracias",
        "muchas gracias",
        "excelente espacio",
        "excelente espacio.",
        "todo muy bien",
    }
)


def clasificar_tema_nlp(comentario: Any) -> str | None:
    """Clasifica un comentario abierto de encuesta en una categoría temática HR.

    Args:
        comentario: Texto libre capturado en temarios_sugeridos.

    Returns:
        Categoría temática homologada o None cuando no aporta un tema concreto.

    """
    if pd.isna(comentario):
        return None
    texto = str(comentario).strip().lower()
    if texto in COMENTARIOS_NO_TEMATICOS or len(texto) < 2:
        return None
    for categoria, patrones in REGLAS_TEMAS_NLP:
        for patron in patrones:
            if patron.startswith(r"\b") and re.search(patron, texto):
                return categoria
            if not patron.startswith(r"\b") and patron in texto:
                return categoria
    if "gracias" in texto and len(texto) < 30:
        return None
    return "Otro"


def inicializar_columnas_ml_reservadas(df_emp_360: pd.DataFrame) -> pd.DataFrame:
    """Inicializa como nulas las columnas reservadas para la rama de modelos ML.

    Args:
        df_emp_360: DataFrame de gold_dim_empresa_360 previo al cálculo del semáforo.

    Returns:
        Copia del DataFrame con las 6 columnas ML reservadas en su tipo esperado.

    """
    res = df_emp_360.copy()
    if "probabilidad_churn_ml" not in res.columns:
        res["probabilidad_churn_ml"] = np.nan
    if "score_fidelidad_ml_0_100" not in res.columns:
        res["score_fidelidad_ml_0_100"] = np.nan
    if "arquetipo_fidelidad_ml" not in res.columns:
        res["arquetipo_fidelidad_ml"] = None
    if "score_conversion_lead_ml_0_100" not in res.columns:
        res["score_conversion_lead_ml_0_100"] = np.nan
    if "linea_2027_recomendada_ml" not in res.columns:
        res["linea_2027_recomendada_ml"] = None
    if "prob_asistencia_prox_evento_ml" not in res.columns:
        res["prob_asistencia_prox_evento_ml"] = np.nan
    return res
