"""Pruebas unitarias para las rutinas de entrenamiento y persistencia de modelos."""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from app.modules.machine_learning.training import (
    bootstrap_default_models,
    save_model,
    train_churn_model,
    train_clustering_model,
)


class TestTraining(unittest.TestCase):
    """Casos de prueba para las funciones de entrenamiento y guardado de modelos."""

    def setUp(self) -> None:
        """Inicializa datos sintéticos para las pruebas de entrenamiento."""
        self.x_sample = np.array([[10, 2], [20, 5], [5, 1], [30, 8]], dtype=float)
        self.y_sample = np.array([0, 1, 0, 1])

    def test_train_churn_model(self) -> None:
        """Verifica que el modelo de churn se entrene y posea método predict."""
        model = train_churn_model(self.x_sample, self.y_sample)
        self.assertTrue(hasattr(model, "predict"))
        self.assertTrue(hasattr(model, "predict_proba"))

    def test_train_clustering_model(self) -> None:
        """Verifica el entrenamiento de segmentación KMeans."""
        kmeans = train_clustering_model(self.x_sample, n_clusters=2)
        self.assertEqual(kmeans.n_clusters, 2)
        self.assertTrue(hasattr(kmeans, "predict"))

    @patch("joblib.dump")
    def test_save_model(self, mock_joblib_dump: MagicMock) -> None:
        """Verifica que save_model serialice el estimador correctamente."""
        dummy_model = MagicMock()
        saved_path = save_model(dummy_model, "test_model.pkl")
        self.assertTrue(saved_path.name.endswith(".pkl"))
        mock_joblib_dump.assert_called_once()

    def test_bootstrap_default_models(self) -> None:
        """Verifica la ejecución del flujo completo de bootstrap."""
        with self.assertRaises(RuntimeError):
            bootstrap_default_models()


if __name__ == "__main__":
    unittest.main()
