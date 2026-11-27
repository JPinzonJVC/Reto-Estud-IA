"""Pruebas del registro de modelos y ejecuciones de inferencia."""

from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from app.modules.eda.ml.common.registry import (
    ModelRegistration,
    load_approved_model,
    store_model_artifact,
    store_prediction_execution,
)


def _registration(*, approved: bool) -> ModelRegistration:
    """Construye metadatos de prueba sin datos ACTHO."""
    return ModelRegistration(
        model_name="churn",
        model_version="0.1.0-test",
        algorithm="LogisticRegression",
        training_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        training_cutoff=date(2025, 12, 31),
        feature_schema_version="test-v1",
        training_samples=4,
        validation_metrics={"pr_auc": 0.75, "brier_score": 0.2},
        approved=approved,
    )


def _fitted_model() -> LogisticRegression:
    """Ajusta un clasificador mínimo para probar serialización local."""
    model = LogisticRegression(random_state=42).fit(
        np.array([[0.0], [1.0], [2.0], [3.0]]),
        np.array([0, 0, 1, 1]),
    )
    return model


def test_registry_requires_explicit_approval_for_inference(tmp_path: Path) -> None:
    """No permite cargar un modelo exploratorio sin aprobación."""
    manifest = store_model_artifact(
        _fitted_model(), _registration(approved=False), artifacts_root=tmp_path
    )
    path = tmp_path / "churn" / "0.1.0-test" / "manifest.json"

    with pytest.raises(ValueError, match="no está aprobado"):
        load_approved_model(path)

    assert manifest.artifact_sha256
    assert manifest.training_samples == 4


def test_registry_checks_hash_before_loading_and_audits_prediction(
    tmp_path: Path,
) -> None:
    """Carga el modelo aprobado, verifica el hash y registra ejecución agregada."""
    manifest = store_model_artifact(
        _fitted_model(), _registration(approved=True), artifacts_root=tmp_path
    )
    path = tmp_path / "churn" / "0.1.0-test" / "manifest.json"
    model, loaded_manifest = load_approved_model(path)
    assert model.predict(np.array([[2.5]])).shape == (1,)

    execution = store_prediction_execution(
        loaded_manifest,
        artifacts_root=tmp_path,
        input_rows=3,
        output_rows=2,
        rejected_rows=1,
        target="gold_dim_empresa_360",
    )
    assert execution.model_id == manifest.model_id
    assert (tmp_path / "runs" / f"{execution.execution_id}.json").is_file()

    artifact = Path(manifest.artifact_path)
    artifact.write_bytes(artifact.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="hash SHA-256"):
        load_approved_model(path)


def test_registry_rejects_path_traversal_in_model_name(tmp_path: Path) -> None:
    """Impide que nombres de modelo escriban fuera del directorio de artefactos."""
    registration = _registration(approved=False).model_copy(
        update={"model_name": "../outside"}
    )

    with pytest.raises(ValueError, match="caracteres no permitidos"):
        store_model_artifact(_fitted_model(), registration, artifacts_root=tmp_path)
