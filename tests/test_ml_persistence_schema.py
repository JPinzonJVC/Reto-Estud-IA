"""Pruebas de contratos de la persistencia Gold de ML."""

from importlib import import_module
from io import StringIO

import pytest


def test_ml_result_table_has_idempotency_and_execution_trace() -> None:
    """La tabla incluye clave de idempotencia y trazabilidad por ejecución."""
    from app.modules.eda.models.gold_ml_resultado import GoldMlResultado

    table = GoldMlResultado.__table__
    constraint = next(
        item for item in table.constraints if item.name and item.name.startswith("uq_")
    )
    assert [column.name for column in constraint.columns] == [
        "caso_uso", "id_empresa", "version_modelo", "fecha_corte"
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
