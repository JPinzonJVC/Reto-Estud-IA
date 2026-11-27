"""Modelos SQLAlchemy ORM para personas y relación N:N persona-empresa en Silver."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class SilverDimPersona(Base):  # type: ignore[misc,valid-type]
    """Dimensión normalizada de profesionales y contactos únicos en Silver."""

    __tablename__ = "silver_dim_personas"

    id_persona = Column(String(64), primary_key=True)
    """Identificador único de la persona (P-xxxxx)."""

    id_ciudad_persona = Column(
        Integer,
        ForeignKey("silver_dim_ciudad.id_ciudad"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia la ciudad asociada al profesional."""

    nivel_cargo_actual = Column(String(128), nullable=True)
    """Nivel jerárquico actual conocido del profesional."""


class SilverBridgePersonaEmpresa(Base):  # type: ignore[misc,valid-type]
    """Tabla puente N:N de vínculos evidenciados entre personas y empresas."""

    __tablename__ = "silver_bridge_persona_empresa"
    __table_args__ = (
        UniqueConstraint(
            "id_persona", "id_empresa", name="uq_silver_bridge_persona_empresa"
        ),
    )

    id_vinculo = Column(Integer, primary_key=True)
    """Clave primaria entera del vínculo persona-empresa."""

    id_persona = Column(
        String(64),
        ForeignKey("silver_dim_personas.id_persona"),
        nullable=False,
        index=True,
    )
    """Clave foránea obligatoria hacia silver_dim_personas."""

    id_empresa = Column(
        String(64),
        ForeignKey("silver_dim_empresas.id_empresa"),
        nullable=False,
        index=True,
    )
    """Clave foránea obligatoria hacia silver_dim_empresas."""

    nivel_cargo = Column(String(128), nullable=True)
    """Cargo evidenciado para la persona dentro de esa empresa."""

    fecha_primera_evidencia = Column(String(32), nullable=True)
    """Primera fecha ISO en la que se evidenció la relación (no contratación)."""

    fecha_ultima_evidencia = Column(String(32), nullable=True)
    """Última fecha ISO en la que se evidenció la relación (no retiro)."""

    fuente_relacion = Column(String(64), nullable=False)
    """Fuente principal del vínculo (CRM, ASISTENCIA o ENCUESTA)."""

    estado_validacion = Column(String(64), nullable=False)
    """Grado de certeza (CONFIRMADO_CRM, REPORTADO_FORMULARIO, INFERIDO_DOMINIO)."""

    es_vinculo_actual = Column(Boolean, nullable=False, default=False)
    """Indica mediante regla determinística cuál es el vínculo más reciente."""
