"""Funciones y transformaciones de preprocesamiento de datos."""

import numpy as np
import pandas as pd


def clean_dataset(data: pd.DataFrame) -> pd.DataFrame:
    """Limpia valores nulos y registros duplicados del dataset.

    Args:
        data: DataFrame con los registros crudos de clientes.

    Returns:
        DataFrame saneado sin duplicados ni nulos en campos clave.

    """
    df_cleaned = data.drop_duplicates().copy()
    numeric_cols = df_cleaned.select_dtypes(include=[np.number]).columns
    df_cleaned[numeric_cols] = df_cleaned[numeric_cols].fillna(0)
    return df_cleaned


def encode_categorical(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Aplica codificación one-hot a columnas categóricas especificadas.

    Args:
        data: DataFrame de entrada con columnas categóricas.
        columns: Lista de nombres de columnas a transformar.

    Returns:
        DataFrame transformado con variables dummy.

    """
    return pd.get_dummies(data, columns=columns, drop_first=True)


def normalize_features(
    features: np.ndarray,
) -> np.ndarray:
    """Normaliza un arreglo de características utilizando escala min-max.

    Args:
        features: Arreglo bidimensional de valores numéricos.

    Returns:
        Arreglo normalizado con valores en el rango de 0 a 1.

    """
    min_val = np.min(features, axis=0)
    max_val = np.max(features, axis=0)
    denom = np.where((max_val - min_val) == 0, 1.0, max_val - min_val)
    normalized: np.ndarray = (features - min_val) / denom
    return normalized
