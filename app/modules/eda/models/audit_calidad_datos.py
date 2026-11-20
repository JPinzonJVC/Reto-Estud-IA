"""Modelo ORM para reglas e incidencias de calidad (audit_calidad_datos)."""

from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class AuditCalidadDatos(Base):  # type: ignore[misc,valid-type]
    """Registro de reglas e incidencias de calidad de datos aplicadas."""

    __tablename__ = "audit_calidad_datos"

    id_incidencia = Column(String(64), primary_key=True)
    """Identificador único de la regla o incidencia de calidad (DQ-xxxx)."""

    tabla_analizada = Column(String(128), nullable=True)
    """Nombre de la tabla Silver evaluada por la regla de calidad."""

    campo_afectado = Column(String(256), nullable=True)
    """Campo o conjunto de columnas verificadas."""

    tipo_inconsistencia = Column(String(128), nullable=True)
    """Tipología de la inconsistencia o regla de negocio aplicada."""

    registros_afectados = Column(Integer, nullable=True)
    """Cantidad de filas impactadas por la regla o hallazgo."""

    valor_original = Column(Text, nullable=True)
    """Descripción del estado o valor original en la capa Bronze."""

    valor_corregido = Column(Text, nullable=True)
    """Acción de estandarización o conservación aplicada en Silver."""

    fecha_corte_modelo = Column(String(32), nullable=True)
    """Fecha de corte de referencia del modelo."""

    estado_resolucion = Column(String(128), nullable=True)
    """Estado final de la regla (CORREGIDO_HOMOLOGADO, DOCUMENTADO_CONSERVADO, etc.)."""
