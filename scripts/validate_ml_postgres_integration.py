"""Valida persistencia/idempotencia real de ML dentro de una transacción reversible."""

from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_engine
from app.modules.eda.ml.persistence import generate_descriptive_results
from app.modules.eda.models.gold_ml_resultado import GoldMlResultado
from migrations.versions import rev_0005_gold_ml_resultados


def main() -> None:
    """Ejecuta dos cortes iguales en un schema temporal y revierte todos los cambios."""
    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()
    schema = f"ml_validation_{uuid4().hex}"
    try:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.execute(text(f'SET search_path TO "{schema}", public'))
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            rev_0005_gold_ml_resultados.upgrade()
            rev_0005_gold_ml_resultados.downgrade()
            rev_0005_gold_ml_resultados.upgrade()
        with Session(
            bind=connection, join_transaction_mode="create_savepoint"
        ) as session:
            first = generate_descriptive_results(session)
            first_total = session.query(GoldMlResultado).count()
            second = generate_descriptive_results(session)
            second_total = session.query(GoldMlResultado).count()
            distinct_runs = session.query(GoldMlResultado.id_ejecucion).distinct().count()
        if first_total != second_total or distinct_runs != 1:
            raise AssertionError("Repetir el mismo corte duplicó filas Gold ML.")
        if not any(count for key, count in first.items() if key != "id_ejecucion"):
            raise AssertionError(
                "No se generaron resultados desde las fuentes PostgreSQL."
            )
        print(
            {
                "primera_ejecucion": first,
                "segunda_ejecucion": second,
                "filas_gold": second_total,
                "ejecuciones_en_corte": distinct_runs,
            }
        )
    finally:
        transaction.rollback()
        connection.close()
        engine.dispose()


if __name__ == "__main__":
    main()
