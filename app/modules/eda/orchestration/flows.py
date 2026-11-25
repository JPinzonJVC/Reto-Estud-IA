"""Flujos y tareas de Prefect para automatizar el pipeline EDA Medallion."""

import logging
from pathlib import Path
import shutil
from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy.engine import Engine

from app.database import get_engine
from app.env_vars import OrchestrationEnvs
from app.modules.eda.bronze import ARCHIVOS_REQUERIDOS_ORIGEN
from app.modules.eda.config import cargar_configuracion
from app.modules.eda.extractors import (
    ExtractionResult,
    GoogleDriveExtractor,
    ZohoCRMExtractor,
    get_watermark,
    upsert_watermark,
)
from app.modules.eda.pipeline import ejecutar_pipeline_completo

logger = logging.getLogger(__name__)

_F = TypeVar("_F", bound=Callable[..., Any])

try:
    from prefect import flow, task  # type: ignore[import-not-found]
    from prefect.cache_policies import NO_CACHE  # type: ignore[import-not-found]
    from prefect.schedules import Cron  # type: ignore[import-not-found]

    PREFECT_AVAILABLE = True
except ImportError:  # pragma: no cover - fallback para entornos sin prefect instalado
    PREFECT_AVAILABLE = False
    NO_CACHE = None

    def flow(*_args: Any, **_kwargs: Any) -> Callable[[_F], _F]:
        """Decorador fallback cuando prefect no está instalado.

        Args:
            *_args: Argumentos posicionales ignorados del decorador.
            **_kwargs: Argumentos nombrados ignorados del decorador.

        Returns:
            Función decoradora que retorna la función original sin cambios.

        Raises:
            None.

        """

        def _decorator(func: _F) -> _F:
            """Retorna la función decorada sin alteraciones.

            Args:
                func: Función objetivo del flujo.

            Returns:
                La misma función recibida.

            Raises:
                None.

            """
            return func

        return _decorator

    def task(*_args: Any, **_kwargs: Any) -> Callable[[_F], _F]:
        """Decorador fallback cuando prefect no está instalado.

        Args:
            *_args: Argumentos posicionales ignorados del decorador.
            **_kwargs: Argumentos nombrados ignorados del decorador.

        Returns:
            Función decoradora que retorna la función original sin cambios.

        Raises:
            None.

        """

        def _decorator(func: _F) -> _F:
            """Retorna la función decorada sin alteraciones.

            Args:
                func: Función objetivo de la tarea.

            Returns:
                La misma función recibida.

            Raises:
                None.

            """
            return func

        return _decorator


@task(
    name="extract-google-drive",
    retries=3,
    retry_delay_seconds=60,
    cache_policy=NO_CACHE,
)
def extract_google_drive_task(
    *,
    engine: Engine,
    force: bool = False,
    extractor: GoogleDriveExtractor | None = None,
) -> ExtractionResult:
    """Extrae archivos Excel/CSV desde Google Drive y actualiza su watermark.

    Args:
        engine: Motor SQLAlchemy conectado a PostgreSQL.
        force: Si es True, fuerza descarga aunque el cursor no haya cambiado.
        extractor: Instancia opcional de GoogleDriveExtractor para inyección/pruebas.

    Returns:
        Resultado estandarizado de la extracción de Google Drive.

    Raises:
        ValueError: Si faltan parámetros obligatorios estando GDRIVE_ENABLED=true.
        FileNotFoundError: Si no existe el archivo de credenciales Service Account.
        Exception: Si falla la comunicación con Google Drive API.

    """
    drive_extractor = extractor or GoogleDriveExtractor()
    source_name = drive_extractor.config.source_name
    watermark = get_watermark(engine, source_name)
    last_cursor = watermark.last_cursor if watermark else None

    try:
        result = drive_extractor.extract(last_cursor=last_cursor, force=force)
        if result.files_written:
            _sincronizar_insumos_normalizados(result.files_written)
        status = "SUCCESS" if result.has_changes else "SKIPPED"
        upsert_watermark(
            engine,
            source_name=source_name,
            last_status=status,
            last_cursor=result.new_cursor,
            records_extracted=result.records_extracted,
            details=result.skipped_reason,
        )
        return result
    except Exception as exc:
        upsert_watermark(
            engine,
            source_name=source_name,
            last_status="FAILED",
            details=str(exc),
        )
        raise


