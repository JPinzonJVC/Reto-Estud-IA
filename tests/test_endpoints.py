"""Pruebas unitarias para los endpoints y vistas del aplicativo."""

import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.main import health_check, render_dashboard
from app.modules.affiliates.router import get_affiliates_summary
from app.modules.analytics.router import get_analytics_metrics
from app.modules.retention.router import (
    CustomerEvaluationRequest,
    evaluate_customer,
    get_overview,
)


class TestEndpoints(unittest.TestCase):
    """Casos de prueba para endpoints de salud, retención, analítica y afiliados."""

    def test_health_check(self) -> None:
        """Verifica que el endpoint de salud devuelva estado ok."""
        res = health_check()
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["app"], "Reto EstudIA")

    def test_retention_overview(self) -> None:
        """Verifica la respuesta del resumen del módulo de retención desde Gold."""
        overview = get_overview()
        self.assertIn("total_empresas", overview)
        self.assertIn("membresias_activas", overview)
        self.assertIn("riesgo_rojo_alto", overview)
        self.assertIn("fuente_datos", overview)

    def test_retention_evaluate_customer(self) -> None:
        """Verifica la evaluación puntual de un cliente vía endpoint."""
        req = CustomerEvaluationRequest(
            customer_id="C-99",
            features=[10.0, 2.0],
        )
        with self.assertRaises(HTTPException) as error:
            evaluate_customer(req)
        self.assertEqual(error.exception.status_code, 503)
        self.assertIn("no hay artefacto supervisado", error.exception.detail.lower())

    def test_analytics_metrics(self) -> None:
        """Verifica métricas cuantitativas del módulo de analítica desde Gold."""
        metrics = get_analytics_metrics()
        self.assertIn("total_asistencias", metrics)
        self.assertIn("total_respuestas_encuestas", metrics)
        self.assertIn("promedio_satisfaccion_general_1_5", metrics)
        self.assertIn("participacion_por_modalidad", metrics)

    def test_affiliates_summary(self) -> None:
        """Verifica el resumen de la red de afiliados desde Gold."""
        summary = get_affiliates_summary()
        self.assertIn("total_empresas", summary)
        self.assertIn("afiliados_activos_crm", summary)
        self.assertIn("empresas_con_participacion", summary)

    def test_render_dashboard(self) -> None:
        """Verifica la renderización de la vista principal del dashboard."""
        mock_request = MagicMock()
        response = render_dashboard(mock_request)
        self.assertIsNotNone(response)


if __name__ == "__main__":
    unittest.main()
