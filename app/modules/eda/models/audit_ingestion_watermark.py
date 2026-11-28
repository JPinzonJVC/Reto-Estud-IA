"""Modelo ORM para el control de watermarks de ingesta (audit_ingestion_watermarks)."""

from typing import Any

from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class AuditIngestionWatermark(Base):  # type: ignore[misc,valid-type]
    """Registro del último estado sincronizado por fuente externa (Drive, Zoho CRM)."""

    __tablename__ = "audit_ingestion_watermarks"

    source_name: Any = Column(String(128), primary_key=True)
    """Identificador único de la fuente (ej. 'google_drive', 'zoho_crm:Accounts')."""

    last_sync_at: Any = Column(String(64), nullable=True)
    """Timestamp ISO-8601 UTC de la última sincronización exitosa."""

    last_cursor: Any = Column(String(256), nullable=True)
    """Cursor o checksum de control (ej. md5Checksum de Drive o fecha Zoho)."""

    last_status: Any = Column(String(32), nullable=False, default="PENDING")
    """Estado de la última ejecución de extracción (SUCCESS, SKIPPED, FAILED)."""

    records_extracted: Any = Column(Integer, nullable=False, default=0)
    """Cantidad de registros o archivos extraídos en la última corrida."""

    details: Any = Column(Text, nullable=True)
    """Detalle opcional o mensaje de error de la última extracción."""

    updated_at: Any = Column(String(64), nullable=False)
    """Fecha y hora ISO-8601 UTC de última actualización del registro."""
