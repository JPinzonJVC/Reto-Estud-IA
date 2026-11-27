"""Pruebas del baseline de afinidad de línea de oferta."""

import pandas as pd

from app.modules.eda.ml.recommender.recommendation import recommend_historical_line


def test_recommendation_counts_distinct_events_not_participant_rows() -> None:
    """Un evento con varias personas no pesa más que eventos distintos."""
    attendance = pd.DataFrame(
        [
            {"id_empresa": "A", "id_evento": 1, "linea_oferta_2027": "Anticipar"},
            {"id_empresa": "A", "id_evento": 1, "linea_oferta_2027": "Anticipar"},
            {"id_empresa": "A", "id_evento": 2, "linea_oferta_2027": "Pares"},
            {"id_empresa": "A", "id_evento": 3, "linea_oferta_2027": "Pares"},
            {"id_empresa": "B", "id_evento": 4, "linea_oferta_2027": "Foro"},
            {"id_empresa": None, "id_evento": 5, "linea_oferta_2027": "Foro"},
        ]
    )

    result = recommend_historical_line(attendance).set_index("id_empresa")

    assert result.loc["A", "linea_2027_recomendada_baseline"] == "Pares"
    assert result.loc["A", "eventos_soporte"] == 2
    assert result.loc["B", "linea_2027_recomendada_baseline"] == "Foro"
    assert len(result) == 2


def test_recommendation_returns_empty_when_no_history_is_linked() -> None:
    """No inventa una recomendación para una empresa sin asistencia enlazada."""
    attendance = pd.DataFrame(
        columns=["id_empresa", "id_evento", "linea_oferta_2027"]
    )

    result = recommend_historical_line(attendance)

    assert result.empty
    assert "linea_2027_recomendada_baseline" in result.columns
