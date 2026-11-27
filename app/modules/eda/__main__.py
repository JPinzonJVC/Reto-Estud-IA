"""Punto de entrada ejecutable para el pipeline ETL (python -m app.modules.eda)."""

import logging

from app.database import ping_database
from app.modules.eda.pipeline import ejecutar_pipeline_completo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

if __name__ == "__main__":
    res = ejecutar_pipeline_completo(persistir_en_db=ping_database())
    logging.getLogger(__name__).info(
        "ETL DWH completado (%s) | Tablas DB cargadas: %d",
        res["run_id"],
        len(res["conteos_db"]),
    )
