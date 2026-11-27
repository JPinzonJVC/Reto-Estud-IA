"""Preprocesamiento tabular que se ajusta dentro del pipeline de entrenamiento."""

from collections.abc import Sequence

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def build_tabular_preprocessor(
    *,
    numeric_features: Sequence[str],
    categorical_features: Sequence[str],
) -> ColumnTransformer:
    """Construye transformaciones numéricas y categóricas sin fuga entre splits.

    Args:
        numeric_features: Columnas numéricas aprobadas para el caso de uso.
        categorical_features: Columnas categóricas aprobadas para el caso de uso.

    Returns:
        Transformador para incluir antes del estimador en un `Pipeline` de sklearn.

    Raises:
        ValueError: Si las listas están vacías en conjunto o contienen duplicados.
    """
    all_features = [*numeric_features, *categorical_features]
    if not all_features:
        raise ValueError("Debe especificarse al menos una feature.")
    if len(set(all_features)) != len(all_features):
        raise ValueError("Las features numéricas y categóricas deben ser disjuntas.")

    transformers: list[tuple[str, Pipeline, Sequence[str]]] = []
    if numeric_features:
        numeric_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                ("scaler", StandardScaler()),
            ]
        )
        transformers.append(("numeric", numeric_pipeline, list(numeric_features)))

    if categorical_features:
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("one_hot", OneHotEncoder(handle_unknown="ignore")),
            ]
        )
        transformers.append(
            ("categorical", categorical_pipeline, list(categorical_features))
        )

    return ColumnTransformer(transformers=transformers, remainder="drop")
