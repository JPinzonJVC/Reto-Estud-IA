"""Registro local versionado de artefactos y ejecuciones de inferencia aprobadas."""

from datetime import date, datetime, timezone
import hashlib
import os
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

import joblib
from pydantic import BaseModel, ConfigDict, Field

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


class ModelRegistration(BaseModel):
    """Metadatos de entrenamiento que acompañan un artefacto serializado."""

    model_name: str
    model_version: str
    algorithm: str
    training_date: datetime
    training_cutoff: date
    feature_schema_version: str
    training_samples: int = Field(gt=0)
    validation_metrics: dict[str, float | int | str | bool | None]
    approved: bool = False
    execution_id: str = Field(default_factory=lambda: str(uuid4()))

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        protected_namespaces=(),
    )


class ModelManifest(ModelRegistration):
    """Metadatos persistidos e integridad del artefacto ML."""

    model_id: str
    artifact_path: str
    artifact_sha256: str


class PredictionExecution(BaseModel):
    """Auditoría agregada de una ejecución de inferencia aprobada."""

    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    model_id: str
    model_name: str
    model_version: str
    artifact_sha256: str
    prediction_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    input_rows: int = Field(ge=0)
    output_rows: int = Field(ge=0)
    rejected_rows: int = Field(ge=0)
    feature_schema_version: str
    target: str

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        protected_namespaces=(),
    )


def _validate_name(value: str, field_name: str) -> str:
    """Valida que nombres de archivos no incluyan rutas o traversal."""
    if not SAFE_NAME.fullmatch(value):
        raise ValueError(f"`{field_name}` contiene caracteres no permitidos.")
    return value


def _sha256(path: Path) -> str:
    """Calcula el hash del archivo por bloques para limitar memoria."""
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def store_model_artifact(
    model: Any,
    registration: ModelRegistration,
    *,
    artifacts_root: Path,
) -> ModelManifest:
    """Guarda un modelo joblib y manifiesto JSON mediante reemplazo atómico.

    Args:
        model: Estimador o pipeline sklearn entrenado.
        registration: Metadatos de entrenamiento y evaluación.
        artifacts_root: Directorio externo a Git para artefactos versionados.
    """
    model_name = _validate_name(registration.model_name, "model_name")
    model_version = _validate_name(registration.model_version, "model_version")
    root = artifacts_root.expanduser().resolve()
    model_dir = (root / model_name / model_version).resolve()
    if not model_dir.is_relative_to(root):
        raise ValueError("La ruta del artefacto debe permanecer bajo artifacts_root.")
    model_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{model_name}-{model_version}.joblib"
    artifact_path = model_dir / filename
    temporary_artifact = model_dir / f".{filename}.{uuid4().hex}.tmp"
    temporary_manifest = model_dir / f".manifest.{uuid4().hex}.tmp"
    manifest_path = model_dir / "manifest.json"
    if artifact_path.exists() or manifest_path.exists():
        raise FileExistsError("La versión de modelo ya existe y es inmutable.")
    try:
        joblib.dump(model, temporary_artifact)
        os.replace(temporary_artifact, artifact_path)
        manifest = ModelManifest(
            **registration.model_dump(),
            model_id=str(uuid4()),
            artifact_path=str(artifact_path),
            artifact_sha256=_sha256(artifact_path),
        )
        temporary_manifest.write_text(
            manifest.model_dump_json(indent=2), encoding="utf-8"
        )
        os.replace(temporary_manifest, manifest_path)
    finally:
        temporary_artifact.unlink(missing_ok=True)
        temporary_manifest.unlink(missing_ok=True)
    return manifest


def load_approved_model(manifest_path: Path) -> tuple[Any, ModelManifest]:
    """Carga solo modelos aprobados y cuyo hash corresponda al manifiesto."""
    manifest = ModelManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    if not manifest.approved:
        raise ValueError("El modelo no está aprobado para inferencia.")
    artifact_path = Path(manifest.artifact_path).resolve()
    expected_path = (
        manifest_path.resolve().parent
        / f"{manifest.model_name}-{manifest.model_version}.joblib"
    ).resolve()
    if artifact_path != expected_path:
        raise ValueError("La ruta del artefacto no coincide con el manifiesto local.")
    if not artifact_path.is_file() or _sha256(artifact_path) != manifest.artifact_sha256:
        raise ValueError("El artefacto falta o no coincide con su hash SHA-256.")
    return joblib.load(artifact_path), manifest


def store_prediction_execution(
    manifest: ModelManifest,
    *,
    artifacts_root: Path,
    input_rows: int,
    output_rows: int,
    rejected_rows: int,
    target: str,
) -> PredictionExecution:
    """Registra una ejecución sin filas personales ni valores de predicción."""
    if not manifest.approved:
        raise ValueError("No se registra inferencia para un modelo no aprobado.")
    artifact_path = Path(manifest.artifact_path).resolve()
    if not artifact_path.is_file() or _sha256(artifact_path) != manifest.artifact_sha256:
        raise ValueError("No se registra inferencia para un artefacto inválido.")
    if output_rows + rejected_rows > input_rows:
        raise ValueError("Las filas de salida/rechazadas exceden las filas de entrada.")
    for field_name, value in (("model_name", manifest.model_name), ("target", target)):
        _validate_name(value, field_name)
    execution = PredictionExecution(
        model_id=manifest.model_id,
        model_name=manifest.model_name,
        model_version=manifest.model_version,
        artifact_sha256=manifest.artifact_sha256,
        input_rows=input_rows,
        output_rows=output_rows,
        rejected_rows=rejected_rows,
        feature_schema_version=manifest.feature_schema_version,
        target=target,
    )
    runs_dir = (artifacts_root.expanduser().resolve() / "runs").resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{execution.execution_id}.json"
    temporary = runs_dir / f".{execution.execution_id}.{uuid4().hex}.tmp"
    try:
        temporary.write_text(
            execution.model_dump_json(indent=2), encoding="utf-8"
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return execution


def artifacts_root_from_environment() -> Path:
    """Exige una ubicación externa explícita para no guardar modelos en Git."""
    configured = os.environ.get("ACTHO_ML_ARTIFACTS_DIR")
    if not configured:
        raise RuntimeError("Configura `ACTHO_ML_ARTIFACTS_DIR` fuera del repositorio.")
    return Path(configured).expanduser().resolve()
