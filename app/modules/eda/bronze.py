"""Módulo de ingesta, persistencia Parquet/CSV y validación SHA-256 para capa Bronze."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.modules.eda.config import ConfiguracionETL

ARCHIVOS_REQUERIDOS_ORIGEN: tuple[str, ...] = (
    "dim_empresas",
    "dim_personas",
    "dim_eventos",
    "dim_kams",
    "fact_asistencias",
    "fact_encuestas_satisfaccion",
    "fact_movimientos_crm",
)


def calcular_sha256_archivo(ruta: Path) -> str:
    """Calcula el hash SHA-256 de un archivo para verificar integridad e inmutabilidad.

    Args:
        ruta: Ruta del archivo a procesar.

    Returns:
        Cadena hexadecimal con el digest SHA-256.

    """
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(65536), b""):
            digest.update(bloque)
    return digest.hexdigest()


def guardar_tabla_medallion(
    df: pd.DataFrame,
    carpeta: Path,
    nombre_base: str,
    registro_errores: list[dict[str, Any]] | None = None,
) -> tuple[Path, Path]:
    """Persiste un DataFrame en CSV y Apache Parquet validando errores explícitamente.

    Args:
        df: DataFrame de Pandas a persistir.
        carpeta: Directorio destino de la capa Medallion.
        nombre_base: Nombre base del archivo sin extensión.
        registro_errores: Lista opcional donde registrar errores de escritura.

    Returns:
        Tupla con las rutas del archivo CSV y del archivo Parquet generados.

    Raises:
        RuntimeError: Si ocurre un fallo al escribir el archivo Parquet o CSV.

    """
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_csv = carpeta / f"{nombre_base}.csv"
    ruta_parquet = carpeta / f"{nombre_base}.parquet"

    df.to_csv(ruta_csv, index=False, encoding="utf-8-sig")
    try:
        df.to_parquet(ruta_parquet, index=False)
    except Exception as exc:
        if registro_errores is not None:
            registro_errores.append(
                {
                    "tabla": nombre_base,
                    "carpeta": str(carpeta),
                    "error": str(exc),
                }
            )
        raise RuntimeError(
            f"Error al generar archivo Parquet para '{nombre_base}' "
            f"en '{carpeta}': {exc}"
        ) from exc

    if not ruta_csv.exists() or not ruta_parquet.exists():
        raise RuntimeError(
            f"Fallo de persistencia en '{nombre_base}': CSV o Parquet no generado."
        )
    return ruta_csv, ruta_parquet


def _sincronizar_archivo_bronze(
    ruta_src: Path,
    ruta_dst: Path,
    nombre: str,
    *,
    permitir_actualizacion: bool = False,
    run_id: str | None = None,
) -> str:
    """Sincroniza un archivo hacia Bronze verificando su hash SHA-256.

    Args:
        ruta_src: Ruta del archivo fuente normalizado.
        ruta_dst: Ruta destino en la capa Bronze.
        nombre: Nombre lógico de la tabla fuente.
        permitir_actualizacion: Si es True, respalda en bronze/historial y actualiza.
        run_id: Identificador de corrida para etiquetar el respaldo histórico.

    Returns:
        Acción aplicada sobre el archivo en Bronze.

    Raises:
        RuntimeError: Si el archivo existente en Bronze difiere de la fuente y
            permitir_actualizacion es False.

    """
    hash_src = calcular_sha256_archivo(ruta_src)
    if ruta_dst.exists():
        hash_dst = calcular_sha256_archivo(ruta_dst)
        if hash_dst == hash_src:
            return "CONSERVADO_SIN_SOBRESCRIBIR_HASH_IDENTICO"
        if permitir_actualizacion:
            hist_dir = ruta_dst.parent / "historial"
            hist_dir.mkdir(parents=True, exist_ok=True)
            tag = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
            respaldo = hist_dir / f"{tag}_{ruta_dst.name}"
            respaldo.write_bytes(ruta_dst.read_bytes())
            ruta_dst.write_bytes(ruta_src.read_bytes())
            return "ACTUALIZADO_NUEVA_VERSION_VERIFICADA"
        raise RuntimeError(
            f"Conflicto de integridad en Bronze para '{nombre}.csv': "
            f"el archivo existente en Bronze ({hash_dst[:12]}) difiere de "
            f"la fuente ({hash_src[:12]}). No se sobrescribe silenciosamente."
        )
    ruta_dst.write_bytes(ruta_src.read_bytes())
    return "COPIADO_INICIAL_VERIFICADO"


def ingerir_y_validar_bronze(
    cfg: ConfiguracionETL,
    run_id: str | None = None,
    ts_ingesta: str | None = None,
    *,
    permitir_actualizacion_bronze: bool = False,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Valida existencia e integridad de las 7 fuentes y registra SHA-256 en Bronze.

    Args:
        cfg: Configuración del pipeline ETL Medallion.
        run_id: Identificador de la ejecución ETL actual.
        ts_ingesta: Fecha y hora ISO de la ingesta en Bronze.

    Returns:
        Tupla con el diccionario de DataFrames leídos y el DataFrame de hashes.

    Raises:
        FileNotFoundError: Si algún archivo fuente obligatorio no existe.
        ValueError: Si algún archivo fuente está vacío (0 bytes).

    """
    cfg.asegurar_directorios()
    legado_dup = cfg.bronze_dir / "registros_duplicados.csv"
    if legado_dup.exists():
        legado_dup.unlink()

    id_ejec = run_id or f"ETL-ACTHO360-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    fecha_ingesta = ts_ingesta or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    mapa_origen: dict[str, Path] = {
        nombre: cfg.origen_normalizados_dir / f"{nombre}.csv"
        for nombre in ARCHIVOS_REQUERIDOS_ORIGEN
    }
    if any(not ruta.exists() for ruta in mapa_origen.values()):
        if cfg.origen_raw_csv_dir is not None and cfg.origen_raw_csv_dir.exists():
            # pylint: disable=import-outside-toplevel
            from app.modules.eda.raw_builder import construir_normalizados_desde_raw

            construir_normalizados_desde_raw(cfg)

    bronze_dfs: dict[str, pd.DataFrame] = {}
    hashes_rows: list[dict[str, Any]] = []

    for nombre, ruta_src in mapa_origen.items():
        if not ruta_src.exists():
            raise FileNotFoundError(f"Fuente obligatoria no encontrada: {ruta_src}")
        tamano_bytes = ruta_src.stat().st_size
        if tamano_bytes == 0:
            raise ValueError(f"Fuente obligatoria vacía (0 bytes): {ruta_src}")

        ruta_dst = cfg.bronze_dir / f"{nombre}.csv"
        accion_bronze = _sincronizar_archivo_bronze(
            ruta_src,
            ruta_dst,
            nombre,
            permitir_actualizacion=permitir_actualizacion_bronze,
            run_id=id_ejec,
        )
        df_leido = pd.read_csv(ruta_dst, keep_default_na=True)
        bronze_dfs[nombre] = df_leido
        hashes_rows.append(
            {
                "id_ejecucion": id_ejec,
                "fecha_hora_ingesta": fecha_ingesta,
                "tabla_fuente": nombre,
                "archivo_nombre": ruta_src.name,
                "bytes_origen": int(tamano_bytes),
                "filas_leidas": int(len(df_leido)),
                "columnas_leidas": int(df_leido.shape[1]),
                "sha256_origen": calcular_sha256_archivo(ruta_src),
                "sha256_bronze": calcular_sha256_archivo(ruta_dst),
                "integridad_verificada": True,
                "accion_bronze": accion_bronze,
            }
        )

    df_hashes = pd.DataFrame(hashes_rows)
    guardar_tabla_medallion(df_hashes, cfg.audit_dir, "audit_hashes_fuentes_bronze")
    if cfg.origen_raw_csv_dir is not None and cfg.origen_raw_csv_dir.exists():
        ingerir_fuentes_crudas_bronze(cfg, run_id=id_ejec, ts_ingesta=fecha_ingesta)
    return bronze_dfs, df_hashes


