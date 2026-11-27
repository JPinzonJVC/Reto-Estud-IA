"""Repositorio de acceso a gold_dim_empresa_360 para el módulo de retención."""

import logging
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.modules.eda.config import cargar_configuracion
from app.modules.eda.models.gold_dim_empresa_360 import GoldDimEmpresa360

logger = logging.getLogger(__name__)

TRAMOS_PROXIMOS_90D: tuple[str, ...] = ("0_30D", "31_60D", "61_90D")


class RetentionRepository:
    """Gestiona consultas de retención, semáforo híbrido y ML sobre Gold 360."""

    def __init__(self, session: Session | None = None) -> None:
        """Inicializa el repositorio con una sesión SQLAlchemy opcional.

        Args:
            session: Sesión activa de SQLAlchemy o None para lectura local.

        """
        self.session = session

    def _leer_resumen_desde_db(self) -> dict[str, Any] | None:
        """Consulta el resumen de retención y semáforo híbrido desde PostgreSQL.

        Returns:
            Diccionario de indicadores de retención o None si la tabla está vacía.

        """
        if self.session is None:
            return None
        try:
            q_base = self.session.query(GoldDimEmpresa360)
            total = int(q_base.count())
            if total == 0:
                return None

            activas = int(
                q_base.filter(GoldDimEmpresa360.es_membresia_activa.is_(True)).count()
            )
            vencidas = int(
                q_base.filter(GoldDimEmpresa360.tramo_vencimiento == "VENCIDA").count()
            )
            prox_90 = int(
                q_base.filter(
                    GoldDimEmpresa360.tramo_vencimiento.in_(TRAMOS_PROXIMOS_90D)
                ).count()
            )
            rojo = int(
                q_base.filter(
                    GoldDimEmpresa360.semaforo_riesgo_renovacion == "ROJO"
                ).count()
            )
            amarillo = int(
                q_base.filter(
                    GoldDimEmpresa360.semaforo_riesgo_renovacion == "AMARILLO"
                ).count()
            )
            verde = int(
                q_base.filter(
                    GoldDimEmpresa360.semaforo_riesgo_renovacion == "VERDE"
                ).count()
            )
            retiros = int(
                q_base.filter(
                    GoldDimEmpresa360.tipo_relacion_actho == "EX_AFILIADO"
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
        """Obtiene el resumen de retención y semáforo desde gold_dim_empresa_360.

        Returns:
            Diccionario con conteos de vigencias, vencimientos y niveles de riesgo.

        """
        desde_db = self._leer_resumen_desde_db()
        if desde_db is not None:
            return desde_db

        cfg = cargar_configuracion()
        ruta_360 = cfg.gold_dir / "dim_empresa_360.parquet"
        if ruta_360.exists():
            df_emp = pd.read_parquet(ruta_360)
            return {
                "total_empresas": int(len(df_emp)),
                "membresias_activas": int(
                    df_emp["es_membresia_activa"].astype(bool).sum()
                ),
                "membresias_vencidas": int(
                    (df_emp["tramo_vencimiento"] == "VENCIDA").sum()
                ),
                "proximos_vencimientos_90d": int(
                    df_emp["tramo_vencimiento"].isin(TRAMOS_PROXIMOS_90D).sum()
                ),
                "riesgo_rojo_alto": int(
                    (df_emp["semaforo_riesgo_renovacion"] == "ROJO").sum()
                ),
                "riesgo_amarillo_medio": int(
                    (df_emp["semaforo_riesgo_renovacion"] == "AMARILLO").sum()
                ),
                "riesgo_verde_bajo": int(
                    (df_emp["semaforo_riesgo_renovacion"] == "VERDE").sum()
                ),
                "retiros_definitivos_actuales": int(
                    (df_emp["tipo_relacion_actho"] == "EX_AFILIADO").sum()
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
        """Lista empresas desde gold_dim_empresa_360 con su semáforo y scores ML.

        Args:
            semaforo: Filtro opcional ('ROJO', 'AMARILLO', 'VERDE', 'NO_APLICA').
            limit: Cantidad máxima de registros a retornar.

        Returns:
            Lista de diccionarios con información de vigencia, riesgo y fidelidad.

        """
        if self.session is not None:
            try:
                query = self.session.query(GoldDimEmpresa360)
                if semaforo:
                    query = query.filter(
                        GoldDimEmpresa360.semaforo_riesgo_renovacion == semaforo
                    )
                filas = (
                    query.order_by(
                        GoldDimEmpresa360.probabilidad_churn_ml.desc().nulls_last()
                    )
                    .limit(limit)
                    .all()
                )
                if filas:
                    return [
                        {
                            "id_empresa": str(f.id_empresa),
                            "tipo_relacion_actho": str(f.tipo_relacion_actho),
                            "kam_id": str(f.kam_id),
                            "responsable_kam": str(f.responsable_kam),
                            "nivel_membresia": f.nivel_membresia,
                            "sector_economico": f.sector_economico,
                            "nombre_ciudad": f.nombre_ciudad,
                            "estado_membresia_detalle": str(f.estado_membresia_detalle),
                            "fecha_fin_vigencia": f.fecha_fin_vigencia,
                            "dias_para_expiracion": f.dias_para_expiracion,
                            "tramo_vencimiento": str(f.tramo_vencimiento),
                            "puntaje_riesgo_heuristico": f.puntaje_riesgo_heuristico,
                            "probabilidad_churn_ml": f.probabilidad_churn_ml,
                            "semaforo_riesgo_renovacion": str(
                                f.semaforo_riesgo_renovacion
                            ),
                            "score_fidelidad_ml_0_100": f.score_fidelidad_ml_0_100,
                            "arquetipo_fidelidad_ml": f.arquetipo_fidelidad_ml,
                        }
                        for f in filas
                    ]
            except Exception as exc:
                logger.debug("Fallback empresas retención a Parquet: %s", exc)

        cfg = cargar_configuracion()
        ruta_360 = cfg.gold_dir / "dim_empresa_360.parquet"
        if ruta_360.exists():
            df_emp = pd.read_parquet(ruta_360)
            if semaforo:
                df_emp = df_emp[df_emp["semaforo_riesgo_renovacion"] == semaforo]
            cols = [
                "id_empresa",
                "tipo_relacion_actho",
                "kam_id",
                "responsable_kam",
                "nivel_membresia",
                "sector_economico",
                "nombre_ciudad",
                "estado_membresia_detalle",
                "fecha_fin_vigencia",
                "dias_para_expiracion",
                "tramo_vencimiento",
                "puntaje_riesgo_heuristico",
                "probabilidad_churn_ml",
                "semaforo_riesgo_renovacion",
                "score_fidelidad_ml_0_100",
                "arquetipo_fidelidad_ml",
            ]
            df_top = (
                df_emp[cols]
                .sort_values("probabilidad_churn_ml", ascending=False, na_position="last")
                .head(limit)
            )
            return [
                {str(k): (None if pd.isna(v) else v) for k, v in row.items()}
                for row in df_top.to_dict(orient="records")
            ]
        return []
