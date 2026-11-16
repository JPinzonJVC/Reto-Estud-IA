"""Pruebas unitarias para los endpoints y vistas del aplicativo."""

import unittest
from unittest.mock import MagicMock

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
        """Verifica la respuesta del resumen del módulo de retención."""
        overview = get_overview()
        self.assertIn("total_evaluated", overview)
        self.assertIn("high_risk_count", overview)

    def test_retention_evaluate_customer(self) -> None:
        """Verifica la evaluación puntual de un cliente vía endpoint."""
        req = CustomerEvaluationRequest(
            customer_id="C-99",
            features=[10.0, 2.0],
        )
        eval_res = evaluate_customer(req)
        self.assertEqual(eval_res["customer_id"], "C-99")
        self.assertIn("risk_level", eval_res)

    def test_analytics_metrics(self) -> None:
        """Verifica métricas cuantitativas del módulo de analítica."""
        metrics = get_analytics_metrics()
        self.assertIn("daily_active_users", metrics)
        self.assertIn("conversion_funnel", metrics)

    def test_affiliates_summary(self) -> None:
        """Verifica el resumen de la red de afiliados."""
        summary = get_affiliates_summary()
        self.assertIn("active_affiliates", summary)
        self.assertIn("commission_paid_usd", summary)

    def test_render_dashboard(self) -> None:
        """Verifica la renderización de la vista principal del dashboard."""
        mock_request = MagicMock()
        response = render_dashboard(mock_request)
        self.assertIsNotNone(response)


if __name__ == "__main__":
    unittest.main()