@task(
    name="extract-zoho-crm",
    retries=3,
    retry_delay_seconds=120,
    cache_policy=NO_CACHE,
)
def extract_zoho_crm_task(
    *,
    engine: Engine,
    force: bool = False,
    extractor: ZohoCRMExtractor | None = None,
) -> ExtractionResult:
    """Extrae registros incrementales desde Zoho CRM y actualiza su watermark.

    Args:
        engine: Motor SQLAlchemy conectado a PostgreSQL.
        force: Si es True, ignora el watermark previo y descarga todo el módulo.
        extractor: Instancia opcional de ZohoCRMExtractor para inyección/pruebas.

    Returns:
        Resultado estandarizado de la extracción de Zoho CRM.

    Raises:
        ValueError: Si faltan credenciales OAuth2 estando ZOHO_ENABLED=true.
        Exception: Si falla la petición HTTP hacia Zoho CRM.

    """
    zoho_extractor = extractor or ZohoCRMExtractor()
    source_name = zoho_extractor.config.source_name
    watermark = get_watermark(engine, source_name)
    last_sync_at = watermark.last_sync_at if watermark else None

    try:
        result = zoho_extractor.extract(last_sync_at=last_sync_at, force=force)
        status = "SUCCESS" if result.has_changes else "SKIPPED"
        upsert_watermark(
            engine,
            source_name=source_name,
            last_status=status,
            last_sync_at=result.new_cursor if result.enabled else None,
            last_cursor=result.new_cursor,
            records_extracted=result.records_extracted,
            details=result.skipped_reason,
        )
        return result
    except Exception as exc:
        upsert_watermark(
            engine,
            source_name=source_name,
            last_status="FAILED",
            details=str(exc),
        )
        raise


def _sincronizar_insumos_normalizados(files_written: list[Path]) -> list[Path]:
    """Copia los CSV extraídos de Drive hacia input/normalizados cuando coinciden con Bronze.

    Args:
        files_written: Lista de rutas generadas por el extractor de Google Drive.

    Returns:
        Lista de rutas CSV sincronizadas dentro del directorio normalizados/duplicados.

    Raises:
        OSError: Si ocurre un error de permisos o escritura al copiar archivos.

    """
    cfg = cargar_configuracion()
    cfg.asegurar_directorios()
    requeridos = set(ARCHIVOS_REQUERIDOS_ORIGEN)
    duplicados_nombres = {"registros_duplicados", "duplicados_afiliados_crm"}
    sincronizados: list[Path] = []

    for path in files_written:
        if path.suffix.lower() != ".csv" or not path.exists():
            continue
        base_name = path.stem.split("__")[0].strip()
        sheet_part = path.stem.split("__")[-1].strip()

        for candidate in (base_name, sheet_part):
            if candidate in requeridos:
                dst = cfg.origen_normalizados_dir / f"{candidate}.csv"
                shutil.copy2(path, dst)
                sincronizados.append(dst)
                break
            if candidate in duplicados_nombres:
                dst = cfg.origen_duplicados_dir / f"{candidate}.csv"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dst)
                sincronizados.append(dst)
                break

    return sincronizados


@task(
    name="run-medallion-etl",
    retries=1,
    retry_delay_seconds=30,
    cache_policy=NO_CACHE,
)
def run_medallion_etl_task(*, engine: Engine) -> dict[str, Any]:
    """Ejecuta el pipeline Medallion completo persistiendo en PostgreSQL.

    Args:
        engine: Motor SQLAlchemy conectado a PostgreSQL.

    Returns:
        Diccionario con resumen de ejecución, tablas y errores del pipeline.

    Raises:
        Exception: Si ocurre un error crítico en Bronze, Silver, Gold o carga DB.

    """
    return ejecutar_pipeline_completo(
        persistir_en_db=True,
        db_engine=engine,
        permitir_actualizacion_bronze=True,
    )


@task(
    name="cleanup-staging-raw",
    cache_policy=NO_CACHE,
)
def cleanup_staging_raw_task(*, files_to_delete: list[Path]) -> int:
    """Elimina archivos temporales descargados en raw_drive/raw_zoho tras carga exitosa.

    Args:
        files_to_delete: Rutas de archivos temporales generados por Drive y Zoho.

    Returns:
        Cantidad total de archivos temporales eliminados.

    Raises:
        None.

    """
    deleted = 0
    parent_dirs: set[Path] = set()
    for path in files_to_delete:
        if path.name == ".gitkeep":
            continue
        try:
            if path.exists() and path.is_file():
                path.unlink()
                deleted += 1
                parent_dirs.add(path.parent)
        except OSError as exc:
            logger.warning("No se pudo eliminar archivo temporal %s: %s", path, exc)

    # Limpiar subcarpetas vacías creadas durante descargas recursivas
    for directory in sorted(parent_dirs, key=lambda p: len(p.parts), reverse=True):
        try:
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()
        except OSError:
            continue

    logger.info("Limpieza de staging temporal completada: %d archivo(s) eliminados.", deleted)
    return deleted


