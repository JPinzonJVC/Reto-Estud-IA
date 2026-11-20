"""Cargador transaccional e idempotente (UPSERT masivo) hacia PostgreSQL."""

from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import Table, inspect, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Connection, Engine

from app.database import Base, get_engine
from app.modules.eda import models as _models  # noqa: F401

ORDEN_CARGA_TABLAS: tuple[tuple[str, str], ...] = (
    ("silver", "dim_kams"),
    ("silver", "dim_empresas"),
    ("silver", "dim_empresas_scd2"),
    ("silver", "dim_personas"),
    ("silver", "dim_eventos"),
    ("silver", "fact_asistencias"),
    ("silver", "fact_encuestas_satisfaccion"),
    ("silver", "fact_movimientos_crm"),
    ("gold", "agg_participacion_empresa"),
    ("gold", "agg_satisfaccion_encuestas"),
    ("gold", "agg_retencion_empresa"),
    ("audit", "audit_hashes_fuentes_bronze"),
    ("audit", "audit_registros_duplicados"),
    ("audit", "audit_registros_rechazados"),
    ("audit", "audit_calidad_datos"),
    ("audit", "audit_reconciliacion_origen_destino"),
    ("audit", "audit_cargas"),
    ("audit", "audit_ejecuciones_etl"),
)

MAPA_NOMBRE_TABLA_SQL: dict[str, str] = {
    "dim_kams": "silver_dim_kams",
    "dim_empresas": "silver_dim_empresas",
    "dim_empresas_scd2": "silver_dim_empresas_scd2",
    "dim_personas": "silver_dim_personas",
    "dim_eventos": "silver_dim_eventos",
    "fact_asistencias": "silver_fact_asistencias",
    "fact_encuestas_satisfaccion": "silver_fact_encuestas_satisfaccion",
    "fact_movimientos_crm": "silver_fact_movimientos_crm",
    "agg_participacion_empresa": "gold_agg_participacion_empresa",
    "agg_satisfaccion_encuestas": "gold_agg_satisfaccion_encuestas",
    "agg_retencion_empresa": "gold_agg_retencion_empresa",
    "audit_hashes_fuentes_bronze": "audit_hashes_fuentes_bronze",
    "audit_registros_duplicados": "audit_registros_duplicados",
    "audit_registros_rechazados": "audit_registros_rechazados",
    "audit_calidad_datos": "audit_calidad_datos",
    "audit_reconciliacion_origen_destino": "audit_reconciliacion_origen_destino",
    "audit_cargas": "audit_cargas",
    "audit_ejecuciones_etl": "audit_ejecuciones_etl",
}


def inicializar_esquema_medallion(engine: Engine | None = None) -> None:
    """Crea todas las tablas Medallion en la base de datos si no existen.

    Args:
        engine: Instancia opcional de Engine. Si es None, usa get_engine().

    """
    target_engine = engine or get_engine()
    Base.metadata.create_all(bind=target_engine)


def _sanear_valor_sql(valor: Any) -> Any:
    """Convierte valores de Pandas/NumPy (NaN, pd.NA, int64) a tipos nativos Python.

    Args:
        valor: Valor de una celda de DataFrame.

    Returns:
        Valor nativo de Python o None si es nulo.

    """
    if valor is None or valor is pd.NA:
        return None
    if isinstance(valor, float) and np.isnan(valor):
        return None
    if pd.isna(valor):
        return None
    if isinstance(valor, np.generic):
        return valor.item()
    return valor


def _preparar_registros_tabla(df: pd.DataFrame, table: Table) -> list[dict[str, Any]]:
    """Prepara una lista de diccionarios compatibles con las columnas de la tabla SQL.

    Args:
        df: DataFrame con los datos a persistir.
        table: Objeto Table de SQLAlchemy.

    Returns:
        Lista de registros saneados para inserción masiva.

    """
    if df.empty:
        return []
    cols_validas = [c.name for c in table.columns if c.name in df.columns]
    df_sub = df[cols_validas].copy()
    registros: list[dict[str, Any]] = []
    for raw_row in df_sub.to_dict(orient="records"):
        registros.append({str(k): _sanear_valor_sql(v) for k, v in raw_row.items()})
    return registros


