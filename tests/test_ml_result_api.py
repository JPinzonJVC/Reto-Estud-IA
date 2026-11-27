"""Pruebas de filtros, paginación y resumen del API ML."""

from unittest.mock import patch

from fastapi import HTTPException
import pytest

from app.modules.machine_learning.router import get_ml_overview, get_ml_results


def test_results_endpoint_forwards_filters_and_pagination() -> None:
    """El contrato de consulta envía filtros al servicio real de paginación."""
    expected = {
        "caso_uso": "recomendacion_linea",
        "fecha_corte": "2026-11-27",
        "version": "actho-descriptive-v1",
        "id_ejecucion": "run-1",
        "total": 1,
        "limit": 12,
        "offset": 12,
        "items": [],
    }
    with (
        patch(
            "app.modules.machine_learning.router.list_result_page",
            return_value=expected,
        ) as service,
        patch(
            "app.modules.machine_learning.router._result_table_exists",
            return_value=True,
        ),
    ):
        response = get_ml_results(
            "recomendacion_linea",
            buscar_empresa="EMP",
            segmento="Foro",
            estado="DESCRIPTIVO",
            limit=12,
            offset=12,
            db=object(),
        )
    assert response == expected
    assert service.call_args.kwargs == {
        "limit": 12,
        "offset": 12,
        "company_search": "EMP",
        "segment": "Foro",
        "status": "DESCRIPTIVO",
    }


def test_results_endpoint_rejects_unknown_case() -> None:
    """Una ruta desconocida responde 404 sin consultar la base."""
    with patch("app.modules.machine_learning.router.list_result_page") as service:
        with pytest.raises(HTTPException) as error:
            get_ml_results("churn_falso", db=object())
    assert error.value.status_code == 404
    service.assert_not_called()


def test_results_endpoint_reports_missing_migration() -> None:
    """Antes de migrar responde 503 y explica el requisito."""
    with patch(
        "app.modules.machine_learning.router._result_table_exists",
        return_value=False,
    ):
        with pytest.raises(HTTPException) as error:
            get_ml_results("fidelidad_rfm_s", db=object())
    assert error.value.status_code == 503


def test_overview_reports_real_counts_and_approved_models() -> None:
    """El resumen agrega casos reales y el registro aprobado configurado."""
    pages = {
        case: {
            "caso_uso": case,
            "fecha_corte": "2026-11-27",
            "version": "v1",
            "id_ejecucion": "run-1",
            "total": count,
            "items": [{"estado": "DESCRIPTIVO"}],
        }
        for case, count in (
            ("fidelidad_rfm_s", 140),
            ("recomendacion_linea", 1197),
            ("churn_heuristico", 435),
            ("lead_prioridad", 720),
        )
    }
    with (
        patch(
            "app.modules.machine_learning.router.list_result_page",
            side_effect=lambda _db, case, **_kwargs: pages[case],
        ),
        patch(
            "app.modules.machine_learning.router._result_table_exists",
            return_value=True,
        ),
        patch(
            "app.modules.machine_learning.router._approved_model_count",
            return_value=0,
        ),
    ):
        payload = get_ml_overview(db=object())
    assert payload["resultados_totales"] == 2492
    assert payload["modelos_aprobados_disponibles"] == 0
    assert len(payload["casos_uso"]) == 4
