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


def _calcular_nps_adaptado_resumen(prom: int, det: int, total: int) -> float:
    """Calcula el NPS adaptado (%Promotores - %Detractores) entre -100 y +100.

    Args:
        prom: Cantidad de respuestas promotoras (4-5).
        det: Cantidad de respuestas detractoras (1-2).
        total: Total de respuestas evaluadas.

    Returns:
        Puntaje NPS adaptado redondeado a 2 decimales.

    """
    if total <= 0:
        return 0.0
    return round(((prom - det) / total) * 100.0, 2)


class AnalyticsRepository:
    """Gestiona consultas analíticas sobre PostgreSQL o archivos Gold Parquet."""

    def __init__(self, session: Session | None = None) -> None:
        """Inicializa el repositorio con una sesión SQLAlchemy opcional.

        Args:
            session: Sesión activa de SQLAlchemy o None para lectura local.

        """
        self.session = session

    def _leer_metricas_desde_db(self) -> dict[str, Any] | None:
        """Consulta métricas globales de participación, satisfacción y NPS en DB.

        Returns:
            Diccionario de indicadores calculados desde DB o None si está vacía.

        """
        if self.session is None:
            return None
        try:
            q_part = self.session.query(GoldAggParticipacionEmpresa)
            total_emp = int(q_part.count())
            if total_emp == 0:
                return None
            emp_con_part = int(
                q_part.filter(GoldAggParticipacionEmpresa.total_eventos > 0).count()
            )
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
            modalidades = self._sumar_modalidades_db()
            nps_info = self._sumar_nps_y_satisfaccion_db()
            tasa_part = round(emp_con_part / total_emp, 4) if total_emp else 0.0
            return {
                "total_empresas": total_emp,
                "empresas_con_participacion": emp_con_part,
                "tasa_participacion_empresas": tasa_part,
                "total_asistencias": total_asist,
                "personas_participantes_acumuladas": total_personas,
                "participacion_por_modalidad": modalidades,
                **nps_info,
                "fuente_datos": "postgresql",
            }
        except Exception as exc:
            logger.debug("Fallback métricas analítica a Parquet: %s", exc)
            return None

    def _sumar_modalidades_db(self) -> dict[str, int]:
        """Suma las asistencias por modalidad en PostgreSQL.

        Returns:
            Diccionario con conteos presencial, virtual e híbrido.

        """
        assert self.session is not None
        pres = int(
            self.session.query(
                func.sum(GoldAggParticipacionEmpresa.participacion_modalidad_presencial)
            ).scalar()
            or 0
        )
        virt = int(
            self.session.query(
                func.sum(GoldAggParticipacionEmpresa.participacion_modalidad_virtual)
            ).scalar()
            or 0
        )
        hib = int(
            self.session.query(
                func.sum(GoldAggParticipacionEmpresa.participacion_modalidad_hibrido)
            ).scalar()
            or 0
        )
        return {"presencial": pres, "virtual": virt, "hibrido": hib}

    def _sumar_nps_y_satisfaccion_db(self) -> dict[str, Any]:
        """Calcula totales de satisfacción y NPS adaptado (1-5) desde PostgreSQL.

        Returns:
            Diccionario con promedios 1-5 y desglose de NPS adaptado.

        """
        assert self.session is not None
        total_resp = int(
            self.session.query(
                func.sum(GoldAggSatisfaccionEncuestas.total_respuestas)
            ).scalar()
            or 0
        )
        prom_sat = float(
            self.session.query(
                func.avg(GoldAggSatisfaccionEncuestas.promedio_satisfaccion_general_1_5)
            ).scalar()
            or 0.0
        )
        prom_1_5 = int(
            self.session.query(
                func.sum(GoldAggSatisfaccionEncuestas.promotores_nps_adaptado_1_5)
            ).scalar()
            or 0
        )
        neu_1_5 = int(
            self.session.query(
                func.sum(GoldAggSatisfaccionEncuestas.neutros_nps_adaptado_1_5)
            ).scalar()
            or 0
        )
        det_1_5 = int(
            self.session.query(
                func.sum(GoldAggSatisfaccionEncuestas.detractores_nps_adaptado_1_5)
            ).scalar()
            or 0
        )
        return {
            "total_respuestas_encuestas": total_resp,
            "promedio_satisfaccion_general_1_5": round(prom_sat, 2),
            "promotores_nps_adaptado_1_5": prom_1_5,
            "neutros_nps_adaptado_1_5": neu_1_5,
            "detractores_nps_adaptado_1_5": det_1_5,
            "nps_adaptado_global_1_5": _calcular_nps_adaptado_resumen(
                prom_1_5, det_1_5, total_resp
            ),
            "estado_calculo_nps": "NPS_ADAPTADO_1_5_CALCULADO",
        }

    def obtener_metricas_analitica(self) -> dict[str, Any]:
        """Obtiene métricas cuantitativas calculadas desde las tablas Gold.

        Returns:
            Diccionario con métricas reales de asistencia, satisfacción y NPS adaptado.

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
            total_emp = int(len(df_part))
            emp_con_part = int((df_part["total_eventos"] > 0).sum())
            tasa_part = round(emp_con_part / total_emp, 4) if total_emp else 0.0
            prom_sat = (
                float(df_sat["promedio_satisfaccion_general_1_5"].mean())
                if not df_sat.empty
                else 0.0
            )
            tot_resp = int(df_sat["total_respuestas"].sum())
            prom_1_5 = int(df_sat["promotores_nps_adaptado_1_5"].sum())
            neu_1_5 = int(df_sat["neutros_nps_adaptado_1_5"].sum())
            det_1_5 = int(df_sat["detractores_nps_adaptado_1_5"].sum())
            return {
                "total_empresas": total_emp,
                "empresas_con_participacion": emp_con_part,
                "tasa_participacion_empresas": tasa_part,
                "total_asistencias": int(df_part["total_asistencias"].sum()),
                "personas_participantes_acumuladas": int(
                    df_part["personas_distintas_participantes"].sum()
                ),
                "participacion_por_modalidad": {
                    "presencial": int(
                        df_part["participacion_modalidad_presencial"].sum()
                    ),
                    "virtual": int(df_part["participacion_modalidad_virtual"].sum()),
                    "hibrido": int(df_part["participacion_modalidad_hibrido"].sum()),
                },
                "total_respuestas_encuestas": tot_resp,
                "promedio_satisfaccion_general_1_5": round(prom_sat, 2),
                "promotores_nps_adaptado_1_5": prom_1_5,
                "neutros_nps_adaptado_1_5": neu_1_5,
                "detractores_nps_adaptado_1_5": det_1_5,
                "nps_adaptado_global_1_5": _calcular_nps_adaptado_resumen(
                    prom_1_5, det_1_5, tot_resp
                ),
                "estado_calculo_nps": "NPS_ADAPTADO_1_5_CALCULADO",
                "fuente_datos": "gold_parquet",
            }

        return {
            "total_empresas": 0,
            "empresas_con_participacion": 0,
            "tasa_participacion_empresas": 0.0,
            "total_asistencias": 0,
            "personas_participantes_acumuladas": 0,
            "participacion_por_modalidad": {
                "presencial": 0,
                "virtual": 0,
                "hibrido": 0,
            },
            "total_respuestas_encuestas": 0,
            "promedio_satisfaccion_general_1_5": 0.0,
            "promotores_nps_adaptado_1_5": 0,
            "neutros_nps_adaptado_1_5": 0,
            "detractores_nps_adaptado_1_5": 0,
            "nps_adaptado_global_1_5": 0.0,
            "estado_calculo_nps": "SIN_DATOS",
            "fuente_datos": "sin_datos",
        }

    def listar_satisfaccion_encuestas(self) -> list[dict[str, Any]]:
        """Lista los indicadores de satisfacción y NPS adaptado por modalidad y mes.

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
                            "promotores_nps_adaptado_1_5": int(
                                f.promotores_nps_adaptado_1_5 or 0
                            ),
                            "neutros_nps_adaptado_1_5": int(
                                f.neutros_nps_adaptado_1_5 or 0
                            ),
                            "detractores_nps_adaptado_1_5": int(
                                f.detractores_nps_adaptado_1_5 or 0
                            ),
                            "nps_adaptado_1_5": float(f.nps_adaptado_1_5 or 0.0),
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
