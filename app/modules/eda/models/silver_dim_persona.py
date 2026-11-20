"""Modelo SQLAlchemy ORM para la dimensión de personas (silver_dim_personas)."""

from sqlalchemy import Boolean, Column, ForeignKey, String

from app.database import Base


class SilverDimPersona(Base):  # type: ignore[misc,valid-type]
    """Dimensión de personas asistentes y encuestadas en la capa Silver."""

    __tablename__ = "silver_dim_personas"

    id_persona = Column(String(64), primary_key=True)
    """Identificador único de la persona (P-xxxx)."""

    id_empresa_principal = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), nullable=True
    )
    """Clave foránea opcional hacia la empresa principal de la persona."""

    estado_resolucion_empresa = Column(String(64), nullable=True)
    """Estado de vinculación empresarial (ASOCIADA o SIN_EMPRESA_ASOCIADA)."""

    nivel_cargo = Column(String(128), nullable=True)
    """Nivel jerárquico o segmento de cargo del profesional."""

    ciudad = Column(String(128), nullable=True)
    """Ciudad reportada para el profesional."""

    es_afiliado_principal_nuevo = Column(Boolean, nullable=False, default=False)
    """Indica si la persona figura como contacto principal de nueva afiliación."""

    fecha_afiliacion_nueva = Column(String(32), nullable=True)
    """Fecha de nueva afiliación cuando aplica."""
