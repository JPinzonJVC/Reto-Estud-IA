"""Repositorio de acceso al Esquema Estrella Gold para el módulo de analítica."""

import logging
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.eda.config import cargar_configuracion
from app.modules.eda.models.gold_dim_empresa_360 import GoldDimEmpresa360
from app.modules.eda.models.gold_hechos_y_marts import (
    GoldFactAsistenciasBi,
    GoldFactEncuestasBi,
)

logger = logging.getLogger(__name__)


def _agrupar_satisfaccion_df(df_enc: pd.DataFrame) -> list[dict[str, Any]]:
    """Calcula el desglose mensual ponderado sobre respuestas individuales Gold.

    Args:
        df_enc: DataFrame de gold_fact_encuestas_bi.

    Returns:
        Lista ordenada de diccionarios con satisfacción 1-5 y NPS 0-10 separados.

    """
    if df_enc.empty:
        return []

    grp = (
        df_enc.groupby(
            ["tipo_encuesta", "modalidad_encuesta", "periodo_mes_iso"],
            as_index=False,
        )
        .agg(
            total_respuestas=("id_respuesta", "count"),
            promedio_satisfaccion_general_1_5=("promedio_respuesta_1_5", "mean"),
            respuestas_alta_satisfaccion=(
                "nivel_satisfaccion_1_5",
                lambda s: int((s == "ALTA").sum()),
            ),
            respuestas_media_satisfaccion=(
                "nivel_satisfaccion_1_5",
                lambda s: int((s == "MEDIA").sum()),
            ),
            respuestas_baja_satisfaccion=(
                "nivel_satisfaccion_1_5",
                lambda s: int((s == "BAJA").sum()),
            ),
            promotores_0_10=(
                "categoria_nps_0_10",
                lambda s: int((s == "PROMOTOR").sum()) if s.notna().any() else np.nan,
            ),
            pasivos_0_10=(
                "categoria_nps_0_10",
                lambda s: int((s == "PASIVO").sum()) if s.notna().any() else np.nan,
            ),
            detractores_0_10=(
                "categoria_nps_0_10",
                lambda s: int((s == "DETRACTOR").sum()) if s.notna().any() else np.nan,
            ),
        )
        .sort_values(["tipo_encuesta", "modalidad_encuesta", "periodo_mes_iso"])
    )

    resultados: list[dict[str, Any]] = []
    for _, r in grp.iterrows():
        prom_0_10 = r["promotores_0_10"]
        pas_0_10 = r["pasivos_0_10"]
        det_0_10 = r["detractores_0_10"]
        nps_val: float | None = None
        if pd.notna(prom_0_10) and pd.notna(pas_0_10) and pd.notna(det_0_10):
            tot_n = int(prom_0_10) + int(pas_0_10) + int(det_0_10)
            if tot_n > 0:
                nps_val = round(((int(prom_0_10) - int(det_0_10)) / tot_n) * 100.0, 2)

        resultados.append(
            {
                "tipo_encuesta": str(r["tipo_encuesta"]),
                "modalidad_encuesta": str(r["modalidad_encuesta"]),
                "periodo_mes_iso": str(r["periodo_mes_iso"]),
                "total_respuestas": int(r["total_respuestas"]),
                "promedio_satisfaccion_general_1_5": (
                    0.0
                    if pd.isna(r["promedio_satisfaccion_general_1_5"])
                    else round(float(r["promedio_satisfaccion_general_1_5"]), 2)
                ),
                "respuestas_alta_satisfaccion": int(r["respuestas_alta_satisfaccion"]),
                "respuestas_media_satisfaccion": int(r["respuestas_media_satisfaccion"]),
                "respuestas_baja_satisfaccion": int(r["respuestas_baja_satisfaccion"]),
                "nps_oficial_0_10": nps_val,
                "estado_calculo_nps": (
                    "NPS_0_10_CALCULADO"
                    if nps_val is not None
                    else "PENDIENTE_ENCUESTA_ESCALA_0_10"
                ),
            }
        )
    return resultados


