"""Repositorio de acceso a datos Gold y Silver para el módulo de afiliados."""

import logging
from typing import Any

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.eda.config import cargar_configuracion
from app.modules.eda.models.gold_agg_participacion_empresa import (
    GoldAggParticipacionEmpresa,
)
from app.modules.eda.models.gold_agg_retencion_empresa import (
    GoldAggRetencionEmpresa,
)

logger = logging.getLogger(__name__)


class AffiliatesRepository:
    """Gestiona consultas de afiliados sobre PostgreSQL o archivos Gold Parquet."""

    def __init__(self, session: Session | None = None) -> None:
        """Inicializa el repositorio con una sesión SQLAlchemy opcional.

        Args:
            session: Sesión activa de SQLAlchemy o None para lectura local.

        """
        self.session = session

    def _leer_desde_db(self) -> dict[str, Any] | None:
        """Consulta indicadores agregados de afiliados desde PostgreSQL.

        Returns:
            Diccionario con métricas de afiliados o None si no hay datos en DB.

        """
        if self.session is None:
            return None
        try:
            q_ret = self.session.query(GoldAggRetencionEmpresa)
            total_emp = int(q_ret.count())
            if total_emp == 0:
                return None
            en_crm = int(
                q_ret.filter(GoldAggRetencionEmpresa.en_crm_afiliados.is_(True)).count()
            )
            activas = int(
                q_ret.filter(
                    GoldAggRetencionEmpresa.es_membresia_activa.is_(True)
                ).count()
            )
            renovaciones = int(
                self.session.query(
                    func.sum(GoldAggRetencionEmpresa.renovaciones_registradas_2026)
                ).scalar()
                or 0
            )
            con_part = int(
                self.session.query(GoldAggParticipacionEmpresa)
                .filter(GoldAggParticipacionEmpresa.total_eventos > 0)
                .count()
            )
            total_asist = int(
                self.session.query(
                    func.sum(GoldAggParticipacionEmpresa.total_asistencias)
                ).scalar()
                or 0
            )
            return {
                "total_empresas": total_emp,
                "empresas_en_crm": en_crm,
                "prospectos_sin_crm": total_emp - en_crm,
                "afiliados_activos_crm": activas,
                "empresas_con_participacion": con_part,
                "total_asistencias_eventos": total_asist,
                "renovaciones_registradas_2026": renovaciones,
                "fuente_datos": "postgresql",
            }
        except Exception as exc:
            logger.debug("Fallback de afiliados a Parquet: %s", exc)
            return None

    def obtener_resumen_afiliados(self) -> dict[str, Any]:
        """Obtiene el resumen consolidado de afiliados desde Gold (DB o Parquet).

        Returns:
            Diccionario con conteos reales de empresas afiliadas y participación.

        """
        desde_db = self._leer_desde_db()
        if desde_db is not None:
            return desde_db

        cfg = cargar_configuracion()
        ruta_ret = cfg.gold_dir / "agg_retencion_empresa.parquet"
        ruta_part = cfg.gold_dir / "agg_participacion_empresa.parquet"
        if ruta_ret.exists() and ruta_part.exists():
            df_ret = pd.read_parquet(ruta_ret)
            df_part = pd.read_parquet(ruta_part)
            total_emp = int(len(df_ret))
            en_crm = int(df_ret["en_crm_afiliados"].astype(bool).sum())
            return {
                "total_empresas": total_emp,
                "empresas_en_crm": en_crm,
                "prospectos_sin_crm": total_emp - en_crm,
                "afiliados_activos_crm": int(
                    df_ret["es_membresia_activa"].astype(bool).sum()
                ),
                "empresas_con_participacion": int((df_part["total_eventos"] > 0).sum()),
                "total_asistencias_eventos": int(df_part["total_asistencias"].sum()),
                "renovaciones_registradas_2026": int(
                    df_ret["renovaciones_registradas_2026"].sum()
                ),
                "fuente_datos": "gold_parquet",
            }

        return {
            "total_empresas": 0,
            "empresas_en_crm": 0,
            "prospectos_sin_crm": 0,
            "afiliados_activos_crm": 0,
            "empresas_con_participacion": 0,
            "total_asistencias_eventos": 0,
            "renovaciones_registradas_2026": 0,
            "fuente_datos": "sin_datos",
        }

    def listar_participacion_empresas(self, limit: int = 20) -> list[dict[str, Any]]:
        """Lista los registros de participación por empresa desde la capa Gold.

        Args:
            limit: Cantidad máxima de registros a retornar.

        Returns:
            Lista de diccionarios con indicadores de participación por empresa.

        """
        if self.session is not None:
            try:
                filas = (
                    self.session.query(GoldAggParticipacionEmpresa)
                    .order_by(GoldAggParticipacionEmpresa.total_asistencias.desc())
                    .limit(limit)
                    .all()
                )
                if filas:
                    return [
                        {
                            "id_empresa": str(f.id_empresa),
                            "periodo_analisis": str(f.periodo_analisis),
                            "kam_id": str(f.kam_id),
                            "total_eventos": int(f.total_eventos or 0),
                            "total_asistencias": int(f.total_asistencias or 0),
                            "personas_distintas_participantes": int(
                                f.personas_distintas_participantes or 0
                            ),
                            "ultima_fecha_participacion": (f.ultima_fecha_participacion),
                            "estado_recencia_participacion": (
                                f.estado_recencia_participacion
                            ),
                        }
                        for f in filas
                    ]
            except Exception as exc:
                logger.debug("Fallback listado participación a Parquet: %s", exc)

        cfg = cargar_configuracion()
        ruta_part = cfg.gold_dir / "agg_participacion_empresa.parquet"
        if ruta_part.exists():
            df_part = pd.read_parquet(ruta_part)
            cols = [
                "id_empresa",
                "periodo_analisis",
                "kam_id",
                "total_eventos",
                "total_asistencias",
                "personas_distintas_participantes",
                "ultima_fecha_participacion",
                "estado_recencia_participacion",
            ]
            df_top = (
                df_part[cols]
                .sort_values("total_asistencias", ascending=False)
                .head(limit)
            )
            return [
                {str(k): (None if pd.isna(v) else v) for k, v in row.items()}
                for row in df_top.to_dict(orient="records")
            ]
        return []
