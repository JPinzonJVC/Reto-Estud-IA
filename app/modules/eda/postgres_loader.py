"""Cargador transaccional e idempotente (UPSERT masivo) para las 25 tablas DWH."""

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
    ("silver", "dim_pais"),
    ("silver", "dim_departamento"),
    ("silver", "dim_ciudad"),
    ("silver", "dim_kams"),
    ("silver", "dim_empresas"),
    ("silver", "dim_catalogo_membresia"),
    ("silver", "membresias"),
    ("silver", "dim_personas"),
    ("silver", "bridge_persona_empresa"),
    ("silver", "dim_eventos"),
    ("silver", "fact_asistencias"),
    ("silver", "fact_encuestas_satisfaccion"),
    ("silver", "fact_movimientos_crm"),
    ("gold", "dim_empresa_360"),
    ("gold", "dim_evento_kpis"),
    ("gold", "fact_asistencias_bi"),
    ("gold", "fact_encuestas_bi"),
    ("gold", "fact_evolucion_membresias_mes"),
    ("gold", "mart_segmentos_comunicaciones"),
    ("audit", "audit_hashes_fuentes_bronze"),
    ("audit", "audit_registros_rechazados"),
    ("audit", "audit_calidad_datos"),
    ("audit", "audit_reconciliacion_origen_destino"),
    ("audit", "audit_cargas"),
    ("audit", "audit_ejecuciones_etl"),
)

MAPA_NOMBRE_TABLA_SQL: dict[str, str] = {
    "dim_pais": "silver_dim_pais",
    "dim_departamento": "silver_dim_departamento",
    "dim_ciudad": "silver_dim_ciudad",
    "dim_kams": "silver_dim_kams",
    "dim_empresas": "silver_dim_empresas",
    "dim_catalogo_membresia": "silver_dim_catalogo_membresia",
    "membresias": "silver_membresias",
    "dim_personas": "silver_dim_personas",
    "bridge_persona_empresa": "silver_bridge_persona_empresa",
    "dim_eventos": "silver_dim_eventos",
    "fact_asistencias": "silver_fact_asistencias",
    "fact_encuestas_satisfaccion": "silver_fact_encuestas_satisfaccion",
    "fact_movimientos_crm": "silver_fact_movimientos_crm",
    "dim_empresa_360": "gold_dim_empresa_360",
    "dim_evento_kpis": "gold_dim_evento_kpis",
    "fact_asistencias_bi": "gold_fact_asistencias_bi",
    "fact_encuestas_bi": "gold_fact_encuestas_bi",
    "fact_evolucion_membresias_mes": "gold_fact_evolucion_membresias_mes",
    "mart_segmentos_comunicaciones": "gold_mart_segmentos_comunicaciones",
    "audit_hashes_fuentes_bronze": "audit_hashes_fuentes_bronze",
    "audit_registros_rechazados": "audit_registros_rechazados",
    "audit_calidad_datos": "audit_calidad_datos",
    "audit_reconciliacion_origen_destino": "audit_reconciliacion_origen_destino",
    "audit_cargas": "audit_cargas",
    "audit_ejecuciones_etl": "audit_ejecuciones_etl",
}

TABLAS_OBSOLETAS_LEGADO: tuple[str, ...] = (
    "gold_agg_segmentos_comunicaciones",
    "gold_agg_participacion_eventos",
    "gold_agg_satisfaccion_encuestas",
    "gold_agg_retencion_empresa",
    "gold_agg_participacion_empresa",
    "silver_dim_empresas_scd2",
    "audit_registros_duplicados",
)

TABLAS_REEMPLAZADAS_V3: tuple[str, ...] = (
    *TABLAS_OBSOLETAS_LEGADO,
    "silver_fact_movimientos_crm",
    "silver_fact_encuestas_satisfaccion",
    "silver_fact_asistencias",
    "silver_dim_eventos",
    "silver_dim_personas",
    "silver_dim_empresas",
    "silver_dim_kams",
)


def _requiere_reemplazo_esquema_v3(inspector: Any, existentes: set[str]) -> bool:
    """Detecta si la base de datos aún conserva columnas NOT NULL del modelo legado."""
    huellas_legado = (
        ("silver_dim_kams", "es_kam_asignado"),
        ("silver_dim_empresas", "es_membresia_activa"),
        ("silver_dim_eventos", "fecha_evento"),
        ("silver_fact_asistencias", "es_afiliado"),
    )
    for tabla, col_antigua in huellas_legado:
        if tabla in existentes:
            cols = {c["name"] for c in inspector.get_columns(tabla)}
            if col_antigua in cols:
                return True
    return False


def inicializar_esquema_medallion(engine: Engine | None = None) -> None:
    """Sincroniza el esquema de las 25 tablas DWH y purga tablas obsoletas.

    Args:
        engine: Instancia opcional de Engine. Si es None, usa get_engine().

    """
    target_engine = engine or get_engine()
    inspector = inspect(target_engine)
    tablas_existentes = set(inspector.get_table_names())
    sufijo = " CASCADE" if target_engine.dialect.name == "postgresql" else ""
    a_eliminar = (
        TABLAS_REEMPLAZADAS_V3
        if _requiere_reemplazo_esquema_v3(inspector, tablas_existentes)
        else TABLAS_OBSOLETAS_LEGADO
    )

    with target_engine.begin() as conn:
        for obsoleta in a_eliminar:
            if obsoleta in tablas_existentes:
                conn.execute(text(f"DROP TABLE IF EXISTS {obsoleta}{sufijo}"))

    Base.metadata.create_all(bind=target_engine)
    inspector = inspect(target_engine)
    tablas_existentes = set(inspector.get_table_names())

    with target_engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in tablas_existentes:
                continue
            cols_db = {c["name"] for c in inspector.get_columns(table_name)}
            for col in table.columns:
                if col.name not in cols_db:
                    col_type = col.type.compile(dialect=target_engine.dialect)
                    conn.execute(
                        text(
                            f"ALTER TABLE {table_name} "
                            f"ADD COLUMN {col.name} {col_type}"
                        )
                    )


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
