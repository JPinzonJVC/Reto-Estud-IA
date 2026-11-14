"""Pruebas unitarias para las transformaciones de preprocesamiento."""

import unittest

import numpy as np
import pandas as pd

from app.modules.machine_learning.preprocessing import (
    clean_dataset,
    encode_categorical,
    normalize_features,
)


class TestPreprocessing(unittest.TestCase):
    """Pruebas para saneamiento, codificación y normalización de datos."""

    def test_clean_dataset_removes_duplicates(self) -> None:
        """Verifica que se remuevan duplicados y nulos numéricos sean ceros."""
        df_raw = pd.DataFrame(
            {
                "id": [1, 1, 2],
                "score": [10.0, 10.0, None],
            }
        )
        cleaned = clean_dataset(df_raw)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned.loc[2, "score"], 0.0)

    def test_encode_categorical(self) -> None:
        """Verifica la generación de variables dummies categóricas."""
        df_cat = pd.DataFrame({"plan": ["Basic", "Premium", "Basic"]})
        encoded = encode_categorical(df_cat, columns=["plan"])
        self.assertIn("plan_Premium", encoded.columns)

    def test_normalize_features(self) -> None:
        """Verifica que el escalado min-max acote los valores entre 0 y 1."""
        raw_arr = np.array([[0.0, 10.0], [50.0, 20.0], [100.0, 30.0]])
        norm = normalize_features(raw_arr)
        self.assertEqual(norm[0, 0], 0.0)
        self.assertEqual(norm[2, 0], 1.0)
        self.assertTrue(np.all(norm >= 0.0) and np.all(norm <= 1.0))


if __name__ == "__main__":
    unittest.main()
