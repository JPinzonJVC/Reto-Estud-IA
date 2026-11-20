"""Modelo SQLAlchemy ORM para retención por empresa (gold_agg_retencion_empresa)."""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String

from app.database import Base


class GoldAggRetencionEmpresa(Base):  # type: ignore[misc,valid-type]
    """Agregación analítica de retención y semáforo de riesgo por empresa en Gold."""

    __tablename__ = "gold_agg_retencion_empresa"

    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), primary_key=True
    )
    """Clave primaria y foránea hacia silver_dim_empresas."""

    kam_id = Column(String(64), nullable=True)
    """Identificador homologado de la ejecutiva KAM responsable."""

    en_crm_afiliados = Column(Boolean, nullable=True)
    """Indica si la empresa está registrada en el maestro de afiliados CRM."""

    es_empresa_activa = Column(Boolean, nullable=True)
    """Indica si la empresa tiene estado general Activo en el CRM."""

    es_membresia_activa = Column(Boolean, nullable=True)
    """Indica si la membresía actual de la empresa está activa."""

    estado_membresia_detalle = Column(String(128), nullable=True)
    """Estado detallado de la membresía vigente en el CRM."""

    segmento_membresia = Column(String(128), nullable=True)
    """Segmento comercial de la membresía."""

    nivel_membresia = Column(String(128), nullable=True)
    """Nivel de la membresía vigente."""

    fecha_afiliacion = Column(String(32), nullable=True)
    """Fecha de afiliación vigente en formato ISO YYYY-MM-DD."""

    fecha_expiracion = Column(String(32), nullable=True)
    """Fecha de expiración o vencimiento de la membresía (YYYY-MM-DD)."""

    fecha_ultima_actividad = Column(String(32), nullable=True)
    """Fecha de última actividad registrada en el CRM."""

    renovaciones_registradas_2026 = Column(Integer, nullable=False, default=0)
    """Cantidad de movimientos de renovación registrados para la empresa."""

    estados_inactivos_historicos_scd2 = Column(Integer, nullable=False, default=0)
    """Cantidad de versiones previas no vigentes con estado inactivo en SCD2."""

    numero_retiros_historicos = Column(Integer, nullable=False, default=0)
    """Total acumulado de versiones con estado inactivo o cancelado en SCD2."""

    total_eventos = Column(Integer, nullable=False, default=0)
    """Cantidad de eventos únicos en los que participó la empresa."""

    total_asistencias = Column(Integer, nullable=False, default=0)
    """Total de asistencias registradas para la empresa."""

    personas_distintas_participantes = Column(Integer, nullable=False, default=0)
    """Cantidad de personas distintas que han asistido por la empresa."""

    asistencias_trimestre_calendario = Column(Integer, nullable=False, default=0)
    """Asistencias registradas en el trimestre calendario."""

    asistencias_trimestre_operativo = Column(Integer, nullable=False, default=0)
    """Asistencias registradas en el trimestre operativo."""

    asistencias_ventana_movil_90d_corte = Column(Integer, nullable=False, default=0)
    """Asistencias en la ventana móvil de 90 días respecto a la fecha de corte."""

    asistencias_ventana_movil_90d_ultimo_evento = Column(
        Integer, nullable=False, default=0
    )
    """Asistencias en la ventana móvil de 90 días respecto al último evento."""

    ultima_fecha_participacion = Column(String(32), nullable=True)
    """Fecha de la última participación en eventos (YYYY-MM-DD)."""

    dias_sin_participacion = Column(Float, nullable=True)
    """Días transcurridos desde la última participación en eventos."""

    meses_sin_participacion = Column(Float, nullable=True)
    """Meses de inactividad desde la última participación."""

    estado_recencia_participacion = Column(String(64), nullable=True)
    """Categoría de recencia de participación de la empresa."""

    respuestas_encuestas_total = Column(Integer, nullable=False, default=0)
    """Cantidad de encuestas de satisfacción respondidas por la empresa."""

    satisfaccion_promedio_1_5 = Column(Float, nullable=True)
    """Promedio histórico de satisfacción de la empresa en escala 1 a 5."""

    satisfaccion_reciente_1_5 = Column(Float, nullable=True)
    """Calificación de satisfacción más reciente registrada para la empresa (1 a 5)."""

    nps_adaptado_empresa_1_5 = Column(Float, nullable=True)
    """Puntaje NPS adaptado (-100 a +100) de la empresa (%Promotores - %Detractores)."""

    fecha_ultima_encuesta = Column(String(32), nullable=True)
    """Fecha de la última encuesta respondida por la empresa."""

    en_seguimiento_kam = Column(Boolean, nullable=True)
    """Indicador de origen sobre inclusión en el portafolio de seguimiento KAM."""

    asistio_segun_kam = Column(Boolean, nullable=True)
    """Indicador de origen reportado por la ejecutiva KAM sobre asistencia."""

    eventos_reportados_kam = Column(Float, nullable=True)
    """Cantidad de eventos reportados en la matriz de seguimiento KAM."""

    es_retiro_definitivo_actual = Column(Boolean, nullable=True)
    """Indica si el estado vigente actual de la empresa en CRM es retiro/inactivo."""

    fecha_ultima_interaccion_global = Column(String(32), nullable=True)
    """Fecha máxima de interacción entre actividad CRM, eventos y encuestas."""

    dias_para_expiracion = Column(Float, nullable=True)
    """Días restantes hasta la fecha de expiración respecto a la fecha de corte."""

    es_membresia_vencida = Column(Boolean, nullable=True)
    """Indica si la membresía ya se encuentra vencida (dias_para_expiracion < 0)."""

    es_proximo_vencimiento_30d = Column(Boolean, nullable=True)
    """Indica si la membresía vence entre 0 y 30 días."""

    es_proximo_vencimiento_60d = Column(Boolean, nullable=True)
    """Indica si la membresía vence entre 0 y 60 días."""

    es_proximo_vencimiento_90d = Column(Boolean, nullable=True)
    """Indica si la membresía vence entre 0 y 90 días (excluye vencidas < 0)."""

    estado_vigencia_expiracion = Column(String(64), nullable=True)
    """Clasificación del tramo de vigencia o vencimiento de la membresía."""

    alerta_membresia_vencida = Column(Boolean, nullable=True)
    """Señal booleana de alerta por membresía con fecha de expiración vencida."""

    alerta_proximo_vencimiento_90d = Column(Boolean, nullable=True)
    """Señal booleana de alerta por vencimiento próximo dentro de 90 días."""

    alerta_baja_participacion = Column(Boolean, nullable=True)
    """Señal booleana de alerta por nula participación en eventos."""

    alerta_baja_satisfaccion = Column(Boolean, nullable=True)
    """Señal booleana de alerta por satisfacción reciente inferior al umbral (3.75)."""

    alerta_monocontacto = Column(Boolean, nullable=True)
    """Señal booleana de alerta cuando solo participa una única persona."""

    puntaje_heuristico_riesgo = Column(Integer, nullable=False, default=0)
    """Puntaje acumulado de riesgo según los pesos configurados en etl_config.json."""

    semaforo_riesgo_renovacion = Column(String(64), nullable=True)
    """Clasificación del semáforo heurístico (ROJO, AMARILLO, VERDE o NO_APLICA)."""

    tipo_metodologia_riesgo = Column(String(128), nullable=True)
    """Identificador metodológico (REGLA_HEURISTICA_NEGOCIO_NO_PREDICTIVA)."""
