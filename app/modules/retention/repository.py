"""Repositorio de acceso a datos Gold para el módulo de retención."""

import logging
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.modules.eda.config import cargar_configuracion
from app.modules.eda.models import GoldAggRetencionEmpresa

logger = logging.getLogger(__name__)


class RetentionRepository:
    """Gestiona consultas de retención y riesgo sobre PostgreSQL o Gold Parquet."""

    def __init__(self, session: Session | None = None) -> None:
        """Inicializa el repositorio con una sesión SQLAlchemy opcional.

        Args:
            session: Sesión activa de SQLAlchemy o None para lectura local.

        """
        self.session = session

    def _leer_resumen_desde_db(self) -> dict[str, Any] | None:
        """Consulta el resumen de retención y semáforo desde PostgreSQL.

        Returns:
            Diccionario de indicadores de retención o None si la tabla está vacía.

        """
        if self.session is None:
            return None
        try:
            q_base = self.session.query(GoldAggRetencionEmpresa)
            total = int(q_base.count())
            if total == 0:
                return None
            activas = int(
                q_base.filter(
                    GoldAggRetencionEmpresa.es_membresia_activa.is_(True)
                ).count()
            )
            vencidas = int(
                q_base.filter(
                    GoldAggRetencionEmpresa.es_membresia_vencida.is_(True)
                ).count()
            )
            prox_90 = int(
                q_base.filter(
                    GoldAggRetencionEmpresa.es_proximo_vencimiento_90d.is_(True)
                ).count()
            )
            rojo = int(
                q_base.filter(
                    GoldAggRetencionEmpresa.semaforo_riesgo_renovacion
                    == "ROJO_RIESGO_ALTO"
                ).count()
            )
            amarillo = int(
                q_base.filter(
                    GoldAggRetencionEmpresa.semaforo_riesgo_renovacion
                    == "AMARILLO_RIESGO_MEDIO"
                ).count()
            )
            verde = int(
                q_base.filter(
                    GoldAggRetencionEmpresa.semaforo_riesgo_renovacion
                    == "VERDE_RIESGO_BAJO"
                ).count()
            )
            retiros = int(
                q_base.filter(
                    GoldAggRetencionEmpresa.es_retiro_definitivo_actual.is_(True)
                ).count()
            )
            return {
                "total_empresas": total,
                "membresias_activas": activas,
                "membresias_vencidas": vencidas,
                "proximos_vencimientos_90d": prox_90,
                "riesgo_rojo_alto": rojo,
                "riesgo_amarillo_medio": amarillo,
                "riesgo_verde_bajo": verde,
                "retiros_definitivos_actuales": retiros,
                "fuente_datos": "postgresql",
            }
        except Exception as exc:
            logger.debug("Fallback resumen retención a Parquet: %s", exc)
            return None

    def obtener_resumen_retencion(self) -> dict[str, Any]:
        """Obtiene el resumen de retención y semáforo heurístico desde la capa Gold.

        Returns:
            Diccionario con conteos de vigencias, vencimientos y niveles de riesgo.

        """
        desde_db = self._leer_resumen_desde_db()
        if desde_db is not None:
            return desde_db

        cfg = cargar_configuracion()
        ruta_ret = cfg.gold_dir / "agg_retencion_empresa.parquet"
        if ruta_ret.exists():
            df_ret = pd.read_parquet(ruta_ret)
            return {
                "total_empresas": int(len(df_ret)),
                "membresias_activas": int(
                    df_ret["es_membresia_activa"].astype(bool).sum()
                ),
                "membresias_vencidas": int(
                    df_ret["es_membresia_vencida"].astype(bool).sum()
                ),
                "proximos_vencimientos_90d": int(
                    df_ret["es_proximo_vencimiento_90d"].astype(bool).sum()
                ),
                "riesgo_rojo_alto": int(
                    (df_ret["semaforo_riesgo_renovacion"] == "ROJO_RIESGO_ALTO").sum()
                ),
                "riesgo_amarillo_medio": int(
                    (
                        df_ret["semaforo_riesgo_renovacion"] == "AMARILLO_RIESGO_MEDIO"
                    ).sum()
                ),
                "riesgo_verde_bajo": int(
                    (df_ret["semaforo_riesgo_renovacion"] == "VERDE_RIESGO_BAJO").sum()
                ),
                "retiros_definitivos_actuales": int(
                    df_ret["es_retiro_definitivo_actual"].astype(bool).sum()
                ),
                "fuente_datos": "gold_parquet",
            }

        return {
            "total_empresas": 0,
            "membresias_activas": 0,
            "membresias_vencidas": 0,
            "proximos_vencimientos_90d": 0,
            "riesgo_rojo_alto": 0,
            "riesgo_amarillo_medio": 0,
            "riesgo_verde_bajo": 0,
            "retiros_definitivos_actuales": 0,
            "fuente_datos": "fallback_default",
        }

    def listar_empresas_retencion(
        self, semaforo: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Lista empresas desde agg_retencion_empresa filtrando por semáforo.

        Args:
            semaforo: Filtro opcional de semáforo ('ROJO_RIESGO_ALTO', etc.).
            limit: Cantidad máxima de registros a retornar.

        Returns:
            Lista de diccionarios con información de retención por empresa.

        """
        if self.session is not None:
            try:
                query = self.session.query(GoldAggRetencionEmpresa)
                if semaforo:
                    query = query.filter(
                        GoldAggRetencionEmpresa.semaforo_riesgo_renovacion == semaforo
                    )
                filas = (
                    query.order_by(
                        GoldAggRetencionEmpresa.puntaje_heuristico_riesgo.desc()
                    )
                    .limit(limit)
                    .all()
                )
                if filas:
                    return [
                        {
                            "id_empresa": str(f.id_empresa),
                            "kam_id": str(f.kam_id),
                            "estado_membresia_detalle": str(f.estado_membresia_detalle),
                            "fecha_expiracion": f.fecha_expiracion,
                            "dias_para_expiracion": f.dias_para_expiracion,
                            "es_membresia_vencida": bool(f.es_membresia_vencida),
                            "es_proximo_vencimiento_90d": bool(
                                f.es_proximo_vencimiento_90d
                            ),
                            "estado_vigencia_expiracion": str(
                                f.estado_vigencia_expiracion
                            ),
                            "puntaje_heuristico_riesgo": int(
                                f.puntaje_heuristico_riesgo or 0
                            ),
                            "semaforo_riesgo_renovacion": str(
                                f.semaforo_riesgo_renovacion
                            ),
                        }
                        for f in filas
                    ]
            except Exception as exc:
                logger.debug("Fallback empresas retención a Parquet: %s", exc)

        cfg = cargar_configuracion()
        ruta_ret = cfg.gold_dir / "agg_retencion_empresa.parquet"
        if ruta_ret.exists():
            df_ret = pd.read_parquet(ruta_ret)
            if semaforo:
                df_ret = df_ret[df_ret["semaforo_riesgo_renovacion"] == semaforo]
            cols = [
                "id_empresa",
                "kam_id",
                "estado_membresia_detalle",
                "fecha_expiracion",
                "dias_para_expiracion",
                "es_membresia_vencida",
                "es_proximo_vencimiento_90d",
                "estado_vigencia_expiracion",
                "puntaje_heuristico_riesgo",
                "semaforo_riesgo_renovacion",
            ]
            df_top = (
                df_ret[cols]
                .sort_values("puntaje_heuristico_riesgo", ascending=False)
                .head(limit)
            )
            return [
                {str(k): (None if pd.isna(v) else v) for k, v in row.items()}
                for row in df_top.to_dict(orient="records")
            ]
        return []