class AnalyticsRepository:
    """Gestiona consultas analíticas sobre el Esquema Estrella Gold."""

    def __init__(self, session: Session | None = None) -> None:
        """Inicializa el repositorio con una sesión SQLAlchemy opcional.

        Args:
            session: Sesión activa de SQLAlchemy o None para lectura local.

        """
        self.session = session

    def _leer_metricas_desde_db(self) -> dict[str, Any] | None:
        """Consulta métricas exactas (COUNT DISTINCT y media ponderada) en DB.

        Returns:
            Diccionario de indicadores calculados desde DB o None si está vacía.

        """
        if self.session is None:
            return None
        try:
            q_emp = self.session.query(GoldDimEmpresa360)
            total_emp = int(q_emp.count())
            if total_emp == 0:
                return None

            activas = int(
                q_emp.filter(GoldDimEmpresa360.es_membresia_activa.is_(True)).count()
            )
            activas_con_part = int(
                q_emp.filter(
                    GoldDimEmpresa360.es_membresia_activa.is_(True),
                    GoldDimEmpresa360.total_eventos_anio > 0,
                ).count()
            )
            tasa_part_activas = (
                round(activas_con_part / activas, 4) if activas > 0 else 0.0
            )

            total_asist = int(self.session.query(GoldFactAsistenciasBi).count())
            personas_unicas = int(
                self.session.query(GoldFactAsistenciasBi.id_persona)
                .filter(GoldFactAsistenciasBi.id_persona.isnot(None))
                .distinct()
                .count()
            )
            pres = int(
                self.session.query(GoldFactAsistenciasBi)
                .filter(GoldFactAsistenciasBi.modalidad == "Presencial")
                .count()
            )
            virt = int(
                self.session.query(GoldFactAsistenciasBi)
                .filter(GoldFactAsistenciasBi.modalidad == "Virtual")
                .count()
            )
            hib = int(
                self.session.query(GoldFactAsistenciasBi)
                .filter(GoldFactAsistenciasBi.modalidad == "Híbrido")
                .count()
            )

            total_resp = int(self.session.query(GoldFactEncuestasBi).count())
            prom_sat = float(
                self.session.query(
                    func.avg(GoldFactEncuestasBi.promedio_respuesta_1_5)
                ).scalar()
                or 0.0
            )
            nps_prom = int(
                self.session.query(GoldFactEncuestasBi)
                .filter(GoldFactEncuestasBi.categoria_nps_0_10 == "PROMOTOR")
                .count()
            )
            nps_pas = int(
                self.session.query(GoldFactEncuestasBi)
                .filter(GoldFactEncuestasBi.categoria_nps_0_10 == "PASIVO")
                .count()
            )
            nps_det = int(
                self.session.query(GoldFactEncuestasBi)
                .filter(GoldFactEncuestasBi.categoria_nps_0_10 == "DETRACTOR")
                .count()
            )
            tot_nps = nps_prom + nps_pas + nps_det
            nps_global = (
                round(((nps_prom - nps_det) / tot_nps) * 100.0, 2)
                if tot_nps > 0
                else None
            )

            return {
                "total_empresas": total_emp,
                "afiliados_activos": activas,
                "empresas_con_participacion": activas_con_part,
                "tasa_participacion_empresas": tasa_part_activas,
                "total_asistencias": total_asist,
                "personas_unicas_participantes": personas_unicas,
                "participacion_por_modalidad": {
                    "presencial": pres,
                    "virtual": virt,
                    "hibrido": hib,
                },
                "total_respuestas_encuestas": total_resp,
                "promedio_satisfaccion_general_1_5": round(prom_sat, 2),
                "nps_oficial_global_0_10": nps_global,
                "estado_calculo_nps": (
                    "NPS_0_10_CALCULADO"
                    if nps_global is not None
                    else "PENDIENTE_ENCUESTA_ESCALA_0_10"
                ),
                "fuente_datos": "postgresql",
            }
        except Exception as exc:
            logger.debug("Fallback métricas analítica a Parquet: %s", exc)
            return None

    def obtener_metricas_analitica(self) -> dict[str, Any]:
        """Obtiene métricas cuantitativas exactas desde el Esquema Estrella Gold.

        Returns:
            Diccionario con métricas reales de asistencia, satisfacción y NPS.

        """
        desde_db = self._leer_metricas_desde_db()
        if desde_db is not None:
            return desde_db

        cfg = cargar_configuracion()
        r_emp = cfg.gold_dir / "dim_empresa_360.parquet"
        r_asi = cfg.gold_dir / "fact_asistencias_bi.parquet"
        r_enc = cfg.gold_dir / "fact_encuestas_bi.parquet"
        if r_emp.exists() and r_asi.exists() and r_enc.exists():
            df_emp = pd.read_parquet(r_emp)
            df_asi = pd.read_parquet(r_asi)
            df_enc = pd.read_parquet(r_enc)

            activas = df_emp[df_emp["es_membresia_activa"].astype(bool)]
            n_act = int(len(activas))
            n_act_part = int((activas["total_eventos_anio"] > 0).sum())
            tasa_p = round(n_act_part / n_act, 4) if n_act > 0 else 0.0

            prom_sat = (
                float(df_enc["promedio_respuesta_1_5"].mean())
                if not df_enc.empty
                else 0.0
            )
            sub_nps = df_enc["categoria_nps_0_10"].dropna()
            nps_global: float | None = None
            if len(sub_nps) > 0:
                p_c = int((sub_nps == "PROMOTOR").sum())
                d_c = int((sub_nps == "DETRACTOR").sum())
                nps_global = round(((p_c - d_c) / len(sub_nps)) * 100.0, 2)

            return {
                "total_empresas": int(len(df_emp)),
                "afiliados_activos": n_act,
                "empresas_con_participacion": n_act_part,
                "tasa_participacion_empresas": tasa_p,
                "total_asistencias": int(len(df_asi)),
                "personas_unicas_participantes": int(
                    df_asi["id_persona"].dropna().nunique()
                ),
                "participacion_por_modalidad": {
                    "presencial": int((df_asi["modalidad"] == "Presencial").sum()),
                    "virtual": int((df_asi["modalidad"] == "Virtual").sum()),
                    "hibrido": int((df_asi["modalidad"] == "Híbrido").sum()),
                },
                "total_respuestas_encuestas": int(len(df_enc)),
                "promedio_satisfaccion_general_1_5": round(prom_sat, 2),
                "nps_oficial_global_0_10": nps_global,
                "estado_calculo_nps": (
                    "NPS_0_10_CALCULADO"
                    if nps_global is not None
                    else "PENDIENTE_ENCUESTA_ESCALA_0_10"
                ),
                "fuente_datos": "gold_parquet",
            }

        return {
            "total_empresas": 0,
            "afiliados_activos": 0,
            "empresas_con_participacion": 0,
            "tasa_participacion_empresas": 0.0,
            "total_asistencias": 0,
            "personas_unicas_participantes": 0,
            "participacion_por_modalidad": {
                "presencial": 0,
                "virtual": 0,
                "hibrido": 0,
            },
            "total_respuestas_encuestas": 0,
            "promedio_satisfaccion_general_1_5": 0.0,
            "nps_oficial_global_0_10": None,
            "estado_calculo_nps": "SIN_DATOS",
            "fuente_datos": "sin_datos",
        }

    def listar_satisfaccion_encuestas(self) -> list[dict[str, Any]]:
        """Agrupa dinámicamente gold_fact_encuestas_bi con media ponderada exacta.

        Returns:
            Lista de indicadores mensuales por tipo y modalidad de encuesta.

        """
        if self.session is not None:
            try:
                filas = self.session.query(GoldFactEncuestasBi).all()
                if filas:
                    df_db = pd.DataFrame(
                        [
                            {
                                "id_respuesta": f.id_respuesta,
                                "tipo_encuesta": f.tipo_encuesta,
                                "modalidad_encuesta": f.modalidad_encuesta,
                                "periodo_mes_iso": f.periodo_mes_iso,
                                "promedio_respuesta_1_5": f.promedio_respuesta_1_5,
                                "nivel_satisfaccion_1_5": f.nivel_satisfaccion_1_5,
                                "categoria_nps_0_10": f.categoria_nps_0_10,
                            }
                            for f in filas
                        ]
                    )
                    return _agrupar_satisfaccion_df(df_db)
            except Exception as exc:
                logger.debug("Fallback satisfacción encuestas a Parquet: %s", exc)

        cfg = cargar_configuracion()
        ruta_enc = cfg.gold_dir / "fact_encuestas_bi.parquet"
        if ruta_enc.exists():
            return _agrupar_satisfaccion_df(pd.read_parquet(ruta_enc))
        return []
