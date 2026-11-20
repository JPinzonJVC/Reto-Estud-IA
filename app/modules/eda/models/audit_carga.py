"""Modelo ORM para bitácora operativa de cargas por tabla (audit_cargas)."""

from sqlalchemy import Column, Integer, String

from app.database import Base


class AuditCarga(Base):  # type: ignore[misc,valid-type]
    """Registro de metadatos operativos por tabla cargada en el pipeline ETL."""

    __tablename__ = "audit_cargas"

    id_ejecucion = Column(String(128), primary_key=True)
    """Identificador único de la corrida del pipeline ETL."""

    fuente = Column(String(256), primary_key=True)
    """Descripción del flujo de transformación (origen -> destino)."""

    fecha_inicio = Column(String(64), nullable=True)
    """Marca temporal de inicio del procesamiento de la tabla."""

    fecha_finalizacion = Column(String(64), nullable=True)
    """Marca temporal de finalización del procesamiento de la tabla."""

    registros_leidos = Column(Integer, nullable=True)
    """Cantidad de registros leídos en el paso."""

    registros_procesados = Column(Integer, nullable=True)
    """Cantidad de registros procesados tras validaciones."""

    registros_insertados = Column(Integer, nullable=True)
    """Cantidad de registros escritos en la capa destino."""

    registros_actualizados = Column(Integer, nullable=True)
    """Cantidad de registros homologados o actualizados."""

    registros_rechazados = Column(Integer, nullable=True)
    """Cantidad de registros rechazados por validación de claves."""

    estado_ejecucion = Column(String(64), nullable=True)
    """Estado final del paso de carga (EXITOSO o FALLIDO)."""
