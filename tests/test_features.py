"""Pruebas unitarias para la ingeniería de características."""

import unittest

import pandas as pd

from app.modules.machine_learning.features import (
    calculate_interaction_ratio,
    compute_recency_frequency,
)


class TestFeatures(unittest.TestCase):
    """Pruebas para validación de lógica de extracción de features."""

    def test_compute_recency_frequency(self) -> None:
        """Verifica el cálculo de recencia y frecuencia sobre un DataFrame."""
        df_input = pd.DataFrame(
            {
                "customer_id": ["C1", "C2"],
                "last_interaction_day": [300, 360],
                "interaction_count": [12, 4],
            }
        )
        result = compute_recency_frequency(df_input, current_day=365)
        self.assertIn("recency", result.columns)
        self.assertIn("frequency", result.columns)
        self.assertEqual(result.loc[0, "recency"], 65)
        self.assertEqual(result.loc[1, "recency"], 5)
        self.assertEqual(result.loc[0, "frequency"], 12)

    def test_calculate_interaction_ratio_valid(self) -> None:
        """Valida el cálculo del ratio de interacciones con valores válidos."""
        ratio = calculate_interaction_ratio(total_actions=50, session_count=10)
        self.assertEqual(ratio, 5.0)

    def test_calculate_interaction_ratio_zero_sessions(self) -> None:
        """Valida que no ocurra división por cero cuando las sesiones son 0."""
        ratio = calculate_interaction_ratio(total_actions=20, session_count=0)
        self.assertEqual(ratio, 0.0)


if __name__ == "__main__":
    unittest.main()
