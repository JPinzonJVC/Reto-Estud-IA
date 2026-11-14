"""Pruebas unitarias para el motor de evaluación de riesgo de fuga."""

import unittest

from app.modules.retention.risk_engine import (
    assess_customer_profile,
    evaluate_risk_level,
    recommend_retention_action,
)


class TestRiskEngine(unittest.TestCase):
    """Casos de prueba para las reglas y clasificación del motor de riesgo."""

    def test_evaluate_risk_level(self) -> None:
        """Verifica los umbrales de categorización de riesgo."""
        self.assertEqual(evaluate_risk_level(0.10), "Bajo")
        self.assertEqual(evaluate_risk_level(0.35), "Medio")
        self.assertEqual(evaluate_risk_level(0.60), "Alto")
        self.assertEqual(evaluate_risk_level(0.85), "Crítico")

    def test_recommend_retention_action_high_risk_vip(self) -> None:
        """Valida acción sugerida para riesgo alto en segmento VIP (cluster 1)."""
        action = recommend_retention_action(risk_level="Alto", cluster_id=1)
        self.assertIn("descuento", action.lower())

    def test_recommend_retention_action_low_risk(self) -> None:
        """Valida acción sugerida para riesgo bajo."""
        action = recommend_retention_action(risk_level="Bajo", cluster_id=0)
        self.assertIn("monitoreo", action.lower())

    def test_assess_customer_profile(self) -> None:
        """Verifica la evaluación completa del perfil de cliente."""
        profile = assess_customer_profile(
            customer_id="CLI-100",
            features=[15.0, 2.5],
            cluster_id=0,
        )
        self.assertEqual(profile["customer_id"], "CLI-100")
        self.assertIn("churn_probability", profile)
        self.assertIn("risk_level", profile)
        self.assertIn("recommended_action", profile)


if __name__ == "__main__":
    unittest.main()
