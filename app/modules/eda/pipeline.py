"""Orquestador principal del pipeline ETL Medallion ACTHO 360 (Silver 3NF + Gold)."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.engine import Engine

from app.database import ping_database
from app.modules.eda.audit import BitacoraAuditoria, persistir_auditoria_final
from app.modules.eda.bronze import (
    calcular_sha256_archivo,
    guardar_tabla_medallion,
    homologar_kam_id,
    ingerir_y_validar_bronze,
)
from app.modules.eda.config import ConfiguracionETL, cargar_configuracion
from app.modules.eda.gold import construir_capa_gold
from app.modules.eda.postgres_loader import cargar_tablas_en_postgres
from app.modules.eda.silver import procesar_capa_silver

logger = logging.getLogger(__name__)


def _construir_resumen_ejecucion(
    run_id: str,
    ts_inicio: str,
    *,
    df_hashes: pd.DataFrame,
    df_cargas: pd.DataFrame,
    df_rechazados: pd.DataFrame,
    errores: list[str],
) -> pd.DataFrame:
    """Construye el DataFrame de resumen de ejecución audit_ejecuciones_etl.

    Args:
        run_id: Identificador único de la ejecución.
        ts_inicio: Fecha y hora de inicio.
        df_hashes: Tabla de hashes de archivos Bronze.
        df_cargas: Tabla de cargas ejecutadas.
        df_rechazados: Tabla de registros rechazados.
        errores: Lista de errores capturados.

    Returns:
        DataFrame de una fila con el resumen de la ejecución.

    """
    leidos = int(df_hashes["filas_leidas"].sum()) if not df_hashes.empty else 0
    cargados = int(df_cargas["registros_insertados"].sum()) if not df_cargas.empty else 0
    return pd.DataFrame(
        [
            {
                "id_ejecucion": run_id,
                "fecha_inicio": ts_inicio,
                "fecha_finalizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "archivos_procesados": int(len(df_hashes)),
                "registros_leidos": leidos,
                "registros_cargados": cargados,
                "registros_rechazados": int(len(df_rechazados)),
                "duplicados_identificados": 0,
                "errores": " | ".join(errores) if errores else "NINGUNO",
                "estado_ejecucion": "FALLIDO" if errores else "EXITOSO",
            }
        ]
    )


def ejecutar_pipeline_completo(
    cfg: ConfiguracionETL | None = None,
    ruta_config: Path | str | None = None,
    *,
    persistir_en_db: bool = False,
    db_engine: Engine | None = None,
    run_id: str | None = None,
    permitir_actualizacion_bronze: bool = False,
) -> dict[str, Any]:
    """Ejecuta el pipeline ETL completo con validación Bronze, Silver, Gold y DB.

    Args:
        cfg: Instancia opcional de ConfiguracionETL ya construida.
        ruta_config: Ruta opcional al archivo JSON de configuración.
        persistir_en_db: Si es True, persiste todas las capas en PostgreSQL/SQLite.
        db_engine: Motor SQLAlchemy opcional para persistencia transaccional.
        run_id: Identificador opcional de ejecución para trazabilidad desde API.

    Returns:
        Diccionario con la configuración, tablas generadas y métricas de auditoría.

    """
    if cfg is None:
        cfg = cargar_configuracion(ruta_config=ruta_config)

    cfg.asegurar_directorios()
    ts_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_id = run_id or f"ETL-ACTHO360-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    bitacora = BitacoraAuditoria(run_id=run_id, fecha_corte=cfg.fecha_corte)

    bronze, df_hashes = ingerir_y_validar_bronze(
        cfg,
        run_id=run_id,
        ts_ingesta=ts_inicio,
        permitir_actualizacion_bronze=permitir_actualizacion_bronze,
    )
    silver = procesar_capa_silver(bronze, cfg, bitacora)
    gold = construir_capa_gold(silver, cfg, bitacora)

    aud_res = persistir_auditoria_final(bronze, silver, cfg, bitacora)
    df_ejec = _construir_resumen_ejecucion(
        run_id,
        ts_inicio,
        df_hashes=df_hashes,
        df_cargas=aud_res["cargas"],
        df_rechazados=aud_res["rechazados"],
        errores=bitacora.errores,
    )
    guardar_tabla_medallion(df_ejec, cfg.audit_dir, "audit_ejecuciones_etl")

    conteos_db: dict[str, int] = {}
    if persistir_en_db or db_engine is not None:
        audit_tabs = {
            "audit_hashes_fuentes_bronze": df_hashes,
            "audit_registros_rechazados": aud_res["rechazados"],
            "audit_calidad_datos": aud_res["calidad"],
            "audit_reconciliacion_origen_destino": aud_res["reconciliacion"],
            "audit_cargas": aud_res["cargas"],
            "audit_ejecuciones_etl": df_ejec,
        }
        conteos_db = cargar_tablas_en_postgres(
            {"silver": silver, "gold": gold, "audit": audit_tabs},
            engine=db_engine,
        )

    return {
        "config": cfg,
        "run_id": run_id,
        "inicio": ts_inicio,
        "fin": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "silver": silver,
        "gold": gold,
        "hashes_bronze": df_hashes,
        "reconciliacion": aud_res["reconciliacion"],
        "calidad": aud_res["calidad"],
        "rechazados": aud_res["rechazados"],
        "cargas": aud_res["cargas"],
        "ejecucion": df_ejec,
        "errores": list(bitacora.errores),
        "conteos_db": conteos_db,
    }


__all__ = [
    "ConfiguracionETL",
    "calcular_sha256_archivo",
    "cargar_configuracion",
    "cargar_tablas_en_postgres",
    "ejecutar_pipeline_completo",
    "guardar_tabla_medallion",
    "homologar_kam_id",
    "ingerir_y_validar_bronze",
]


if __name__ == "__main__":
    ejecutar_pipeline_completo(persistir_en_db=ping_database())
    logger.info("Pipeline ETL Medallion ACTHO 360 (v3.0 DWH) completado exitosamente.")
