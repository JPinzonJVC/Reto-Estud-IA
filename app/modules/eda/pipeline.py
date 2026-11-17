"""Orquestador principal del pipeline ETL Medallion ACTHO 360."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.eda.audit import (
    BitacoraAuditoria,
    construir_audit_duplicados,
    persistir_auditoria_final,
)
from app.modules.eda.bronze import (
    calcular_sha256_archivo,
    guardar_tabla_medallion,
    homologar_kam_id,
    ingerir_y_validar_bronze,
)
from app.modules.eda.config import ConfiguracionETL, cargar_configuracion
from app.modules.eda.gold import (
    construir_agg_participacion_empresa,
    construir_agg_retencion_empresa,
    construir_agg_satisfaccion_encuestas,
)
from app.modules.eda.scd2 import construir_dim_empresas_scd2
from app.modules.eda.silver import procesar_capa_silver

logger = logging.getLogger(__name__)


def ejecutar_pipeline_completo(
    cfg: ConfiguracionETL | None = None,
    ruta_config: Path | str | None = None,
) -> dict[str, Any]:
    """Ejecuta el pipeline ETL completo con validación Bronze e idempotencia.

    Args:
        cfg: Instancia opcional de ConfiguracionETL ya construida.
        ruta_config: Ruta opcional al archivo JSON de configuración.

    Returns:
        Diccionario con la configuración, marcas de tiempo y auditoría.

    """
    if cfg is None:
        cfg = cargar_configuracion(ruta_config=ruta_config)

    cfg.asegurar_directorios()
    for ext in ("csv", "parquet"):
        legado = cfg.gold_dir / f"agg_satisfaccion_evento.{ext}"
        if legado.exists():
            legado.unlink()

    ts_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_id = f"ETL-ACTHO360-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    bitacora = BitacoraAuditoria(run_id=run_id, fecha_corte=cfg.fecha_corte)

    bronze, df_hashes_bronze = ingerir_y_validar_bronze(cfg)
    silver = procesar_capa_silver(bronze, cfg, bitacora)

    agg_part = construir_agg_participacion_empresa(silver, cfg, bitacora)
    construir_agg_satisfaccion_encuestas(
        silver["fact_encuestas_satisfaccion"], cfg, bitacora
    )
    construir_agg_retencion_empresa(bronze, silver, agg_part, cfg, bitacora)

    df_audit_dup = construir_audit_duplicados(
        bronze["registros_duplicados"], cfg, bitacora
    )
    df_calidad, reconciliacion, df_cargas = persistir_auditoria_final(
        bronze, silver, df_audit_dup, cfg, bitacora
    )

    return {
        "config": cfg,
        "inicio": ts_inicio,
        "fin": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hashes_bronze": df_hashes_bronze,
        "reconciliacion": reconciliacion,
        "calidad": df_calidad,
        "cargas": df_cargas,
    }


__all__ = [
    "ConfiguracionETL",
    "calcular_sha256_archivo",
    "cargar_configuracion",
    "construir_dim_empresas_scd2",
    "ejecutar_pipeline_completo",
    "guardar_tabla_medallion",
    "homologar_kam_id",
    "ingerir_y_validar_bronze",
]


if __name__ == "__main__":
    resultado = ejecutar_pipeline_completo()
    logger.info("Pipeline ETL Medallion ACTHO 360 (v2.0) completado exitosamente.")
