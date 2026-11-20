"""Modelo ORM para reconciliación de capas (audit_reconciliacion_origen_destino)."""

from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class AuditReconciliacionOrigenDestino(Base):  # type: ignore[misc,valid-type]
    """Registro de reconciliación de conteos entre las capas Bronze y Silver."""

    __tablename__ = "audit_reconciliacion_origen_destino"

    Tabla = Column(String(128), primary_key=True)
    """Nombre lógico de la tabla reconciliada entre Bronze y Silver."""

    Filas_Bronze = Column(Integer, nullable=True)
    """Cantidad de filas leídas en la capa Bronze."""

    Cols_Bronze = Column(Integer, nullable=True)
    """Cantidad de columnas presentes en la capa Bronze."""

    Filas_Silver = Column(Integer, nullable=True)
    """Cantidad de filas válidas persistidas en la capa Silver."""

    Cols_Silver = Column(Integer, nullable=True)
    """Cantidad de columnas estructuradas en la capa Silver."""

    Filas_Rechazadas = Column(Integer, nullable=True)
    """Cantidad de filas enviadas a audit_registros_rechazados."""

    Diferencia_Filas = Column(Integer, nullable=True)
    """Diferencia neta de filas: (Filas_Silver + Filas_Rechazadas) - Filas_Bronze."""

    Explicacion_Reconciliacion = Column(Text, nullable=True)
    """Explicación técnica de la conciliación y separación de métricas."""
