"""Modelo SQLAlchemy ORM para la dimensión de eventos (silver_dim_eventos)."""

from sqlalchemy import Column, ForeignKey, Integer, String

from app.database import Base


class SilverDimEvento(Base):  # type: ignore[misc,valid-type]
    """Catálogo maestro normalizado de eventos y experiencias en la capa Silver."""

    __tablename__ = "silver_dim_eventos"

    id_evento = Column(Integer, primary_key=True)
    """Identificador numérico único del evento (1..N)."""

    id_ciudad_evento = Column(
        Integer,
        ForeignKey("silver_dim_ciudad.id_ciudad"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia la ciudad sede cuando el evento es presencial."""

    nombre_evento = Column(String(256), nullable=False)
    """Nombre oficial descriptivo del evento."""

    fecha_inicio_evento = Column(String(32), nullable=False)
    """Fecha ISO YYYY-MM-DD de inicio del evento."""

    fecha_fin_evento = Column(String(32), nullable=False)
    """Fecha ISO YYYY-MM-DD de finalización del evento."""

    linea_oferta_2027 = Column(String(128), nullable=False)
    """Línea estratégica de oferta 2027 (Anticipar, Evento grande, Foro, Pares)."""

    experiencia_detalle = Column(String(256), nullable=True)
    """Formato o subcategoría detallada de la experiencia."""

    modalidad = Column(String(64), nullable=False)
    """Modalidad de ejecución (Presencial, Virtual o Híbrido)."""
