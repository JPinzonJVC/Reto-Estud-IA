"""Modelo ORM para el resumen de ejecución del pipeline (audit_ejecuciones_etl)."""

from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class AuditEjecucionEtl(Base):  # type: ignore[misc,valid-type]
    """Resumen consolidado de auditoría por ejecución del pipeline Medallion."""

    __tablename__ = "audit_ejecuciones_etl"

    id_ejecucion = Column(String(128), primary_key=True)
    """Identificador único de la ejecución del pipeline ETL."""

    fecha_inicio = Column(String(64), nullable=False)
    """Fecha y hora de inicio global de la ejecución."""

    fecha_finalizacion = Column(String(64), nullable=False)
    """Fecha y hora de finalización global de la ejecución."""

    archivos_procesados = Column(Integer, nullable=False, default=0)
    """Cantidad total de archivos fuente procesados en Bronze."""

    registros_leidos = Column(Integer, nullable=False, default=0)
    """Suma total de registros leídos desde las fuentes Bronze."""

    registros_cargados = Column(Integer, nullable=False, default=0)
    """Suma total de registros cargados en las tablas destino."""

    registros_rechazados = Column(Integer, nullable=False, default=0)
    """Cantidad total de registros rechazados en la ejecución."""

    duplicados_identificados = Column(Integer, nullable=False, default=0)
    """Cantidad total de registros duplicados clasificados en auditoría."""

    errores = Column(Text, nullable=True)
    """Detalle de errores registrados o 'NINGUNO' si fue exitoso."""

    estado_ejecucion = Column(String(64), nullable=False)
    """Estado general de la corrida del pipeline (EXITOSO o FALLIDO)."""
