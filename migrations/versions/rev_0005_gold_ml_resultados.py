"""Resultados experimentales/auditables para los casos ML ACTHO."""

# pylint: disable=invalid-name

import sqlalchemy as sa
from alembic import op

revision: str = "0005_gold_ml_resultados"
down_revision: str | None = "0004_dwh_silver_3nf_gold_star"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Crea tabla versionada de resultados por empresa."""
    op.create_table(
        "gold_ml_resultados_empresa",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("caso_uso", sa.String(length=40), nullable=False),
        sa.Column("id_empresa", sa.String(length=64), nullable=False),
        sa.Column("id_ejecucion", sa.String(length=36), nullable=False),
        sa.Column("version_modelo", sa.String(length=64), nullable=False),
        sa.Column("fecha_corte", sa.String(length=32), nullable=False),
        sa.Column("estado_evaluacion", sa.String(length=32), nullable=False),
        sa.Column("metodo", sa.String(length=128), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("segmento", sa.String(length=128), nullable=True),
        sa.Column("soporte", sa.Integer(), nullable=True),
        sa.Column("justificacion", sa.JSON(), nullable=False),
        sa.Column("metricas", sa.JSON(), nullable=False),
        sa.Column("hash_dataset", sa.String(length=64), nullable=True),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "caso_uso", "id_empresa", "version_modelo", "fecha_corte",
            name="uq_gold_ml_resultado_caso_empresa_version_corte",
        ),
    )
    op.create_index(
        "ix_gold_ml_resultados_empresa", "gold_ml_resultados_empresa", ["id_empresa"]
    )
    op.create_index(
        "ix_gold_ml_resultados_caso_estado", "gold_ml_resultados_empresa",
        ["caso_uso", "estado_evaluacion"],
    )


def downgrade() -> None:
    """Elimina tabla y sus índices."""
    op.drop_index(
        "ix_gold_ml_resultados_caso_estado",
        table_name="gold_ml_resultados_empresa",
    )
    op.drop_index(
        "ix_gold_ml_resultados_empresa", table_name="gold_ml_resultados_empresa"
    )
    op.drop_table("gold_ml_resultados_empresa")
