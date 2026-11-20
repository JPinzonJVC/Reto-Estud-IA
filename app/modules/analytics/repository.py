"""Repositorio de acceso a datos Gold para el módulo de analítica."""

import logging
from typing import Any

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.eda.config import cargar_configuracion
from app.modules.eda.models.gold_agg_participacion_empresa import (
    GoldAggParticipacionEmpresa,
)
from app.modules.eda.models.gold_agg_satisfaccion_encuestas import (
    GoldAggSatisfaccionEncuestas,
)

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """Gestiona consultas analíticas sobre PostgreSQL o archivos Gold Parquet."""

    def __init__(self, session: Session | None = None) -> None:
        """Inicializa el repositorio con una sesión SQLAlchemy opcional.

        Args:
            session: Sesión activa de SQLAlchemy o None para lectura local.

        """
        self.session = session

    def _leer_metricas_desde_db(self) -> dict[str, Any] | None:
        """Consulta métricas globales de participación y satisfacción en PostgreSQL.

        Returns:
            Diccionario de indicadores o None si la base no contiene registros.

        """
        if self.session is None:
            return None
        try:
            total_resp = int(
                self.session.query(
                    func.sum(GoldAggSatisfaccionEncuestas.total_respuestas)
                ).scalar()
                or 0
            )
            if total_resp == 0:
                return None
            total_asist = int(
                self.session.query(
                    func.sum(GoldAggParticipacionEmpresa.total_asistencias)
                ).scalar()
                or 0
            )
            total_personas = int(
                self.session.query(
                    func.sum(GoldAggParticipacionEmpresa.personas_distintas_participantes)
                ).scalar()
                or 0
            )
            prom_sat = float(
                self.session.query(
                    func.avg(
                        GoldAggSatisfaccionEncuestas.promedio_satisfaccion_general_1_5
                    )
                ).scalar()
                or 0.0
            )
            return {
                "total_asistencias": total_asist,
                "personas_participantes_acumuladas": total_personas,
                "total_respuestas_encuestas": total_resp,
                "promedio_satisfaccion_general_1_5": round(prom_sat, 2),
                "estado_calculo_nps": ("NO_CALCULABLE_SIN_PREGUNTA_RECOMENDACION_0_10"),
                "fuente_datos": "postgresql",
            }
        except Exception as exc:
            logger.debug("Fallback métricas analítica a Parquet: %s", exc)
            return None

    def obtener_metricas_analitica(self) -> dict[str, Any]:
        """Obtiene métricas cuantitativas desde las tablas Gold de participación.

        Returns:
            Diccionario con métricas de asistencia y satisfacción 1-5.

        """
        desde_db = self._leer_metricas_desde_db()
        if desde_db is not None:
            return desde_db

        cfg = cargar_configuracion()
        ruta_part = cfg.gold_dir / "agg_participacion_empresa.parquet"
        ruta_sat = cfg.gold_dir / "agg_satisfaccion_encuestas.parquet"
        if ruta_part.exists() and ruta_sat.exists():
            df_part = pd.read_parquet(ruta_part)
            df_sat = pd.read_parquet(ruta_sat)
            prom = (
                float(df_sat["promedio_satisfaccion_general_1_5"].mean())
                if not df_sat.empty
                else 0.0
            )
            return {
                "total_asistencias": int(df_part["total_asistencias"].sum()),
                "personas_participantes_acumuladas": int(
                    df_part["personas_distintas_participantes"].sum()
                ),
                "total_respuestas_encuestas": int(df_sat["total_respuestas"].sum()),
                "promedio_satisfaccion_general_1_5": round(prom, 2),
                "estado_calculo_nps": ("NO_CALCULABLE_SIN_PREGUNTA_RECOMENDACION_0_10"),
                "fuente_datos": "gold_parquet",
            }

        return {
            "total_asistencias": 0,
            "personas_participantes_acumuladas": 0,
            "total_respuestas_encuestas": 0,
            "promedio_satisfaccion_general_1_5": 0.0,
            "estado_calculo_nps": "NO_CALCULABLE_SIN_PREGUNTA_RECOMENDACION_0_10",
            "fuente_datos": "fallback_default",
        }

    def listar_satisfaccion_encuestas(self) -> list[dict[str, Any]]:
        """Lista los indicadores de satisfacción por modalidad y periodo mensual.

        Returns:
            Lista de registros de agg_satisfaccion_encuestas.

        """
        if self.session is not None:
            try:
                filas = (
                    self.session.query(GoldAggSatisfaccionEncuestas)
                    .order_by(
                        GoldAggSatisfaccionEncuestas.modalidad_encuesta,
                        GoldAggSatisfaccionEncuestas.periodo_mes_iso,
                    )
                    .all()
                )
                if filas:
                    return [
                        {
                            "modalidad_encuesta": str(f.modalidad_encuesta),
                            "periodo_mes_iso": str(f.periodo_mes_iso),
                            "total_respuestas": int(f.total_respuestas or 0),
                            "promedio_satisfaccion_general_1_5": float(
                                f.promedio_satisfaccion_general_1_5 or 0.0
                            ),
                            "calificaciones_altas_475_a_500": int(
                                f.calificaciones_altas_475_a_500 or 0
                            ),
                            "calificaciones_medias_375_a_474": int(
                                f.calificaciones_medias_375_a_474 or 0
                            ),
                            "calificaciones_bajas_menores_375": int(
                                f.calificaciones_bajas_menores_375 or 0
                            ),
                            "nps_oficial_0_10": f.nps_oficial_0_10,
                            "estado_calculo_nps": str(f.estado_calculo_nps),
                        }
                        for f in filas
                    ]
            except Exception as exc:
                logger.debug("Fallback satisfacción encuestas a Parquet: %s", exc)

        cfg = cargar_configuracion()
        ruta_sat = cfg.gold_dir / "agg_satisfaccion_encuestas.parquet"
        if ruta_sat.exists():
            df_sat = pd.read_parquet(ruta_sat)
            return [
                {str(k): (None if pd.isna(v) else v) for k, v in row.items()}
                for row in df_sat.to_dict(orient="records")
            ]
        return []
