"""Modelo SQLAlchemy ORM para la dimensión de ejecutivas KAM (silver_dim_kams)."""

from sqlalchemy import Boolean, Column, String

from app.database import Base


class SilverDimKam(Base):  # type: ignore[misc,valid-type]
    """Dimensión de ejecutivas KAM en la capa Silver."""

    __tablename__ = "silver_dim_kams"

    kam_id = Column(String(64), primary_key=True)
    """Identificador canónico de la ejecutiva KAM (KAM A..I o KAM-UNASSIGNED)."""

    kam_etiqueta_original = Column(String(128), nullable=True)
    """Etiqueta original de la ejecutiva KAM en los archivos fuente."""

    responsable_nombre = Column(String(128), nullable=True)
    """Nombre de la ejecutiva responsable de la cuenta."""

    tiene_seguimiento_eventos = Column(Boolean, nullable=False, default=False)
    """Indica si la ejecutiva cuenta con portafolio de seguimiento de eventos."""

    es_kam_asignado = Column(Boolean, nullable=False, default=False)
    """Indica si corresponde a una ejecutiva asignada (True) o a KAM-UNASSIGNED."""
