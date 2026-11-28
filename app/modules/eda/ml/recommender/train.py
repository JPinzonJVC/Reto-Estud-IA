"""Evalúa cobertura del baseline de recomendación sin escribir en Gold."""

import json
from typing import Any

from app.database import get_session_factory
from app.modules.eda.ml.recommender.dataset import load_company_event_attendance
from app.modules.eda.ml.recommender.recommendation import recommend_historical_line


def run_recommendation_baseline() -> dict[str, Any]:
    """Resume empresas recomendables y distribución de líneas por afinidad observada."""
    session_factory = get_session_factory()
    with session_factory() as db:
        attendance = load_company_event_attendance(db)
    recommendations = recommend_historical_line(attendance)
    return {
        "attendance_rows": int(len(attendance)),
        "companies_with_linked_history": int(attendance["id_empresa"].nunique()),
        "companies_with_recommendation": int(len(recommendations)),
        "line_distribution": {
            str(line): int(str(count))
            for line, count in recommendations["linea_2027_recomendada_baseline"]
            .value_counts()
            .items()
        },
        "baseline": "MOST_DISTINCT_EVENTS_PER_COMPANY",
        "attendance_probability": None,
        "persistence": "none",
    }


if __name__ == "__main__":
    print(json.dumps(run_recommendation_baseline(), indent=2))
