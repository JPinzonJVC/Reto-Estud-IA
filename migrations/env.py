"""Entorno de configuración de migraciones Alembic para ACTHO 360."""

from typing import Any

from sqlalchemy import engine_from_config, pool

from app.database import Base, get_database_url
from app.modules.eda import models as _models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline(context_obj: Any) -> None:
    """Ejecuta las migraciones en modo offline utilizando la URL centralizada.

    Args:
        context_obj: Contexto de ejecución de Alembic.

    """
    url = get_database_url()
    context_obj.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context_obj.begin_transaction():
        context_obj.run_migrations()


def run_migrations_online(context_obj: Any) -> None:
    """Ejecuta las migraciones en modo online conectando al motor SQLAlchemy.

    Args:
        context_obj: Contexto de ejecución de Alembic.

    """
    cfg_section = {"sqlalchemy.url": get_database_url()}
    connectable = engine_from_config(
        cfg_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context_obj.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context_obj.begin_transaction():
            context_obj.run_migrations()
