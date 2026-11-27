"""Modelos SQLAlchemy ORM para catálogo de membresía y ciclos de afiliación Silver."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class SilverDimCatalogoMembresia(Base):  # type: ignore[misc,valid-type]
    """Catálogo normalizado de combinaciones de segmento y nivel de membresía."""

    __tablename__ = "silver_dim_catalogo_membresia"
    __table_args__ = (
        UniqueConstraint(
            "segmento_membresia",
            "nivel_membresia",
            name="uq_silver_cat_membresia_seg_niv",
        ),
    )

    id_cat_membresia = Column(Integer, primary_key=True)
    """Clave primaria entera de la categoría de membresía."""

    segmento_membresia = Column(String(128), nullable=False)
    """Segmento comercial homologado (Corporativa, Consultora, etc.)."""

    nivel_membresia = Column(String(128), nullable=False)
    """Nivel comercial homologado (Estándar, Premium, Elite, Personal)."""

    nombre_categoria = Column(String(256), nullable=False)
    """Etiqueta descriptiva compuesta del catálogo de membresía."""


class SilverMembresia(Base):  # type: ignore[misc,valid-type]
    """Entidad de periodos o ciclos reales de membresía de una empresa en Silver."""

    __tablename__ = "silver_membresias"

    id_membresia = Column(String(64), primary_key=True)
    """Clave primaria única del ciclo real de membresía (MEM-xxxx)."""

    id_empresa = Column(
        String(64),
        ForeignKey("silver_dim_empresas.id_empresa"),
        nullable=False,
        index=True,
    )
    """Clave foránea obligatoria hacia silver_dim_empresas."""

    id_cat_membresia = Column(
        Integer,
        ForeignKey("silver_dim_catalogo_membresia.id_cat_membresia"),
        nullable=False,
        index=True,
    )
    """Clave foránea obligatoria hacia silver_dim_catalogo_membresia."""

    kam_id = Column(
        String(64),
        ForeignKey("silver_dim_kams.kam_id"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia la ejecutiva KAM responsable de la afiliación."""

    id_registro_crm_origen = Column(String(128), nullable=True)
    """Metadato técnico opcional con el ID del registro de origen en CRM."""

    estado_membresia_detalle = Column(String(128), nullable=False)
    """Estado de negocio del ciclo (Activo, Cancelado, Expirado, Periodo de Gracia)."""

    es_membresia_activa = Column(Boolean, nullable=False, default=False)
    """Estado booleano de negocio que indica si la afiliación está activa."""

    fecha_miembro_desde = Column(String(32), nullable=True)
    """Fecha ISO YYYY-MM-DD de antigüedad histórica de membresía."""

    fecha_afiliacion = Column(String(32), nullable=True)
    """Fecha ISO YYYY-MM-DD de afiliación registrada para este ciclo."""

    fecha_inicio_vigencia = Column(String(32), nullable=True)
    """Fecha ISO YYYY-MM-DD de inicio del periodo de vigencia."""

    fecha_fin_vigencia = Column(String(32), nullable=True)
    """Fecha ISO YYYY-MM-DD de expiración o fin del periodo de vigencia."""
