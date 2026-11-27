"""Esquemas Pydantic para la ejecución y consulta del pipeline ETL vía API."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EtlRunRequest(BaseModel):
    """Parámetros opcionales para disparar una ejecución del pipeline ETL."""

    model_config = ConfigDict(extra="forbid")
    """Configuración estricta del modelo de entrada."""

    persistir_en_db: bool = True
    """Si es True, persiste las capas Silver, Gold y Auditoría en PostgreSQL."""

    fecha_corte: str | None = None
    """Fecha de corte opcional (YYYY-MM-DD) para sobrescribir etl_config.json."""

    @field_validator("fecha_corte")
    @classmethod
    def validar_fecha_corte(cls, valor: str | None) -> str | None:
        """Valida que fecha_corte cumpla el formato ISO YYYY-MM-DD.

        Args:
            valor: Cadena opcional con la fecha de corte solicitada.

        Returns:
            Cadena validada en formato ISO YYYY-MM-DD o None.

        """
        if valor is None:
            return None
        date.fromisoformat(valor)
        return valor


class EtlRunAcceptedResponse(BaseModel):
    """Respuesta inmediata al encolar una ejecución asíncrona del ETL."""

    model_config = ConfigDict(from_attributes=True)
    """Configuración del esquema de confirmación asíncrona."""

    run_id: str
    """Identificador único de la ejecución ETL."""

    estado_ejecucion: str
    """Estado inicial de la ejecución."""

    mensaje: str
    """Mensaje informativo de confirmación."""


class EtlRunSummary(BaseModel):
    """Resumen estructurado del estado y métricas de una ejecución ETL."""

    model_config = ConfigDict(from_attributes=True)
    """Configuración del modelo de resumen de ejecución."""

    id_ejecucion: str
    """Identificador único de la corrida del pipeline."""

    fecha_inicio: str
    """Marca temporal de inicio de la ejecución."""

    fecha_finalizacion: str | None = None
    """Marca temporal de finalización cuando concluye."""

    archivos_procesados: int = 0
    """Cantidad de archivos fuente verificados en Bronze."""

    registros_leidos: int = 0
    """Total de registros leídos desde Bronze."""

    registros_cargados: int = 0
    """Total de registros insertados en las capas destino."""

    registros_rechazados: int = 0
    """Total de registros enviados a cuarentena por clave inválida."""

    duplicados_identificados: int = 0
    """Contador legado de duplicados descartados."""

    errores: str = "NINGUNO"
    """Detalle de errores o 'NINGUNO' si fue exitoso."""

    estado_ejecucion: str
    """Estado de la corrida ('EN_PROGRESO', 'EXITOSO' o 'FALLIDO')."""

    conteos_db: dict[str, int] = Field(default_factory=dict)
    """Conteo de registros persistidos por tabla SQL cuando aplica."""
