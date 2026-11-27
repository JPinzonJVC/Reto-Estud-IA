"""Modelos SQLAlchemy ORM para la jerarquía geográfica 3NF en capa Silver."""

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class SilverDimPais(Base):  # type: ignore[misc,valid-type]
    """Dimensión de países únicos normalizados en la capa Silver."""

    __tablename__ = "silver_dim_pais"

    id_pais = Column(Integer, primary_key=True)
    """Clave primaria entera del país."""

    nombre_pais = Column(String(128), nullable=False, unique=True)
    """Nombre oficial único del país."""


class SilverDimDepartamento(Base):  # type: ignore[misc,valid-type]
    """Dimensión de departamentos o regiones dentro de un país en Silver."""

    __tablename__ = "silver_dim_departamento"
    __table_args__ = (
        UniqueConstraint(
            "id_pais", "nombre_departamento", name="uq_silver_dep_pais_nombre"
        ),
    )

    id_departamento = Column(Integer, primary_key=True)
    """Clave primaria entera del departamento o región."""

    id_pais = Column(
        Integer, ForeignKey("silver_dim_pais.id_pais"), nullable=False, index=True
    )
    """Clave foránea obligatoria hacia silver_dim_pais."""

    nombre_departamento = Column(String(128), nullable=False)
    """Nombre normalizado del departamento o estado."""


class SilverDimCiudad(Base):  # type: ignore[misc,valid-type]
    """Dimensión de ciudades o municipios únicos por departamento en Silver."""

    __tablename__ = "silver_dim_ciudad"
    __table_args__ = (
        UniqueConstraint(
            "id_departamento", "nombre_ciudad", name="uq_silver_ciudad_dep_nombre"
        ),
    )

    id_ciudad = Column(Integer, primary_key=True)
    """Clave primaria entera de la ciudad."""

    id_departamento = Column(
        Integer,
        ForeignKey("silver_dim_departamento.id_departamento"),
        nullable=False,
        index=True,
    )
    """Clave foránea obligatoria hacia silver_dim_departamento."""

    nombre_ciudad = Column(String(128), nullable=False)
    """Nombre canónico de la ciudad o municipio."""
