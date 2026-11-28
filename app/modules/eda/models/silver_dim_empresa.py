"""Modelo SQLAlchemy ORM para la dimensión de empresas (silver_dim_empresas)."""

from typing import Any

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String

from app.database import Base


class SilverDimEmpresa(Base):  # type: ignore[misc,valid-type]
    """Dimensión normalizada de organizaciones (afiliadas, ex-afiliadas y leads)."""

    __tablename__ = "silver_dim_empresas"

    id_empresa: Any = Column(String(64), primary_key=True)
    """Identificador único de negocio de la organización (EMP-xxxx)."""

    id_registro_crm: Any = Column(String(128), nullable=True)
    """Identificador actual del registro en Zoho CRM cuando aplica."""

    kam_id: Any = Column(
        String(64),
        ForeignKey("silver_dim_kams.kam_id"),
        nullable=False,
        index=True,
    )
    """Clave foránea hacia silver_dim_kams (KAM actualmente asignado)."""

    id_ciudad_empresa: Any = Column(
        Integer,
        ForeignKey("silver_dim_ciudad.id_ciudad"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia silver_dim_ciudad (sede de la empresa)."""

    es_empresa_activa: Any = Column(Boolean, nullable=False, default=False)
    """Indica si el estado operativo general de la cuenta en CRM es Activo."""

    sector_economico: Any = Column(String(256), nullable=True)
    """Sector económico principal de la organización."""

    subsector_economico: Any = Column(String(256), nullable=True)
    """Subsector económico detallado de la organización."""

    tamano_empresa: Any = Column(String(128), nullable=True)
    """Clasificación de tamaño empresarial (Grande, Mediana, Pequeña, Micro)."""

    rango_empleados: Any = Column(String(128), nullable=True)
    """Rango de cantidad de colaboradores de la empresa."""

    porcentaje_mujeres_num: Any = Column(Float, nullable=True)
    """Porcentaje numérico de participación femenina reportado."""

    fecha_ultima_actividad_crm: Any = Column(String(32), nullable=True)
    """Fecha ISO YYYY-MM-DD de última interacción registrada en CRM."""

    es_independiente: Any = Column(Boolean, nullable=True)
    """Indica si corresponde a un profesional independiente."""

    es_registro_prueba: Any = Column(Boolean, nullable=True)
    """Indica si el registro corresponde a una cuenta de prueba."""

    bloqueado_crm: Any = Column(Boolean, nullable=True)
    """Indica si el registro se encuentra bloqueado en CRM."""

    vinculado_comunidades: Any = Column(Boolean, nullable=True)
    """Indica participación en comunidades especializadas ACTHO."""

    pilar_hr_estrategico: Any = Column(Boolean, nullable=True)
    """Indica vinculación al pilar HR Estratégico."""

    pilar_mas_que_salario: Any = Column(Boolean, nullable=True)
    """Indica vinculación al pilar Más que Salario."""

    pilar_talento_que_elige: Any = Column(Boolean, nullable=True)
    """Indica vinculación al pilar Talento que Elige."""

    pilar_gente_que_crece: Any = Column(Boolean, nullable=True)
    """Indica vinculación al pilar Gente que Crece."""

    comunidad_mujeres_hr: Any = Column(Boolean, nullable=True)
    """Indica participación en la comunidad Mujeres en HR."""

    es_influenciador: Any = Column(Boolean, nullable=True)
    """Indica si la cuenta está clasificada como influenciadora."""
