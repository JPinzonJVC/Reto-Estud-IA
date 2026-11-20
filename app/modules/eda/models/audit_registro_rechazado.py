"""Modelo ORM para registros rechazados en Silver (audit_registros_rechazados)."""

from sqlalchemy import Column, String, Text

from app.database import Base


class AuditRegistroRechazado(Base):  # type: ignore[misc,valid-type]
    """Registro de auditoría de filas rechazadas durante la validación Silver."""

    __tablename__ = "audit_registros_rechazados"

    id_rechazo = Column(String(64), primary_key=True)
    """Identificador único del rechazo registrado (REJ-xxxx)."""

    id_ejecucion = Column(String(128), nullable=True)
    """Identificador de la ejecución ETL donde se detectó el rechazo."""

    tabla_destino = Column(String(128), nullable=True)
    """Nombre de la tabla Silver en la que falló la validación."""

    archivo_origen_bronze = Column(String(256), nullable=True)
    """Nombre del archivo Bronze del cual provenía el registro."""

    motivo_rechazo = Column(Text, nullable=True)
    """Causa técnica del rechazo (PK nula, vacía o duplicada)."""

    registro_original_json = Column(Text, nullable=True)
    """Contenido íntegro de la fila rechazada serializado en formato JSON."""

    fecha_corte_modelo = Column(String(32), nullable=True)
    """Fecha de corte del modelo analítico."""
