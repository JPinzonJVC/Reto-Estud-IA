"""Almacén híbrido PostgreSQL/Redis/Parquet para consultas del Dashboard sobre el DWH."""

import logging
import os
import pickle  # nosec B403
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.eda.models import (
    AuditEjecucionEtl,
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

try:
    import redis as _redis_pkg  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    _redis_pkg = None

logger = logging.getLogger(__name__)

ROOT_INPUT = Path(__file__).resolve().parents[3] / "input"
GOLD_DIR = ROOT_INPUT / "gold"
SILVER_DIR = ROOT_INPUT / "silver"

_CACHE_PARQUET: dict[str, tuple[int, pd.DataFrame]] = {}
_CACHE_LOCK = threading.Lock()
_REDIS_SNAPSHOT_KEY = "actho360:dwh:snapshot:v1"
_REDIS_VERSION_KEY = "actho360:dwh:version:v1"


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


@dataclass
class _CacheEntradaDWH:
    """Estado interno de la caché L1 en memoria para una base de datos."""

    firma_version: str
    """Marca de versión calculada sobre audit_ejecuciones_etl y conteos base."""

    expira_monotonic: float
    """Instante monotónico en que se debe revalidar la versión contra la DB."""

    snapshot: SnapshotDWH
    """Snapshot inmutable de las 10 tablas DWH."""


_CACHE_DB_L1: dict[str, _CacheEntradaDWH] = {}
_REDIS_CLIENT: Any = None
_REDIS_INIT_ATTEMPTED: bool = False


def _ttl_cache_segundos() -> float:
    """Retorna el TTL en segundos para revalidar cambios en la base de datos."""
    raw = os.getenv("DWH_CACHE_TTL_SECONDS", "30")
    try:
        return max(float(raw), 0.0)
    except ValueError:
        return 30.0


def _obtener_cliente_redis() -> Any:
    """Obtiene o inicializa perezosamente el cliente Redis L2 si está configurado."""
    global _REDIS_CLIENT, _REDIS_INIT_ATTEMPTED  # pylint: disable=global-statement
    if _REDIS_INIT_ATTEMPTED:
        return _REDIS_CLIENT
    _REDIS_INIT_ATTEMPTED = True
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url or _redis_pkg is None:
        return None
    try:
        client = _redis_pkg.Redis.from_url(
            redis_url,
            socket_connect_timeout=1.0,
            socket_timeout=1.5,
        )
        client.ping()
        _REDIS_CLIENT = client
    except Exception as exc:
        logger.debug("Redis no disponible, usando caché L1 en memoria: %s", exc)
        _REDIS_CLIENT = None
    return _REDIS_CLIENT


def invalidar_cache_dwh() -> None:
    """Invalida inmediatamente la caché L1 en memoria y L2 en Redis tras cargas ETL."""
    with _CACHE_LOCK:
        _CACHE_DB_L1.clear()
        _CACHE_PARQUET.clear()
    client = _obtener_cliente_redis()
    if client is not None:
        try:
            client.delete(_REDIS_SNAPSHOT_KEY, _REDIS_VERSION_KEY)
        except Exception as exc:
            logger.debug("No se pudo limpiar claves DWH en Redis: %s", exc)


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
    """Lee una tabla SQL directamente con SQLAlchemy Core sin instanciar objetos ORM."""
    table = model_cls.__table__
    cols = [col.name for col in table.columns]
    result = session.execute(select(table))
    rows = [tuple(r) for r in result.fetchall()]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame.from_records(rows, columns=cols)


def _identificador_bind(session: Session) -> str:
    """Obtiene una clave única por motor/URL de base de datos para aislar sesiones."""
    try:
        bind = session.get_bind()
        url = getattr(bind, "url", None)
        return str(url) if url is not None else str(id(bind))
    except Exception:
        return "default_bind"


def _consultar_firma_version_db(session: Session) -> str | None:
    """Calcula una firma ligera de versión del DWH consultando conteos y última corrida.

    Args:
        session: Sesión SQLAlchemy activa.

    Returns:
        Cadena con la firma de versión si hay datos en Gold, o None si está vacía.

    """
    try:
        total_emp = int(session.query(GoldDimEmpresa360.id_empresa).count())
        if total_emp == 0:
            return None
    except Exception:
        return None

    ultimo_id = ""
    ultima_fin = ""
    try:
        audit_tbl = AuditEjecucionEtl.__table__
        row = session.execute(
            select(audit_tbl.c.id_ejecucion, audit_tbl.c.fecha_finalizacion)
            .order_by(audit_tbl.c.fecha_finalizacion.desc())
            .limit(1)
        ).first()
        if row is not None:
            ultimo_id = str(row[0] or "")
            ultima_fin = str(row[1] or "")
    except Exception:
        ultimo_id = "no_audit"

    return f"emp={total_emp}|run={ultimo_id}|fin={ultima_fin}"


def _cargar_snapshot_desde_db(session: Session) -> SnapshotDWH:
    """Construye el SnapshotDWH completo leyendo las 10 tablas desde la base de datos."""
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


def _intentar_leer_redis(firma_db: str) -> SnapshotDWH | None:
    """Intenta recuperar el SnapshotDWH desde Redis L2 si la firma de versión coincide."""
    client = _obtener_cliente_redis()
    if client is None:
        return None
    try:
        ver_raw = client.get(_REDIS_VERSION_KEY)
        if ver_raw is None or ver_raw.decode("utf-8") != firma_db:
            return None
        payload = client.get(_REDIS_SNAPSHOT_KEY)
        if payload is None:
            return None
        snap = pickle.loads(payload)  # nosec B301
        return snap if isinstance(snap, SnapshotDWH) else None
    except Exception as exc:
        logger.debug("Fallo leyendo snapshot DWH desde Redis: %s", exc)
        return None


def _guardar_en_redis(firma_db: str, snap: SnapshotDWH, ttl: float) -> None:
    """Almacena el SnapshotDWH serializado en Redis L2 con TTL extendido."""
    client = _obtener_cliente_redis()
    if client is None:
        return
    try:
        redis_ttl = max(int(ttl * 10), 300)
        payload = pickle.dumps(snap, protocol=pickle.HIGHEST_PROTOCOL)
        pipe = client.pipeline()
        pipe.setex(_REDIS_VERSION_KEY, redis_ttl, firma_db.encode("utf-8"))
        pipe.setex(_REDIS_SNAPSHOT_KEY, redis_ttl, payload)
        pipe.execute()
    except Exception as exc:
        logger.debug("Fallo guardando snapshot DWH en Redis: %s", exc)


def cargar_snapshot_dwh(session: Session | None = None) -> SnapshotDWH:
    """Carga el conjunto de tablas Gold/Silver usando caché L1/Redis o respaldo Parquet.

    Evita recargar las 10 tablas en cada una de las 15 peticiones simultáneas del
    Dashboard: mantiene el snapshot en memoria (y opcionalmente en Redis) y verifica
    periódicamente si hubo cambios nuevos en la base de datos.

    Args:
        session: Sesión SQLAlchemy opcional inyectada por FastAPI.

    Returns:
        Instancia SnapshotDWH lista para agregaciones vectorizadas.

    """
    if session is not None:
        bind_key = _identificador_bind(session)
        ttl = _ttl_cache_segundos()
        ahora = time.monotonic()

        with _CACHE_LOCK:
            entrada = _CACHE_DB_L1.get(bind_key)
            if entrada is not None and ahora < entrada.expira_monotonic:
                return entrada.snapshot

        firma_actual = _consultar_firma_version_db(session)
        if firma_actual is not None:
            with _CACHE_LOCK:
                entrada = _CACHE_DB_L1.get(bind_key)
                if entrada is not None and entrada.firma_version == firma_actual:
                    entrada.expira_monotonic = ahora + ttl
                    return entrada.snapshot

            snap_redis = _intentar_leer_redis(firma_actual)
            if snap_redis is not None:
                with _CACHE_LOCK:
                    _CACHE_DB_L1[bind_key] = _CacheEntradaDWH(
                        firma_version=firma_actual,
                        expira_monotonic=ahora + ttl,
                        snapshot=snap_redis,
                    )
                return snap_redis

            snap_db = _cargar_snapshot_desde_db(session)
            with _CACHE_LOCK:
                _CACHE_DB_L1[bind_key] = _CacheEntradaDWH(
                    firma_version=firma_actual,
                    expira_monotonic=ahora + ttl,
                    snapshot=snap_db,
                )
            _guardar_en_redis(firma_actual, snap_db, ttl)
            return snap_db

    return SnapshotDWH(
        fuente="parquet",
        dim_empresa_360=_leer_parquet_cache(GOLD_DIR / "dim_empresa_360.parquet"),
        dim_evento_kpis=_leer_parquet_cache(GOLD_DIR / "dim_evento_kpis.parquet"),
        fact_asistencias_bi=_leer_parquet_cache(GOLD_DIR / "fact_asistencias_bi.parquet"),
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
