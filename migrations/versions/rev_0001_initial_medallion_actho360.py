"""Migración inicial 0001 del esquema Medallion (Silver, Gold y Audit) ACTHO 360."""

# pylint: disable=invalid-name,import-outside-toplevel

from typing import Any

from sqlalchemy.engine import Connection, Engine

from app.database import Base, get_engine
from app.modules.eda import models as _models  # noqa: F401

revision: str = "0001_medallion_actho360"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def _resolver_bind(bind: Engine | Connection | None = None) -> Any:
    """Obtiene el motor o conexión activa desde Alembic o desde app.database.

    Args:
        bind: Motor o conexión SQLAlchemy opcional.

    Returns:
        Conexión o motor SQLAlchemy para aplicar las operaciones DDL.

    """
    if bind is not None:
        return bind
    try:
        from alembic import op  # type: ignore[import-not-found]

        return op.get_bind()
    except Exception:
        return get_engine()


def upgrade(bind: Engine | Connection | None = None) -> None:
    """Aplica la migración creando las tablas de las capas Silver, Gold y Audit.

    Args:
        bind: Motor o conexión SQLAlchemy opcional.

    """
    target = _resolver_bind(bind)
    Base.metadata.create_all(bind=target)


def downgrade(bind: Engine | Connection | None = None) -> None:
    """Revierte la migración eliminando las tablas del modelo Medallion.

    Args:
        bind: Motor o conexión SQLAlchemy opcional.

    """
    target = _resolver_bind(bind)
    Base.metadata.drop_all(bind=target)
