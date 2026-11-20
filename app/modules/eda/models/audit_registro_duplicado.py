"""Modelo ORM para auditoría de duplicados (audit_registros_duplicados)."""

from sqlalchemy import Column, Float, Integer, String, Text

from app.database import Base


class AuditRegistroDuplicado(Base):  # type: ignore[misc,valid-type]
    """Registro de auditoría de los 122 duplicados identificados y clasificados."""

    __tablename__ = "audit_registros_duplicados"

    id_duplicado = Column(String(64), primary_key=True)
    """Identificador único del registro duplicado auditado (DUP-xxxx)."""

    tabla_normalizada_afectada = Column(String(128), nullable=True)
    """Nombre de la tabla normalizada donde se detectó la duplicidad."""

    archivo_origen_csv = Column(String(256), nullable=True)
    """Ruta relativa del archivo CSV crudo original."""

    fila_origen_csv = Column(Integer, nullable=True)
    """Número de fila dentro del archivo CSV original."""

    tipo_duplicado = Column(String(256), nullable=True)
    """Descripción detallada del tipo de duplicado encontrado en el EDA."""

    llave_negocio = Column(String(256), nullable=True)
    """Expresión de la llave de negocio involucrada en la colisión."""

    id_empresa = Column(String(64), nullable=True)
    """Identificador de empresa asociado al registro duplicado cuando aplica."""

    id_persona = Column(String(64), nullable=True)
    """Identificador de persona asociado al registro duplicado cuando aplica."""

    id_evento = Column(Float, nullable=True)
    """Identificador del evento asociado cuando corresponde a asistencias."""

    fecha_iso = Column(String(32), nullable=True)
    """Fecha asociada al registro en formato ISO YYYY-MM-DD."""

    regla_identificacion = Column(Text, nullable=True)
    """Regla aplicada durante la normalización para detectar la duplicidad."""

    detalle_primera_aparicion = Column(Text, nullable=True)
    """Resumen de atributos del registro principal conservado."""

    detalle_duplicado = Column(Text, nullable=True)
    """Resumen de atributos del registro repetido o histórico."""

    categoria_duplicidad = Column(String(128), nullable=True)
    """Categoría estandarizada (DUPLICADO_EXACTO, HISTORICO_SCD2, etc.)."""

    id_registro_conservado = Column(String(128), nullable=True)
    """Identificador del registro principal trazable en la capa Silver."""

    fecha_deteccion = Column(String(32), nullable=True)
    """Fecha de corte en la que se documentó el duplicado."""

    estado_revision = Column(String(128), nullable=True)
    """Estado de gobierno del registro en auditoría."""

    accion_aplicada = Column(String(128), nullable=True)
    """Acción de negocio aplicada (incorporado en SCD2 o conservado con traza)."""
