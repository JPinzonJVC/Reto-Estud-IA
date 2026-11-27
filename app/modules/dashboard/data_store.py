"""Almacén híbrido PostgreSQL/Parquet para consultas del Dashboard sobre el DWH."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.modules.eda.models import (
    GoldDimEmpresa360,
    GoldDimEventoKpis,
    GoldFactAsistenciasBi,
    GoldFactEncuestasBi,
    GoldFactEvolucionMembresiasMes,
    GoldMartSegmentosComunicaciones,
    SilverDimEmpresa,
    SilverDimEvento,
    SilverDimKam,
    SilverFactMovimientoCrm,
)

ROOT_INPUT = Path(__file__).resolve().parents[3] / "input"
GOLD_DIR = ROOT_INPUT / "gold"
SILVER_DIR = ROOT_INPUT / "silver"

_CACHE_PARQUET: dict[str, tuple[int, pd.DataFrame]] = {}


@dataclass
class SnapshotDWH:  # pylint: disable=too-many-instance-attributes
    """Contenedor en memoria de las tablas Gold y Silver usadas por el tablero."""

    fuente: str
    """Origen efectivo de los datos ('postgresql' o 'parquet')."""

    dim_empresa_360: pd.DataFrame
    """Vista integral por empresa (Gold)."""

    dim_evento_kpis: pd.DataFrame
    """Indicadores consolidados por evento (Gold)."""

    fact_asistencias_bi: pd.DataFrame
    """Hechos de asistencias enriquecidos para BI (Gold)."""

    fact_encuestas_bi: pd.DataFrame
    """Hechos de encuestas con Likert 1-5, NPS 0-10 y NLP (Gold)."""

    fact_evolucion_mes: pd.DataFrame
    """Serie mensual de altas, renovaciones y retiros (Gold)."""

    mart_segmentos: pd.DataFrame
    """Los 8 segmentos accionables con Habeas Data (Gold)."""

    silver_empresas: pd.DataFrame
    """Maestro Silver 3NF de empresas (pilares y equidad femenina)."""

    silver_eventos: pd.DataFrame
    """Maestro Silver 3NF de eventos."""

    silver_kams: pd.DataFrame
    """Maestro Silver 3NF de ejecutivas KAM."""

    silver_movimientos: pd.DataFrame
    """Hechos comerciales de movimientos CRM (Silver)."""


def _leer_parquet_cache(ruta: Path) -> pd.DataFrame:
    """Lee un archivo Parquet cacheándolo por marca de modificación."""
    if not ruta.exists():
        return pd.DataFrame()
    key = str(ruta)
    mtime = ruta.stat().st_mtime_ns
    prev = _CACHE_PARQUET.get(key)
    if prev is not None and prev[0] == mtime:
        return prev[1].copy()
    df = pd.read_parquet(ruta)
    _CACHE_PARQUET[key] = (mtime, df)
    return df.copy()


def _modelo_a_df(session: Session, model_cls: Any) -> pd.DataFrame:
    """Convierte registros ORM de una tabla SQLAlchemy en un DataFrame tipado."""
    cols = [col.name for col in model_cls.__table__.columns]
    rows = session.query(model_cls).all()
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(
        [{col: getattr(obj, col) for col in cols} for obj in rows],
        columns=cols,
    )


def _sesion_tiene_dwh(session: Session | None) -> bool:
    """Verifica si la sesión SQLAlchemy está activa y contiene datos del DWH."""
    if session is None:
        return False
    try:
        return session.query(GoldDimEmpresa360.id_empresa).limit(1).count() > 0
    except Exception:
        return False


def cargar_snapshot_dwh(session: Session | None = None) -> SnapshotDWH:
    """Carga el conjunto de tablas Gold/Silver desde DB activa o respaldo Parquet.

    Args:
        session: Sesión SQLAlchemy opcional inyectada por FastAPI.

    Returns:
        Instancia SnapshotDWH lista para agregaciones vectorizadas.

    """
    if _sesion_tiene_dwh(session):
        assert session is not None
        return SnapshotDWH(
            fuente="postgresql",
            dim_empresa_360=_modelo_a_df(session, GoldDimEmpresa360),
            dim_evento_kpis=_modelo_a_df(session, GoldDimEventoKpis),
            fact_asistencias_bi=_modelo_a_df(session, GoldFactAsistenciasBi),
            fact_encuestas_bi=_modelo_a_df(session, GoldFactEncuestasBi),
            fact_evolucion_mes=_modelo_a_df(session, GoldFactEvolucionMembresiasMes),
            mart_segmentos=_modelo_a_df(session, GoldMartSegmentosComunicaciones),
            silver_empresas=_modelo_a_df(session, SilverDimEmpresa),
            silver_eventos=_modelo_a_df(session, SilverDimEvento),
            silver_kams=_modelo_a_df(session, SilverDimKam),
            silver_movimientos=_modelo_a_df(session, SilverFactMovimientoCrm),
        )

    return SnapshotDWH(
        fuente="parquet",
        dim_empresa_360=_leer_parquet_cache(GOLD_DIR / "dim_empresa_360.parquet"),
        dim_evento_kpis=_leer_parquet_cache(GOLD_DIR / "dim_evento_kpis.parquet"),
        fact_asistencias_bi=_leer_parquet_cache(
            GOLD_DIR / "fact_asistencias_bi.parquet"
        ),
        fact_encuestas_bi=_leer_parquet_cache(GOLD_DIR / "fact_encuestas_bi.parquet"),
        fact_evolucion_mes=_leer_parquet_cache(
            GOLD_DIR / "fact_evolucion_membresias_mes.parquet"
        ),
        mart_segmentos=_leer_parquet_cache(
            GOLD_DIR / "mart_segmentos_comunicaciones.parquet"
        ),
        silver_empresas=_leer_parquet_cache(SILVER_DIR / "dim_empresas.parquet"),
        silver_eventos=_leer_parquet_cache(SILVER_DIR / "dim_eventos.parquet"),
        silver_kams=_leer_parquet_cache(SILVER_DIR / "dim_kams.parquet"),
        silver_movimientos=_leer_parquet_cache(
            SILVER_DIR / "fact_movimientos_crm.parquet"
        ),
    )


def lista_distintos(df: pd.DataFrame, col: str) -> list[str]:
    """Extrae valores únicos ordenados no vacíos de una columna."""
    if df.empty or col not in df.columns:
        return []
    vals = {
        str(v).strip()
        for v in df[col].dropna()
        if str(v).strip() and str(v).strip() != "SIN_FECHA"
    }
    return sorted(vals)
