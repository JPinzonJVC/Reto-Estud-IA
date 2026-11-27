"""Repositorio de acceso al Esquema Estrella Gold para el módulo de afiliados."""

import logging
from typing import Any

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.eda.config import cargar_configuracion
from app.modules.eda.models.gold_dim_empresa_360 import GoldDimEmpresa360
from app.modules.eda.models.gold_hechos_y_marts import GoldFactEvolucionMembresiasMes

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
            q_emp = self.session.query(GoldDimEmpresa360)
            total_emp = int(q_emp.count())
            if total_emp == 0:
                return None

            prospectos = int(
                q_emp.filter(
                    GoldDimEmpresa360.tipo_relacion_actho == "PROSPECTO_NO_AFILIADO"
                ).count()
            )
            en_crm = total_emp - prospectos
            activas = int(
                q_emp.filter(GoldDimEmpresa360.es_membresia_activa.is_(True)).count()
            )
            activas_serv = int(
                q_emp.filter(
                    GoldDimEmpresa360.es_membresia_activa.is_(True),
                    GoldDimEmpresa360.total_eventos_anio > 0,
                ).count()
            )
            con_part = int(q_emp.filter(GoldDimEmpresa360.total_eventos_anio > 0).count())
            total_asist = int(
                self.session.query(
                    func.sum(GoldDimEmpresa360.total_asistencias_anio)
                ).scalar()
                or 0
            )
            renovaciones = int(
                self.session.query(
                    func.sum(GoldFactEvolucionMembresiasMes.renovaciones_efectivas_mes)
                ).scalar()
                or 0
            )
            tasa_serv = round((activas_serv / activas) * 100.0, 2) if activas > 0 else 0.0
            return {
                "total_empresas": total_emp,
                "empresas_en_crm": en_crm,
                "prospectos_sin_crm": prospectos,
                "afiliados_activos_crm": activas,
                "afiliados_activos_en_servicios": activas_serv,
                "tasa_afiliados_activos_en_servicios_pct": tasa_serv,
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
        ruta_360 = cfg.gold_dir / "dim_empresa_360.parquet"
        ruta_evo = cfg.gold_dir / "fact_evolucion_membresias_mes.parquet"
        if ruta_360.exists():
            df_emp = pd.read_parquet(ruta_360)
            total_emp = int(len(df_emp))
            prospectos = int(
                (df_emp["tipo_relacion_actho"] == "PROSPECTO_NO_AFILIADO").sum()
            )
            activas = int(df_emp["es_membresia_activa"].astype(bool).sum())
            activas_serv = int(
                (
                    df_emp["es_membresia_activa"].astype(bool)
                    & (df_emp["total_eventos_anio"] > 0)
                ).sum()
            )
            renov = (
                int(pd.read_parquet(ruta_evo)["renovaciones_efectivas_mes"].sum())
                if ruta_evo.exists()
                else 0
            )
            tasa_serv = round((activas_serv / activas) * 100.0, 2) if activas > 0 else 0.0
            return {
                "total_empresas": total_emp,
                "empresas_en_crm": total_emp - prospectos,
                "prospectos_sin_crm": prospectos,
                "afiliados_activos_crm": activas,
                "afiliados_activos_en_servicios": activas_serv,
                "tasa_afiliados_activos_en_servicios_pct": tasa_serv,
                "empresas_con_participacion": int(
                    (df_emp["total_eventos_anio"] > 0).sum()
                ),
                "total_asistencias_eventos": int(df_emp["total_asistencias_anio"].sum()),
                "renovaciones_registradas_2026": renov,
                "fuente_datos": "gold_parquet",
            }

        return {
            "total_empresas": 0,
            "empresas_en_crm": 0,
            "prospectos_sin_crm": 0,
            "afiliados_activos_crm": 0,
            "afiliados_activos_en_servicios": 0,
            "tasa_afiliados_activos_en_servicios_pct": 0.0,
            "empresas_con_participacion": 0,
            "total_asistencias_eventos": 0,
            "renovaciones_registradas_2026": 0,
            "fuente_datos": "sin_datos",
        }

    def listar_participacion_empresas(self, limit: int = 20) -> list[dict[str, Any]]:
        """Lista las empresas con mayor participación desde gold_dim_empresa_360.

        Args:
            limit: Cantidad máxima de registros a retornar.

        Returns:
            Lista de diccionarios con indicadores de participación y recomendación ML.

        """
        if self.session is not None:
            try:
                filas = (
                    self.session.query(GoldDimEmpresa360)
                    .order_by(GoldDimEmpresa360.total_asistencias_anio.desc())
                    .limit(limit)
                    .all()
                )
                if filas:
                    return [
                        {
                            "id_empresa": str(f.id_empresa),
                            "tipo_relacion_actho": str(f.tipo_relacion_actho),
                            "kam_id": str(f.kam_id),
                            "sector_economico": f.sector_economico,
                            "nombre_ciudad": f.nombre_ciudad,
                            "total_eventos": int(f.total_eventos_anio or 0),
                            "total_asistencias": int(f.total_asistencias_anio or 0),
                            "personas_distintas_participantes": int(
                                f.personas_distintas_anio or 0
                            ),
                            "asistencias_ultimo_trimestre": int(
                                f.asistencias_ultimo_trimestre or 0
                            ),
                            "dias_sin_participacion": f.dias_sin_participacion,
                            "linea_2027_recomendada_ml": f.linea_2027_recomendada_ml,
                        }
                        for f in filas
                    ]
            except Exception as exc:
                logger.debug("Fallback listado participación a Parquet: %s", exc)

        cfg = cargar_configuracion()
        ruta_360 = cfg.gold_dir / "dim_empresa_360.parquet"
        if ruta_360.exists():
            df_emp = pd.read_parquet(ruta_360)
            df_top = df_emp.sort_values("total_asistencias_anio", ascending=False).head(
                limit
            )
            salida: list[dict[str, Any]] = []
            for _, r in df_top.iterrows():
                salida.append(
                    {
                        "id_empresa": str(r["id_empresa"]),
                        "tipo_relacion_actho": str(r["tipo_relacion_actho"]),
                        "kam_id": str(r["kam_id"]),
                        "sector_economico": (
                            None
                            if pd.isna(r["sector_economico"])
                            else str(r["sector_economico"])
                        ),
                        "nombre_ciudad": (
                            None
                            if pd.isna(r["nombre_ciudad"])
                            else str(r["nombre_ciudad"])
                        ),
                        "total_eventos": int(r["total_eventos_anio"]),
                        "total_asistencias": int(r["total_asistencias_anio"]),
                        "personas_distintas_participantes": int(
                            r["personas_distintas_anio"]
                        ),
                        "asistencias_ultimo_trimestre": int(
                            r["asistencias_ultimo_trimestre"]
                        ),
                        "dias_sin_participacion": (
                            None
                            if pd.isna(r["dias_sin_participacion"])
                            else float(r["dias_sin_participacion"])
                        ),
                        "linea_2027_recomendada_ml": (
                            None
                            if pd.isna(r["linea_2027_recomendada_ml"])
                            else str(r["linea_2027_recomendada_ml"])
                        ),
                    }
                )
            return salida
        return []
