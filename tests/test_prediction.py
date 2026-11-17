"""Pruebas unitarias para las predicciones de inferencia de modelos."""

import unittest

from app.modules.machine_learning.prediction import (
    load_model,
    predict_churn,
    predict_cluster,
)


class TestPrediction(unittest.TestCase):
    """Casos de prueba para las funciones predictivas de churn y cluster."""

    def test_predict_churn_structure(self) -> None:
        """Verifica que la salida de predicción de churn contenga los campos esperados."""
        res = predict_churn([10.0, 3.0])
        self.assertIn("prediction", res)
        self.assertIn("churn_probability", res)
        self.assertIsInstance(res["prediction"], int)
        self.assertIsInstance(res["churn_probability"], float)

    def test_predict_cluster_type(self) -> None:
        """Verifica que la asignación de cluster retorne un entero no nulo."""
        cluster_id = predict_cluster([10.0, 3.0])
        self.assertIsInstance(cluster_id, int)

    def test_load_model_not_found(self) -> None:
        """Verifica que load_model lance FileNotFoundError si no existe el archivo."""
        with self.assertRaises(FileNotFoundError):
            load_model("non_existent_model_12345.pkl")


if __name__ == "__main__":
    unittest.main()
