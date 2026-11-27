"""Modelo SQLAlchemy ORM para la dimensión de ejecutivas KAM (silver_dim_kams)."""

from sqlalchemy import Boolean, Column, String

from app.database import Base


class SilverDimKam(Base):  # type: ignore[misc,valid-type]
    """Catálogo normalizado de ejecutivas de cuenta KAM en la capa Silver."""

    __tablename__ = "silver_dim_kams"

    kam_id = Column(String(64), primary_key=True)
    """Identificador canónico de la ejecutiva (KAM A..I o KAM-UNASSIGNED)."""

    responsable_nombre = Column(String(128), nullable=False)
    """Nombre de la ejecutiva responsable o etiqueta corporativa."""

    tiene_seguimiento_eventos = Column(Boolean, nullable=False, default=False)
    """Indica si la ejecutiva posee portafolio activo de seguimiento a eventos."""