def ingerir_fuentes_crudas_bronze(
    cfg: ConfiguracionETL,
    run_id: str | None = None,
    ts_ingesta: str | None = None,
) -> pd.DataFrame:
    """Ingesta en crudo los CSV originales de input/CSV hacia Bronze con SHA-256.

    Args:
        cfg: Configuración del pipeline ETL Medallion.
        run_id: Identificador de la ejecución ETL actual.
        ts_ingesta: Fecha y hora ISO de la ingesta en Bronze.

    Returns:
        DataFrame con el registro de hashes SHA-256 de los archivos crudos.

    """
    if cfg.origen_raw_csv_dir is None or not cfg.origen_raw_csv_dir.exists():
        return pd.DataFrame()

    id_ejec = run_id or f"ETL-ACTHO360-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    fecha_ingesta = ts_ingesta or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    archivos_raw = sorted(cfg.origen_raw_csv_dir.rglob("*.csv"))
    if not archivos_raw:
        return pd.DataFrame()

    registros: list[dict[str, Any]] = []
    for ruta_src in archivos_raw:
        rel_path = ruta_src.relative_to(cfg.origen_raw_csv_dir)
        ruta_dst = cfg.bronze_raw_dir / rel_path
        ruta_dst.parent.mkdir(parents=True, exist_ok=True)
        accion = _sincronizar_archivo_bronze(ruta_src, ruta_dst, str(rel_path))
        registros.append(
            {
                "id_ejecucion": id_ejec,
                "fecha_hora_ingesta": fecha_ingesta,
                "archivo_relativo": rel_path.as_posix(),
                "bytes_origen": int(ruta_src.stat().st_size),
                "sha256_origen": calcular_sha256_archivo(ruta_src),
                "sha256_bronze": calcular_sha256_archivo(ruta_dst),
                "integridad_verificada": True,
                "accion_bronze": accion,
            }
        )

    df_raw_hashes = pd.DataFrame(registros)
    guardar_tabla_medallion(
        df_raw_hashes, cfg.audit_dir, "audit_hashes_fuentes_bronze_raw"
    )
    return df_raw_hashes


def homologar_kam_id(valor: Any, cfg: ConfiguracionETL) -> str:
    """Homologa valores de KAM sin asignar al identificador canónico configurado.

    Args:
        valor: Valor original del identificador KAM.
        cfg: Configuración del pipeline ETL Medallion.

    Returns:
        Identificador KAM homologado (NOT NULL).

    """
    if pd.isna(valor):
        return cfg.kam_sin_asignar_id
    texto = str(valor).strip()
    if texto in cfg.valores_origen_sin_asignar:
        return cfg.kam_sin_asignar_id
    return texto


def homologar_kam_opcional(valor: Any, cfg: ConfiguracionETL) -> str | None:
    """Retorna el kam_id asignado real o None si el registro no tiene KAM asignado.

    Args:
        valor: Valor original del identificador KAM en la fuente.
        cfg: Configuración del pipeline ETL Medallion.

    Returns:
        Identificador KAM asignado o None cuando está vacío o sin asignar.

    """
    if pd.isna(valor):
        return None
    texto = str(valor).strip()
    if not texto or texto in cfg.valores_origen_sin_asignar:
        return None
    return texto
