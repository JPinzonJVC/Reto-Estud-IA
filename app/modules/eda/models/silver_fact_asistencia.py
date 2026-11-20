"""Modelo SQLAlchemy ORM para hechos de asistencia (silver_fact_asistencias)."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from app.database import Base


class SilverFactAsistencia(Base):  # type: ignore[misc,valid-type]
    """Tabla de hechos de asistencias a eventos en la capa Silver."""

    __tablename__ = "silver_fact_asistencias"

    id_asistencia = Column(String(64), primary_key=True)
    """Identificador único del registro de asistencia (A-xxxxx)."""

    id_evento = Column(
        Integer, ForeignKey("silver_dim_eventos.id_evento"), nullable=False
    )
    """Clave foránea hacia silver_dim_eventos con el evento asistido."""

    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), nullable=True
    )
    """Clave foránea opcional hacia silver_dim_empresas."""

    id_persona = Column(
        String(64), ForeignKey("silver_dim_personas.id_persona"), nullable=False
    )
    """Clave foránea hacia silver_dim_personas con el asistente."""

    kam_id = Column(String(64), ForeignKey("silver_dim_kams.kam_id"), nullable=False)
    """Clave foránea hacia silver_dim_kams con la ejecutiva responsable."""

    fecha_evento = Column(String(32), nullable=True)
    """Fecha del evento asistido en formato ISO YYYY-MM-DD."""

    periodo_mes_iso = Column(String(32), nullable=True)
    """Periodo mensual de la asistencia en formato YYYY-MM."""

    nivel_cargo = Column(String(128), nullable=True)
    """Nivel de cargo del asistente en el momento del evento."""

    ciudad_evento = Column(String(128), nullable=True)
    """Ciudad asociada al registro de asistencia."""

    cantidad_inscritos = Column(Integer, nullable=True)
    """Cantidad de cupos o inscritos reportados en la transacción."""

    es_afiliado = Column(Boolean, nullable=True)
    """Indica si el asistente participaba en calidad de afiliado."""

    tiene_costo = Column(Boolean, nullable=True)
    """Indica si la inscripción tuvo costo asociado."""

    autoriza_tratamiento_datos = Column(Boolean, nullable=True)
    """Indica si el participante autorizó el tratamiento de datos personales."""

    confirmado_ubicacion_principal = Column(Boolean, nullable=True)
    """Indica confirmación de asistencia en la ubicación principal."""

    reflejado_en_matriz_general = Column(Boolean, nullable=True)
    """Indica si la asistencia de la empresa aparece en la matriz consolidada."""

    conteo_empresa_matriz_general = Column(Integer, nullable=True)
    """Conteo reportado para la empresa en la matriz general de asistencia."""

    kam_valor_original = Column(String(128), nullable=True)
    """Valor original del campo KAM antes de la homologación."""

    tipo_asistencia = Column(String(64), nullable=True)
    """Clasificación de asistencia (Afiliado vs No Afiliado / Invitado)."""

    modalidad_evento = Column(String(64), nullable=True)
    """Modalidad del evento obtenida del catálogo maestro de eventos."""

    estado_resolucion_identidad = Column(String(64), nullable=True)
    """Estado de resolución de empresa y persona en el registro."""
