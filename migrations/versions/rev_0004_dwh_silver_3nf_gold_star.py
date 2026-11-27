"""Migración 0004: Data Warehouse Silver 3NF (13 tablas) y Gold Estrella (6 tablas)."""

# pylint: disable=invalid-name,import-outside-toplevel,no-member

from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine

from app.database import Base, get_engine
from app.modules.eda import models as _models  # noqa: F401

revision: str = "0004_dwh_silver_3nf_gold_star"
down_revision: str | None = "0003_ingestion_watermarks"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

TABLAS_REEMPLAZADAS_EN_0004: tuple[str, ...] = (
    "gold_agg_segmentos_comunicaciones",
    "gold_agg_participacion_eventos",
    "gold_agg_satisfaccion_encuestas",
    "gold_agg_retencion_empresa",
    "gold_agg_participacion_empresa",
    "silver_fact_movimientos_crm",
    "silver_fact_encuestas_satisfaccion",
    "silver_fact_asistencias",
    "silver_dim_empresas_scd2",
    "silver_dim_eventos",
    "silver_dim_personas",
    "silver_dim_empresas",
    "silver_dim_kams",
    "audit_registros_duplicados",
)

TABLAS_CREADAS_EN_0004: tuple[str, ...] = (
    "gold_mart_segmentos_comunicaciones",
    "gold_fact_evolucion_membresias_mes",
    "gold_fact_encuestas_bi",
    "gold_fact_asistencias_bi",
    "gold_dim_evento_kpis",
    "gold_dim_empresa_360",
    "silver_fact_movimientos_crm",
    "silver_fact_encuestas_satisfaccion",
    "silver_fact_asistencias",
    "silver_dim_eventos",
    "silver_bridge_persona_empresa",
    "silver_dim_personas",
    "silver_membresias",
    "silver_dim_catalogo_membresia",
    "silver_dim_empresas",
    "silver_dim_kams",
    "silver_dim_ciudad",
    "silver_dim_departamento",
    "silver_dim_pais",
)


def _resolver_bind(bind: Engine | Connection | None = None) -> Any:
    """Obtiene el motor o conexión activa desde Alembic o desde app.database.

    Args:
        bind: Motor o conexión SQLAlchemy opcional.

    Returns:
        Conexión o motor SQLAlchemy para ejecutar DDL.

    """
    if bind is not None:
        return bind
    try:
        from alembic import op  # type: ignore[import-not-found]

        return op.get_bind()
    except Exception:
        return get_engine()


def _ejecutar_drops(target: Any, nombres_tablas: tuple[str, ...]) -> None:
    """Elimina una secuencia ordenada de tablas manejando Engine o Connection.

    Args:
        target: Instancia Engine o Connection de SQLAlchemy.
        nombres_tablas: Tupla de nombres de tablas en orden inverso de FK.

    """
    sufijo = " CASCADE" if target.dialect.name == "postgresql" else ""
    if isinstance(target, Engine):
        with target.begin() as conn:
            for nombre in nombres_tablas:
                conn.execute(sa.text(f"DROP TABLE IF EXISTS {nombre}{sufijo}"))
    else:
        for nombre in nombres_tablas:
            target.execute(sa.text(f"DROP TABLE IF EXISTS {nombre}{sufijo}"))


def upgrade(bind: Engine | Connection | None = None) -> None:
    """Actualiza el esquema al modelo DWH v3 (Silver 3NF + Gold Estrella, sin dups).

    Args:
        bind: Motor o conexión SQLAlchemy opcional.

    """
    target = _resolver_bind(bind)
    _ejecutar_drops(target, TABLAS_REEMPLAZADAS_EN_0004)
    Base.metadata.create_all(bind=target)


def downgrade(bind: Engine | Connection | None = None) -> None:
    """Revierte las tablas Silver 3NF y Gold Estrella introducidas en 0004.

    Args:
        bind: Motor o conexión SQLAlchemy opcional.

    """
    target = _resolver_bind(bind)
    _ejecutar_drops(target, TABLAS_CREADAS_EN_0004)
