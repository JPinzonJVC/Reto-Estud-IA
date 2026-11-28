"""Modelo ORM para el resumen de ejecución del pipeline (audit_ejecuciones_etl)."""

from typing import Any

from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class AuditEjecucionEtl(Base):  # type: ignore[misc,valid-type]
    """Resumen consolidado de auditoría por ejecución del pipeline Medallion."""

    __tablename__ = "audit_ejecuciones_etl"

    id_ejecucion: Any = Column(String(128), primary_key=True)
    """Identificador único de la ejecución del pipeline ETL."""

    fecha_inicio: Any = Column(String(64), nullable=False)
    """Fecha y hora de inicio global de la ejecución."""

    fecha_finalizacion: Any = Column(String(64), nullable=False)
    """Fecha y hora de finalización global de la ejecución."""

    archivos_procesados: Any = Column(Integer, nullable=False, default=0)
    """Cantidad total de archivos fuente procesados en Bronze."""

    registros_leidos: Any = Column(Integer, nullable=False, default=0)
    """Suma total de registros leídos desde las fuentes Bronze."""

    registros_cargados: Any = Column(Integer, nullable=False, default=0)
    """Suma total de registros cargados en las tablas destino."""

    registros_rechazados: Any = Column(Integer, nullable=False, default=0)
    """Cantidad total de registros rechazados en la ejecución."""

    duplicados_identificados: Any = Column(Integer, nullable=False, default=0)
    """Cantidad total de registros duplicados clasificados en auditoría."""

    errores: Any = Column(Text, nullable=True)
    """Detalle de errores registrados o 'NINGUNO' si fue exitoso."""

    estado_ejecucion: Any = Column(String(64), nullable=False)
    """Estado general de la corrida del pipeline (EXITOSO o FALLIDO)."""
