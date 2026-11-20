"""Migración 0002 para tablas Gold de eventos, segmentos y encuesta 90 días."""

# pylint: disable=invalid-name,import-outside-toplevel

import sqlalchemy as sa
from alembic import op

from app.modules.eda.models.gold_agg_participacion_eventos import (
    GoldAggParticipacionEventos,
)
from app.modules.eda.models.gold_agg_segmentos_comunicaciones import (
    GoldAggSegmentosComunicaciones,
)

revision: str = "0002_gold_actho_entregables"
down_revision: str | None = "0001_medallion_actho360"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Crea las nuevas tablas Gold y amplía gold_agg_satisfaccion_encuestas."""
    bind = op.get_bind()
    GoldAggParticipacionEventos.__table__.create(bind=bind, checkfirst=True)
    GoldAggSegmentosComunicaciones.__table__.create(bind=bind, checkfirst=True)

    inspector = sa.inspect(bind)
    cols = {
        c["name"] for c in inspector.get_columns("gold_agg_satisfaccion_encuestas")
    }
    if "tipo_encuesta" not in cols:
        op.add_column(
            "gold_agg_satisfaccion_encuestas",
            sa.Column(
                "tipo_encuesta",
                sa.String(length=64),
                nullable=False,
                server_default="POST_EVENTO",
            ),
        )
    if "temarios_sugeridos_resumen" not in cols:
        op.add_column(
            "gold_agg_satisfaccion_encuestas",
            sa.Column("temarios_sugeridos_resumen", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    """Revierte las tablas y columnas agregadas en la migración 0002."""
    bind = op.get_bind()
    GoldAggSegmentosComunicaciones.__table__.drop(bind=bind, checkfirst=True)
    GoldAggParticipacionEventos.__table__.drop(bind=bind, checkfirst=True)

    inspector = sa.inspect(bind)
    cols = {
        c["name"] for c in inspector.get_columns("gold_agg_satisfaccion_encuestas")
    }
    if "temarios_sugeridos_resumen" in cols:
        op.drop_column("gold_agg_satisfaccion_encuestas", "temarios_sugeridos_resumen")
    if "tipo_encuesta" in cols:
        op.drop_column("gold_agg_satisfaccion_encuestas", "tipo_encuesta")