@flow(name="eda-medallion-weekly-pipeline", log_prints=True)
def eda_medallion_flow(
    *,
    force_reprocess: bool | None = None,
    cleanup_raw_after_load: bool | None = None,
    engine: Engine | None = None,
    drive_extractor: GoogleDriveExtractor | None = None,
    zoho_extractor: ZohoCRMExtractor | None = None,
) -> dict[str, Any]:
    """Orquesta extracción (Drive + Zoho), Medallion ETL y limpieza de staging temporal.

    Args:
        force_reprocess: Sobreescribe EDA_FORCE_REPROCESS para forzar el ETL.
        cleanup_raw_after_load: Sobreescribe EDA_CLEANUP_RAW_AFTER_LOAD para borrar temporales.
        engine: Motor SQLAlchemy opcional; si es None usa el singleton de app.database.
        drive_extractor: Extractor de Google Drive opcional para pruebas.
        zoho_extractor: Extractor de Zoho CRM opcional para pruebas.

    Returns:
        Diccionario con estado final ('SKIPPED_NO_CHANGES' o 'COMPLETED') y detalle.

    Raises:
        Exception: Si falla alguna de las tareas de extracción o el pipeline Medallion.

    """
    settings = OrchestrationEnvs()
    effective_force = (
        settings.force_reprocess if force_reprocess is None else force_reprocess
    )
    effective_cleanup = (
        settings.cleanup_raw_after_load
        if cleanup_raw_after_load is None
        else cleanup_raw_after_load
    )
    db_engine = engine or get_engine()

    drive_result = extract_google_drive_task(
        engine=db_engine,
        force=effective_force,
        extractor=drive_extractor,
    )
    zoho_result = extract_zoho_crm_task(
        engine=db_engine,
        force=effective_force,
        extractor=zoho_extractor,
    )

    should_run_medallion = (
        effective_force or drive_result.has_changes or zoho_result.has_changes
    )

    if not should_run_medallion:
        logger.info(
            "Sin cambios en Drive ni Zoho CRM; se omite ejecución del Medallion ETL."
        )
        return {
            "status": "SKIPPED_NO_CHANGES",
            "drive": drive_result.model_dump(mode="json"),
            "zoho": zoho_result.model_dump(mode="json"),
            "pipeline_run_id": None,
            "staging_cleaned_files": 0,
        }

    etl_result = run_medallion_etl_task(engine=db_engine)
    pipeline_errors = etl_result.get("errores", [])
    cleaned_files = 0
    if effective_cleanup and not pipeline_errors:
        staging_files = [*drive_result.files_written, *zoho_result.files_written]
        if staging_files:
            cleaned_files = cleanup_staging_raw_task(files_to_delete=staging_files)

    return {
        "status": "COMPLETED",
        "drive": drive_result.model_dump(mode="json"),
        "zoho": zoho_result.model_dump(mode="json"),
        "pipeline_run_id": etl_result.get("run_id"),
        "pipeline_errors": pipeline_errors,
        "staging_cleaned_files": cleaned_files,
    }


def serve_eda_pipeline() -> None:
    """Registra y sirve el deployment semanal configurable por variables de entorno.

    Args:
        None.

    Returns:
        None.

    Raises:
        ImportError: Si Prefect no está instalado en el entorno actual.

    """
    if not PREFECT_AVAILABLE:
        raise ImportError(
            "Prefect no está instalado. Instala las dependencias con 'pip install -r requirements.txt'."
        )

    settings = OrchestrationEnvs()
    logger.info(
        "Iniciando Prefect serve '%s' con cron='%s' (timezone='%s').",
        settings.deployment_name,
        settings.schedule_cron,
        settings.schedule_timezone,
    )
    schedule = Cron(
        settings.schedule_cron,
        timezone=settings.schedule_timezone,
    )
    eda_medallion_flow.serve(  # type: ignore[attr-defined]
        name=settings.deployment_name,
        schedules=[schedule],
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    serve_eda_pipeline()
