"""Migración histórica 0002 autocontenida (previa a la refactorización DWH 0003)."""

# pylint: disable=invalid-name,import-outside-toplevel

from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine

from app.database import get_engine

revision: str = "0002_gold_actho_entregables"
down_revision: str | None = "0001_medallion_actho360"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def _resolver_bind(bind: Engine | Connection | None = None) -> Any:
    """Obtiene el motor o conexión activa desde Alembic o desde app.database."""
    if bind is not None:
        return bind
    try:
        from alembic import op  # type: ignore[import-not-found]

        return op.get_bind()
    except Exception:
        return get_engine()


def upgrade(bind: Engine | Connection | None = None) -> None:
    """Aplica ajustes intermedios 0002 si existen las tablas previas a 0003."""
    target = _resolver_bind(bind)
    inspector = sa.inspect(target)
    tablas = set(inspector.get_table_names())
    if "gold_agg_satisfaccion_encuestas" not in tablas:
        return

    cols = {
        c["name"] for c in inspector.get_columns("gold_agg_satisfaccion_encuestas")
    }
    with target.begin() as conn:
        if "tipo_encuesta" not in cols:
            conn.execute(
                sa.text(
                    "ALTER TABLE gold_agg_satisfaccion_encuestas "
                    "ADD COLUMN tipo_encuesta VARCHAR(64) DEFAULT 'POST_EVENTO'"
                )
            )
        if "temarios_sugeridos_resumen" not in cols:
            conn.execute(
                sa.text(
                    "ALTER TABLE gold_agg_satisfaccion_encuestas "
                    "ADD COLUMN temarios_sugeridos_resumen TEXT"
                )
            )


def downgrade(bind: Engine | Connection | None = None) -> None:
    """Revierte las tablas intermedias 0002 si están presentes."""
    target = _resolver_bind(bind)
    with target.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS gold_agg_segmentos_comunicaciones"))
        conn.execute(sa.text("DROP TABLE IF EXISTS gold_agg_participacion_eventos"))
