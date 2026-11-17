"""Módulo de configuración portable para el pipeline ETL Medallion ACTHO 360."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MODULE_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT_DEFAULT: Path = MODULE_DIR.parents[2]
CONFIG_FILE_DEFAULT: Path = MODULE_DIR / "etl_config.json"

REGLAS_SEMAFORO_DEFAULT: dict[str, Any] = {
    "tipo_metodologia": "REGLA_HEURISTICA_NEGOCIO_NO_PREDICTIVA",
    "umbrales": {
        "dias_vencimiento_inmediato": 30,
        "dias_vencimiento_medio": 60,
        "dias_vencimiento_proximo": 90,
        "min_eventos_participacion_activa": 1,
        "satisfaccion_detractor_max_1_5": 3.75,
        "max_personas_monocontacto": 1,
        "puntaje_minimo_rojo_alto": 4,
        "puntaje_minimo_amarillo_medio": 2,
    },
    "pesos": {
        "membresia_vencida": 2,
        "proximo_vencimiento_90d": 2,
        "baja_participacion_cero_eventos": 2,
        "baja_satisfaccion_menor_3_75": 2,
        "monocontacto_una_persona": 1,
    },
}


@dataclass(frozen=True)
class ConfiguracionETL:
    """Configuración inmutable de directorios, parámetros temporales y reglas.

    Attributes:
        origen_normalizados_dir: Directorio con los archivos CSV normalizados.
        origen_duplicados_dir: Directorio con los archivos de duplicados.
        salida_root_dir: Directorio raíz de salida para capas Medallion (input).
        parametros_temporales: Parámetros de fecha de corte, trimestres y ventanas.
        homologacion_kam: Parámetros para homologación de KAM sin asignar.
        reglas_semaforo: Umbrales y pesos del semáforo heurístico de riesgo.

    """

    origen_normalizados_dir: Path
    origen_duplicados_dir: Path
    salida_root_dir: Path
    parametros_temporales: dict[str, Any] = field(default_factory=dict)
    homologacion_kam: dict[str, Any] = field(default_factory=dict)
    reglas_semaforo: dict[str, Any] = field(default_factory=dict)

    @property
    def fecha_corte(self) -> str:
        """Retorna la fecha de corte de referencia del modelo."""
        return str(self.parametros_temporales.get("fecha_corte", "2026-11-13"))

    @property
    def anio_analisis(self) -> int:
        """Retorna el año de análisis configurado."""
        return int(self.parametros_temporales.get("anio_analisis", 2026))

    @property
    def trimestre_calendario_etiqueta(self) -> str:
        """Retorna la etiqueta del trimestre calendario."""
        return str(
            self.parametros_temporales.get("trimestre_calendario_etiqueta", "2026-Q3")
        )

    @property
    def trimestre_calendario_meses(self) -> tuple[str, ...]:
        """Retorna los meses ISO del trimestre calendario."""
        meses = self.parametros_temporales.get(
            "trimestre_calendario_meses", ["2026-07", "2026-08", "2026-09"]
        )
        return tuple(str(m) for m in meses)

    @property
    def trimestre_operativo_etiqueta(self) -> str:
        """Retorna la etiqueta del trimestre operativo."""
        return str(
            self.parametros_temporales.get(
                "trimestre_operativo_etiqueta", "2026-T3-OPERATIVO (AGO-OCT)"
            )
        )

    @property
    def trimestre_operativo_meses(self) -> tuple[str, ...]:
        """Retorna los meses ISO del trimestre operativo."""
        meses = self.parametros_temporales.get(
            "trimestre_operativo_meses", ["2026-08", "2026-09", "2026-10"]
        )
        return tuple(str(m) for m in meses)

    @property
    def ventana_movil_dias(self) -> int:
        """Retorna la cantidad de días de la ventana móvil."""
        return int(self.parametros_temporales.get("ventana_movil_dias", 90))

    @property
    def dias_por_mes_estandar(self) -> float:
        """Retorna el factor estándar de días por mes."""
        return float(self.parametros_temporales.get("dias_por_mes_estandar", 30.4375))

    @property
    def kam_sin_asignar_id(self) -> str:
        """Retorna el identificador canónico para KAM sin asignar."""
        return str(
            self.homologacion_kam.get(
                "identificador_canonico_sin_asignar", "KAM-UNASSIGNED"
            )
        )

    @property
    def valores_origen_sin_asignar(self) -> tuple[str, ...]:
        """Retorna la tupla de valores de origen que representan KAM sin asignar."""
        valores = self.homologacion_kam.get(
            "valores_origen_sin_asignar",
            ["", "Sin asignar", "Sin asignar (cuenta ACTHO)", "KAM-UNASSIGNED"],
        )
        return tuple(str(v) for v in valores)

    @property
    def bronze_dir(self) -> Path:
        """Retorna el directorio de la capa Bronze."""
        return self.salida_root_dir / "bronze"

    @property
    def silver_dir(self) -> Path:
        """Retorna el directorio de la capa Silver."""
        return self.salida_root_dir / "silver"

    @property
    def gold_dir(self) -> Path:
        """Retorna el directorio de la capa Gold."""
        return self.salida_root_dir / "gold"

    @property
    def audit_dir(self) -> Path:
        """Retorna el directorio de la capa de Auditoría."""
        return self.salida_root_dir / "audit"

    @property
    def docs_dir(self) -> Path:
        """Retorna el directorio de documentación."""
        return PROJECT_ROOT_DEFAULT / "docs"

    def asegurar_directorios(self) -> None:
        """Crea los directorios de las capas Medallion si no existen."""
        for directorio in (
            self.bronze_dir,
            self.silver_dir,
            self.gold_dir,
            self.audit_dir,
        ):
            directorio.mkdir(parents=True, exist_ok=True)


def _resolver_ruta(base_dir: Path, override: Path | str | None, rel_default: str) -> Path:
    """Resuelve una ruta relativa o absoluta respecto al directorio base.

    Args:
        base_dir: Directorio base para resolver rutas relativas.
        override: Ruta de sobrescritura opcional.
        rel_default: Ruta por defecto relativa al directorio base.

    Returns:
        Ruta absoluta resuelta como objeto Path.

    """
    if override is not None:
        return Path(override).resolve()
    candidato = Path(rel_default)
    if candidato.is_absolute():
        return candidato
    return (base_dir / candidato).resolve()


def cargar_configuracion(
    ruta_config: Path | str | None = None,
    origen_normalizados_override: Path | str | None = None,
    origen_duplicados_override: Path | str | None = None,
    salida_root_override: Path | str | None = None,
) -> ConfiguracionETL:
    """Carga la configuración desde JSON o variables de entorno usando pathlib.Path.

    Args:
        ruta_config: Ruta opcional al archivo JSON de configuración.
        origen_normalizados_override: Sobrescritura del directorio de normalizados.
        origen_duplicados_override: Sobrescritura del directorio de duplicados.
        salida_root_override: Sobrescritura del directorio raíz de salida.

    Returns:
        Instancia inmutable de ConfiguracionETL con rutas resueltas.

    """
    env_cfg = os.environ.get("ACTHO360_CONFIG_PATH")
    cfg_path = Path(ruta_config or env_cfg or CONFIG_FILE_DEFAULT).resolve()
    base_dir = PROJECT_ROOT_DEFAULT

    raw: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open("r", encoding="utf-8") as archivo:
            raw = json.load(archivo)

    rutas_cfg = raw.get("rutas_relativas", {})
    norm_dir = _resolver_ruta(
        base_dir,
        origen_normalizados_override or os.environ.get("ACTHO360_ORIGEN_DIR"),
        rutas_cfg.get("origen_normalizados_dir", "input/normalizados"),
    )
    dup_dir = _resolver_ruta(
        base_dir,
        origen_duplicados_override or os.environ.get("ACTHO360_DUPLICADOS_DIR"),
        rutas_cfg.get("origen_duplicados_dir", "input/normalizados/duplicados"),
    )
    out_dir = _resolver_ruta(
        base_dir,
        salida_root_override or os.environ.get("ACTHO360_SALIDA_DIR"),
        rutas_cfg.get("salida_root_dir", "input"),
    )

    return ConfiguracionETL(
        origen_normalizados_dir=norm_dir,
        origen_duplicados_dir=dup_dir,
        salida_root_dir=out_dir,
        parametros_temporales=raw.get("parametros_temporales", {}),
        homologacion_kam=raw.get("homologacion_kam", {}),
        reglas_semaforo=raw.get("reglas_semaforo_riesgo", REGLAS_SEMAFORO_DEFAULT),
    )
