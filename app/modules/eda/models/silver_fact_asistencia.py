"""Modelo SQLAlchemy ORM para hechos de asistencias (silver_fact_asistencias)."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from app.database import Base


class SilverFactAsistencia(Base):  # type: ignore[misc,valid-type]
    """Tabla de hechos transaccionales de asistencias a eventos en Silver."""

    __tablename__ = "silver_fact_asistencias"

    id_asistencia = Column(String(64), primary_key=True)
    """Identificador único del registro de asistencia."""

    id_evento = Column(
        Integer,
        ForeignKey("silver_dim_eventos.id_evento"),
        nullable=False,
        index=True,
    )
    """Clave foránea obligatoria hacia silver_dim_eventos."""

    id_persona = Column(
        String(64),
        ForeignKey("silver_dim_personas.id_persona"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia el asistente identificado."""

    id_empresa = Column(
        String(64),
        ForeignKey("silver_dim_empresas.id_empresa"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia la empresa asociada a la asistencia."""

    id_vinculo = Column(
        Integer,
        ForeignKey("silver_bridge_persona_empresa.id_vinculo"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia el vínculo validado persona-empresa."""

    kam_id = Column(
        String(64),
        ForeignKey("silver_dim_kams.kam_id"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional cuando el registro identifica un KAM asignado."""

    id_ciudad_asistente = Column(
        Integer,
        ForeignKey("silver_dim_ciudad.id_ciudad"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia la ciudad reportada por el asistente."""

    nivel_cargo_evento = Column(String(128), nullable=True)
    """Nivel jerárquico del participante al momento del evento."""

    tipo_asistencia = Column(String(64), nullable=False)
    """Clasificación de asistencia ('Afiliado' o 'No Afiliado / Invitado')."""

    cantidad_inscritos = Column(Integer, nullable=True)
    """Cantidad provisional de cupos inscritos asociada al registro."""

    tiene_costo = Column(Boolean, nullable=True)
    """Indica si la participación tuvo cobro o facturación."""

    autoriza_tratamiento_datos = Column(Boolean, nullable=True)
    """Indica si el asistente autorizó el tratamiento de datos personales."""
