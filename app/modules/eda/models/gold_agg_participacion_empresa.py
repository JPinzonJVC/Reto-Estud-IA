"""Modelo ORM para participación por empresa (gold_agg_participacion_empresa)."""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String

from app.database import Base


class GoldAggParticipacionEmpresa(Base):  # type: ignore[misc,valid-type]
    """Agregación analítica de participación por empresa en la capa Gold."""

    __tablename__ = "gold_agg_participacion_empresa"

    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), primary_key=True
    )
    """Clave primaria y foránea hacia silver_dim_empresas."""

    periodo_analisis = Column(String(32), primary_key=True)
    """Etiqueta del periodo consolidado de análisis (ej. 2026-ANUAL)."""

    fecha_corte_referencia = Column(String(32), nullable=True)
    """Fecha de corte utilizada como referencia para ventanas móviles y recencia."""

    etiqueta_trimestre_calendario = Column(String(64), nullable=True)
    """Etiqueta del trimestre calendario evaluado (ej. 2026-Q3)."""

    kam_id = Column(String(64), nullable=True)
    """Identificador de la ejecutiva KAM asignada a la empresa."""

    es_membresia_activa = Column(Boolean, nullable=True)
    """Indica si la membresía de la empresa se encuentra activa."""

    nivel_membresia = Column(String(128), nullable=True)
    """Nivel de membresía vigente de la empresa."""

    total_eventos = Column(Integer, nullable=False, default=0)
    """Cantidad de eventos únicos a los que asistió la empresa."""

    total_asistencias = Column(Integer, nullable=False, default=0)
    """Cantidad total de participaciones o asistencias registradas."""

    personas_distintas_participantes = Column(Integer, nullable=False, default=0)
    """Cantidad de profesionales distintos que participaron por la empresa."""

    ultima_fecha_participacion = Column(String(32), nullable=True)
    """Fecha del último evento en el que participó la empresa (YYYY-MM-DD)."""

    primera_fecha_participacion = Column(String(32), nullable=True)
    """Fecha del primer evento en el que participó la empresa (YYYY-MM-DD)."""

    asistencias_trimestre_calendario = Column(Integer, nullable=False, default=0)
    """Total de asistencias durante el trimestre calendario configurado."""

    asistencias_trimestre_operativo = Column(Integer, nullable=False, default=0)
    """Total de asistencias durante el trimestre operativo configurado."""

    asistencias_ventana_movil_90d_corte = Column(Integer, nullable=False, default=0)
    """Asistencias en la ventana móvil de 90 días previos a la fecha de corte."""

    asistencias_ventana_movil_90d_ultimo_evento = Column(
        Integer, nullable=False, default=0
    )
    """Asistencias en la ventana móvil de 90 días previos al último evento global."""

    participacion_linea_anticipar = Column(Integer, nullable=False, default=0)
    """Cantidad de asistencias en eventos de la línea Anticipar."""

    participacion_linea_evento_grande = Column(Integer, nullable=False, default=0)
    """Cantidad de asistencias en eventos de la línea Evento grande."""

    participacion_linea_foro = Column(Integer, nullable=False, default=0)
    """Cantidad de asistencias en eventos de la línea Foro."""

    participacion_linea_pares = Column(Integer, nullable=False, default=0)
    """Cantidad de asistencias en eventos de la línea Pares."""

    participacion_modalidad_presencial = Column(Integer, nullable=False, default=0)
    """Cantidad de asistencias en eventos de modalidad Presencial."""

    participacion_modalidad_virtual = Column(Integer, nullable=False, default=0)
    """Cantidad de asistencias en eventos de modalidad Virtual."""

    participacion_modalidad_hibrido = Column(Integer, nullable=False, default=0)
    """Cantidad de asistencias en eventos de modalidad Híbrido."""

    dias_sin_participacion = Column(Float, nullable=True)
    """Días transcurridos desde la última participación hasta la fecha de corte."""

    meses_sin_participacion = Column(Float, nullable=True)
    """Meses de inactividad desde la última participación (nulo si total_eventos=0)."""

    estado_recencia_participacion = Column(String(64), nullable=True)
    """Clasificación del estado de recencia de participación de la empresa."""
