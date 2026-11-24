"""Contratos base para extractores desacoplados del pipeline EDA Medallion."""

from pathlib import Path

from pydantic import BaseModel, Field

from app.env_vars import IngestionSource

__all__ = ["ExtractionResult", "IngestionSource"]


class ExtractionResult(BaseModel):
    """Resultado estandarizado de una corrida de extracción externa."""

    source_name: str
    """Identificador único de la fuente extraída."""

    enabled: bool = True
    """Indica si el extractor estuvo habilitado durante la corrida."""

    has_changes: bool = False
    """Indica si se descargaron archivos o registros nuevos/modificados."""

    files_written: list[Path] = Field(default_factory=list)
    """Rutas locales de archivos generados o actualizados."""

    records_extracted: int = 0
    """Total de registros o filas extraídas."""

    new_cursor: str | None = None
    """Nuevo cursor o checksum para persistir en watermarks."""

    skipped_reason: str | None = None
    """Motivo por el cual la extracción fue omitida, si aplica."""