def _ejecutar_upsert_lote(
    conn: Connection,
    table: Table,
    lote: list[dict[str, Any]],
    dialect_name: str,
) -> None:
    """Ejecuta un UPSERT masivo por lote utilizando ON CONFLICT DO UPDATE.

    Args:
        conn: Conexión transaccional activa de SQLAlchemy.
        table: Tabla SQLAlchemy destino.
        lote: Lista de diccionarios a insertar o actualizar.
        dialect_name: Nombre del dialecto SQL ('postgresql' o 'sqlite').

    """
    if not lote:
        return
    pk_cols = [c.name for c in table.primary_key.columns]
    update_cols = [c for c in lote[0].keys() if c not in pk_cols]

    if dialect_name == "postgresql":
        stmt_pg = pg_insert(table).values(lote)
        if update_cols:
            stmt_pg = stmt_pg.on_conflict_do_update(
                index_elements=pk_cols,
                set_={col: getattr(stmt_pg.excluded, col) for col in update_cols},
            )
        else:
            stmt_pg = stmt_pg.on_conflict_do_nothing(index_elements=pk_cols)
        conn.execute(stmt_pg)
        return

    if dialect_name == "sqlite":
        stmt_sq = sqlite_insert(table).values(lote)
        if update_cols:
            stmt_sq = stmt_sq.on_conflict_do_update(
                index_elements=pk_cols,
                set_={col: getattr(stmt_sq.excluded, col) for col in update_cols},
            )
        else:
            stmt_sq = stmt_sq.on_conflict_do_nothing(index_elements=pk_cols)
        conn.execute(stmt_sq)
        return

    conn.execute(table.insert(), lote)


def cargar_tablas_en_postgres(
    tablas_por_capa: dict[str, dict[str, pd.DataFrame]],
    engine: Engine | None = None,
    tamano_lote: int = 500,
) -> dict[str, int]:
    """Persiste de forma transaccional e idempotente las capas Silver, Gold y Audit.

    Args:
        tablas_por_capa: Diccionario con DataFrames por capa ('silver', 'gold', 'audit').
        engine: Motor SQLAlchemy opcional (usa get_engine() por defecto).
        tamano_lote: Cantidad de registros por lote en inserciones masivas.

    Returns:
        Diccionario con la cantidad de registros procesados por tabla SQL.

    Raises:
        RuntimeError: Si ocurre un error de integridad o base de datos (hace rollback).

    """
    target_engine = engine or get_engine()
    inicializar_esquema_medallion(target_engine)
    dialect_name = target_engine.dialect.name
    conteos: dict[str, int] = {}

    try:
        with target_engine.begin() as conn:
            if dialect_name == "sqlite":
                conn.execute(text("PRAGMA foreign_keys = ON"))

            for capa, nombre_logico in ORDEN_CARGA_TABLAS:
                df = tablas_por_capa.get(capa, {}).get(nombre_logico)
                if df is None:
                    continue
                sql_table_name = MAPA_NOMBRE_TABLA_SQL[nombre_logico]
                table = Base.metadata.tables[sql_table_name]
                registros = _preparar_registros_tabla(df, table)

                for inicio in range(0, len(registros), tamano_lote):
                    fin = inicio + tamano_lote
                    lote = registros[inicio:fin]
                    _ejecutar_upsert_lote(conn, table, lote, dialect_name)
                conteos[sql_table_name] = len(registros)
    except Exception as exc:
        raise RuntimeError(
            f"Error al persistir capas Medallion en PostgreSQL (transacción "
            f"revertida con rollback): {exc}"
        ) from exc

    return conteos


def listar_tablas_medallion_db(engine: Engine | None = None) -> list[str]:
    """Lista las tablas del modelo Medallion existentes en la base de datos.

    Args:
        engine: Motor SQLAlchemy opcional.

    Returns:
        Lista ordenada de nombres de tablas presentes en el motor.

    """
    target_engine = engine or get_engine()
    inspector = inspect(target_engine)
    todas = set(inspector.get_table_names())
    esperadas = set(MAPA_NOMBRE_TABLA_SQL.values())
    return sorted(todas.intersection(esperadas))
