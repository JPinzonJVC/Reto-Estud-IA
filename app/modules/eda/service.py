"""Servicio de negocio para orquestar ejecuciones del pipeline ETL desde la API."""

import logging
import threading
from datetime import datetime
from typing import Any

import pandas as pd
from fastapi import BackgroundTasks

from app.modules.eda.config import ConfiguracionETL, cargar_configuracion
from app.modules.eda.pipeline import ejecutar_pipeline_completo
from app.modules.eda.schemas import (
    EtlRunAcceptedResponse,
    EtlRunRequest,
    EtlRunSummary,
)

logger = logging.getLogger(__name__)


class EtlAlreadyRunningError(RuntimeError):
    """Se lanza cuando ya existe una ejecución ETL en curso."""


class EtlInputNotFoundError(FileNotFoundError):
    """Se lanza cuando el directorio de fuentes normalizadas no existe."""


class EtlRunNotFoundError(LookupError):
    """Se lanza cuando no existe una ejecución ETL con el run_id solicitado."""


class EtlService:
    """Gestiona la ejecución en segundo plano y consulta de estado del pipeline ETL."""

    def __init__(self) -> None:
        """Inicializa el servicio con bloqueo de concurrencia y registro en memoria."""
        self._lock = threading.Lock()
        self._runs: dict[str, EtlRunSummary] = {}

    def _construir_configuracion(self, fecha_corte: str | None) -> ConfiguracionETL:
        """Carga la configuración base y aplica la fecha de corte si fue enviada."""
        cfg = cargar_configuracion()
        if fecha_corte is None:
            return cfg
        params = {**cfg.parametros_temporales, "fecha_corte": fecha_corte}
        return cfg.model_copy(update={"parametros_temporales": params})

    def iniciar_ejecucion(
        self,
        request: EtlRunRequest,
        background_tasks: BackgroundTasks,
    ) -> EtlRunAcceptedResponse:
        """Valida precondiciones y encola el pipeline ETL en segundo plano.

        Args:
            request: Parámetros de ejecución recibidos en la petición HTTP.
            background_tasks: Gestor de tareas en segundo plano de FastAPI.

        Returns:
            Confirmación con el run_id asignado y estado EN_PROGRESO.

        Raises:
            EtlAlreadyRunningError: Si ya hay una ejecución activa.
            EtlInputNotFoundError: Si no existe el directorio de entrada normalizado.

        """
        if not self._lock.acquire(blocking=False):  # pylint: disable=consider-using-with
            raise EtlAlreadyRunningError(
                "Ya existe una ejecución del pipeline ETL en progreso."
            )

        try:
            cfg = self._construir_configuracion(request.fecha_corte)
            has_norm = cfg.origen_normalizados_dir.exists()
            has_raw = (
                cfg.origen_raw_csv_dir is not None and cfg.origen_raw_csv_dir.exists()
            )
            if not has_norm and not has_raw:
                raise EtlInputNotFoundError(
                    f"No existe el directorio de fuentes: {cfg.origen_normalizados_dir}"
                )

            ahora = datetime.now()
            run_id = f"ETL-ACTHO360-{ahora.strftime('%Y%m%d-%H%M%S')}"
            self._runs[run_id] = EtlRunSummary(
                id_ejecucion=run_id,
                fecha_inicio=ahora.strftime("%Y-%m-%d %H:%M:%S"),
                estado_ejecucion="EN_PROGRESO",
            )
            background_tasks.add_task(
                self._ejecutar_en_segundo_plano,
                run_id,
                cfg,
                request.persistir_en_db,
            )
        except Exception:
            self._lock.release()
            raise

        return EtlRunAcceptedResponse(
            run_id=run_id,
            estado_ejecucion="EN_PROGRESO",
            mensaje="Ejecución del pipeline ETL iniciada en segundo plano.",
        )

    def _ejecutar_en_segundo_plano(
        self,
        run_id: str,
        cfg: ConfiguracionETL,
        persistir_en_db: bool,
    ) -> None:
        """Ejecuta el pipeline completo y actualiza el resumen de estado."""
        try:
            resultado = ejecutar_pipeline_completo(
                cfg=cfg,
                persistir_en_db=persistir_en_db,
                run_id=run_id,
            )
            self._runs[run_id] = self._resumen_desde_resultado(resultado)
        except Exception as exc:
            logger.exception("Error ejecutando pipeline ETL %s", run_id)
            previo = self._runs.get(run_id)
            self._runs[run_id] = EtlRunSummary(
                id_ejecucion=run_id,
                fecha_inicio=(
                    previo.fecha_inicio
                    if previo is not None
                    else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ),
                fecha_finalizacion=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                errores=str(exc),
                estado_ejecucion="FALLIDO",
            )
        finally:
            if self._lock.locked():
                self._lock.release()

    @staticmethod
    def _resumen_desde_resultado(resultado: dict[str, Any]) -> EtlRunSummary:
        """Convierte el diccionario retornado por el pipeline a EtlRunSummary."""
        df_ejec: pd.DataFrame = resultado["ejecucion"]
        fila = df_ejec.iloc[0].to_dict()
        return EtlRunSummary(
            id_ejecucion=str(fila["id_ejecucion"]),
            fecha_inicio=str(fila["fecha_inicio"]),
            fecha_finalizacion=str(fila["fecha_finalizacion"]),
            archivos_procesados=int(fila["archivos_procesados"]),
            registros_leidos=int(fila["registros_leidos"]),
            registros_cargados=int(fila["registros_cargados"]),
            registros_rechazados=int(fila["registros_rechazados"]),
            duplicados_identificados=int(fila["duplicados_identificados"]),
            errores=str(fila["errores"]),
            estado_ejecucion=str(fila["estado_ejecucion"]),
            conteos_db={
                str(k): int(v) for k, v in resultado.get("conteos_db", {}).items()
            },
        )

    def _leer_historial_auditoria(self) -> dict[str, EtlRunSummary]:
        """Lee ejecuciones previas persistidas en audit_ejecuciones_etl.csv."""
        cfg = cargar_configuracion()
        ruta_audit = cfg.audit_dir / "audit_ejecuciones_etl.csv"
        if not ruta_audit.exists():
            return {}

        df = pd.read_csv(ruta_audit)
        historial: dict[str, EtlRunSummary] = {}
        for fila in df.to_dict(orient="records"):
            run_id = str(fila["id_ejecucion"])
            historial[run_id] = EtlRunSummary(
                id_ejecucion=run_id,
                fecha_inicio=str(fila["fecha_inicio"]),
                fecha_finalizacion=(
                    str(fila["fecha_finalizacion"])
                    if pd.notna(fila.get("fecha_finalizacion"))
                    else None
                ),
                archivos_procesados=int(fila.get("archivos_procesados", 0)),
                registros_leidos=int(fila.get("registros_leidos", 0)),
                registros_cargados=int(fila.get("registros_cargados", 0)),
                registros_rechazados=int(fila.get("registros_rechazados", 0)),
                duplicados_identificados=int(fila.get("duplicados_identificados", 0)),
                errores=str(fila.get("errores", "NINGUNO")),
                estado_ejecucion=str(fila.get("estado_ejecucion", "DESCONOCIDO")),
            )
        return historial

    def listar_ejecuciones(self) -> list[EtlRunSummary]:
        """Retorna las ejecuciones registradas de la más reciente a la antigua."""
        combinado = self._leer_historial_auditoria()
        combinado.update(self._runs)
        return sorted(
            combinado.values(),
            key=lambda item: item.fecha_inicio,
            reverse=True,
        )

    def obtener_ejecucion(self, run_id: str) -> EtlRunSummary:
        """Retorna el estado y métricas de una ejecución específica por run_id."""
        if run_id in self._runs:
            return self._runs[run_id]
        historial = self._leer_historial_auditoria()
        if run_id in historial:
            return historial[run_id]
        raise EtlRunNotFoundError(f"No se encontró la ejecución ETL '{run_id}'.")
