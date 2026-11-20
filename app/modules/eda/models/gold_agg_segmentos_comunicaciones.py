"""Modelo ORM para segmentos de comunicaciones (gold_agg_segmentos_comunicaciones)."""

from sqlalchemy import Boolean, Column, Integer, String, Text

from app.database import Base


class GoldAggSegmentosComunicaciones(Base):  # type: ignore[misc,valid-type]
    """Tabla Gold con los 8 segmentos accionables para campañas de comunicaciones."""

    __tablename__ = "gold_agg_segmentos_comunicaciones"

    id_registro_segmento = Column(String(160), primary_key=True)
    """Clave primaria compuesta determinística (segmento::empresa::persona)."""

    orden_segmento = Column(Integer, nullable=False)
    """Número de orden oficial del segmento (1 a 8)."""

    segmento_codigo = Column(String(64), nullable=False, index=True)
    """Código técnico estandarizado del segmento de comunicaciones."""

    segmento_nombre = Column(String(128), nullable=False)
    """Nombre legible del segmento de comunicaciones para negocio."""

    id_empresa = Column(String(64), nullable=True, index=True)
    """Identificador de la empresa asociada al registro del segmento."""

    id_persona = Column(String(64), nullable=True, index=True)
    """Identificador de la persona asociada cuando el segmento es a nivel contacto."""

    kam_id = Column(String(64), nullable=True, index=True)
    """Identificador homologado de la ejecutiva KAM responsable de la cuenta."""

    nivel_membresia = Column(String(64), nullable=True)
    """Nivel de membresía de la empresa (Conectar, Crecer, Liderar, etc.)."""

    estado_vigencia_expiracion = Column(String(64), nullable=True)
    """Clasificación temporal de vigencia o vencimiento de la membresía."""

    semaforo_riesgo_renovacion = Column(String(64), nullable=True)
    """Categoría del semáforo heurístico de riesgo de no renovación."""

    detalle_criterio = Column(Text, nullable=True)
    """Descripción del criterio específico por el cual ingresó al segmento."""

    autoriza_tratamiento_datos = Column(Boolean, nullable=True)
    """Indicador de autorización de datos cuando proviene de asistencias/encuestas."""
