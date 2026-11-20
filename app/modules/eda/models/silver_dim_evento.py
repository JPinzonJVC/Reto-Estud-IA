"""Modelo SQLAlchemy ORM para la dimensión de eventos (silver_dim_eventos)."""

from sqlalchemy import Boolean, Column, Integer, String

from app.database import Base


class SilverDimEvento(Base):  # type: ignore[misc,valid-type]
    """Dimensión de eventos en la capa Silver."""

    __tablename__ = "silver_dim_eventos"

    id_evento = Column(Integer, primary_key=True)
    """Identificador numérico único del evento en el catálogo maestro."""

    archivo_csv = Column(String(256), nullable=True)
    """Nombre del archivo CSV original del evento."""

    fecha_evento = Column(String(32), nullable=True)
    """Fecha principal del evento en formato ISO YYYY-MM-DD."""

    fecha_inicio_evento = Column(String(32), nullable=True)
    """Fecha de inicio del evento en formato ISO YYYY-MM-DD."""

    fecha_fin_evento = Column(String(32), nullable=True)
    """Fecha de finalización del evento en formato ISO YYYY-MM-DD."""

    periodo_mes_iso = Column(String(32), nullable=True)
    """Periodo mensual del evento en formato YYYY-MM."""

    nombre_evento = Column(String(256), nullable=True)
    """Nombre descriptivo oficial del evento."""

    linea_oferta_2027 = Column(String(128), nullable=True)
    """Línea de oferta estratégica 2027 (Anticipar, Evento grande, Foro, Pares)."""

    experiencia_detalle = Column(String(256), nullable=True)
    """Tipo o formato detallado de la experiencia del evento."""

    modalidad = Column(String(64), nullable=True)
    """Modalidad de ejecución (Presencial, Virtual o Híbrido)."""

    es_presencial = Column(Boolean, nullable=False, default=False)
    """Indica si el evento cuenta con componente presencial."""

    tiene_asistentes_registrados = Column(Boolean, nullable=False, default=False)
    """Indica si el evento posee registros de asistencia en los archivos fuente."""
