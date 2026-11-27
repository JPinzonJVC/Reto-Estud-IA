"""Pruebas de contratos de la persistencia Gold de ML."""

# pylint: disable=no-member

from datetime import date
from importlib import import_module
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.modules.eda.ml.fidelity.train import train_fidelity_model
from app.modules.eda.ml.persistence import generate_descriptive_results
from app.modules.eda.models.gold_dim_empresa_360 import GoldDimEmpresa360
from app.modules.eda.models.gold_hechos_y_marts import GoldFactAsistenciasBi
from app.modules.machine_learning.router import _approved_model_count
from tests.test_ml_fidelity import _fidelity_frame


def test_ml_result_table_has_idempotency_and_execution_trace() -> None:
    """La tabla incluye clave de idempotencia y trazabilidad por ejecución."""
    # pylint: disable=import-outside-toplevel
    from app.modules.eda.models.gold_ml_resultado import GoldMlResultado

    table = GoldMlResultado.__table__
    constraint = next(
        item for item in table.constraints if item.name and item.name.startswith("uq_")
    )
    assert [column.name for column in constraint.columns] == [
        "caso_uso",
        "id_empresa",
        "version_modelo",
        "fecha_corte",
    ]
    assert "id_ejecucion" in table.columns


def test_ml_migration_emits_postgresql_ddl() -> None:
    """La revisión nueva compila a DDL PostgreSQL sin ejecutar una base real."""
    alembic_migration = pytest.importorskip("alembic.migration")
    alembic_operations = pytest.importorskip("alembic.operations")
    output = StringIO()
    context = alembic_migration.MigrationContext.configure(
        dialect_name="postgresql",
        opts={"as_sql": True, "output_buffer": output},
    )
    migration = import_module("migrations.versions.rev_0005_gold_ml_resultados")
    with alembic_operations.Operations.context(context):
        migration.upgrade()
    ddl = output.getvalue()
    assert "CREATE TABLE gold_ml_resultados_empresa" in ddl
    assert "id_ejecucion VARCHAR(36) NOT NULL" in ddl
    assert "uq_gold_ml_resultado_caso_empresa_version_corte" in ddl


def test_postgresql_upsert_target_is_unique_per_case_company_version_cutoff() -> None:
    """La tabla permite compilar el upsert idempotente sobre su constraint."""
    # pylint: disable=import-outside-toplevel
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.dialects.postgresql import insert

    from app.modules.eda.models.gold_ml_resultado import GoldMlResultado

    statement = insert(GoldMlResultado).values(
        caso_uso="fidelidad_rfm_s",
        id_empresa="empresa-x",
        id_ejecucion="ejecucion-x",
        version_modelo="v1",
        fecha_corte="2026-11-27",
        estado_evaluacion="EXPERIMENTAL",
        metodo="KMeans",
        justificacion={},
        metricas={},
    )
    compiled = statement.on_conflict_do_update(
        constraint="uq_gold_ml_resultado_caso_empresa_version_corte",
        set_={"estado_evaluacion": statement.excluded.estado_evaluacion},
    ).compile(dialect=postgresql.dialect())
    assert "ON CONFLICT ON CONSTRAINT" in str(compiled)


def test_generate_descriptive_results_exports_and_reuses_fidelity_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que la primera corrida exporte el .joblib y la segunda lo reutilice."""
    # pylint: disable=import-outside-toplevel
    from app.modules.eda.models.gold_ml_resultado import GoldMlResultado

    artifacts_dir = tmp_path / "ml_artifacts"
    monkeypatch.setenv("ACTHO_ML_ARTIFACTS_DIR", str(artifacts_dir))

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            GoldDimEmpresa360.__table__,
            GoldFactAsistenciasBi.__table__,
            GoldMlResultado.__table__,
        ],
    )

    with (
        patch(
            "app.modules.eda.ml.persistence.load_fidelity_dataset",
            return_value=_fidelity_frame(rows=25),
        ),
        patch(
            "app.modules.eda.ml.persistence.train_fidelity_model",
            wraps=train_fidelity_model,
        ) as spy_train,
        Session(bind=engine) as session,
    ):
        first = generate_descriptive_results(
            session, cutoff=date(2026, 11, 27), artifacts_root=artifacts_dir
        )
        assert first["fidelidad"] == 25
        assert spy_train.call_count == 1
        assert _approved_model_count() == 1

        first_row = session.query(GoldMlResultado).first()
        assert first_row is not None
        assert first_row.metricas["artifact_reused"] is False

        second = generate_descriptive_results(
            session, cutoff=date(2026, 12, 4), artifacts_root=artifacts_dir
        )
        assert second["fidelidad"] == 25
        assert spy_train.call_count == 1

        second_row = (
            session.query(GoldMlResultado)
            .filter(GoldMlResultado.fecha_corte == "2026-12-04")
            .first()
        )
        assert second_row is not None
        assert second_row.metricas["artifact_reused"] is True
