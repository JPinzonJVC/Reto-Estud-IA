"""Migración 0003 para la tabla audit_ingestion_watermarks."""

# pylint: disable=invalid-name

from alembic import op

from app.modules.eda.models.audit_ingestion_watermark import AuditIngestionWatermark

revision: str = "0003_ingestion_watermarks"
down_revision: str | None = "0002_gold_actho_entregables"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Crea la tabla audit_ingestion_watermarks si no existe.

    Args:
        None.

    Returns:
        None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: Si falla la creación de la tabla en la base de datos.

    """
    bind = op.get_bind()
    AuditIngestionWatermark.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    """Elimina la tabla audit_ingestion_watermarks.

    Args:
        None.

    Returns:
        None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: Si falla la eliminación de la tabla en la base de datos.

    """
    bind = op.get_bind()
    AuditIngestionWatermark.__table__.drop(bind=bind, checkfirst=True)
