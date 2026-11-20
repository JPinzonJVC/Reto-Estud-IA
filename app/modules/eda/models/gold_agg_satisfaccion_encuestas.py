"""Modelo ORM para satisfacción de encuestas (gold_agg_satisfaccion_encuestas)."""

from sqlalchemy import Column, Float, Integer, String

from app.database import Base


class GoldAggSatisfaccionEncuestas(Base):  # type: ignore[misc,valid-type]
    """Agregación analítica de satisfacción por modalidad y mes en la capa Gold."""

    __tablename__ = "gold_agg_satisfaccion_encuestas"

    modalidad_encuesta = Column(String(64), primary_key=True)
    """Modalidad del instrumento evaluado (Presencial o Virtual)."""

    periodo_mes_iso = Column(String(32), primary_key=True)
    """Periodo mensual de aplicación de la encuesta en formato YYYY-MM."""

    total_respuestas = Column(Integer, nullable=False, default=0)
    """Cantidad total de respuestas recibidas en la modalidad y periodo."""

    respuestas_con_empresa_resuelta = Column(Integer, nullable=False, default=0)
    """Cantidad de respuestas donde se identificó la empresa del participante."""

    respuestas_sin_empresa = Column(Integer, nullable=False, default=0)
    """Cantidad de respuestas sin empresa vinculada."""

    respuestas_anonimas_sin_persona = Column(Integer, nullable=False, default=0)
    """Cantidad de respuestas anónimas sin identificador de persona."""

    promedio_satisfaccion_general_1_5 = Column(Float, nullable=True)
    """Promedio general de satisfacción en escala Likert de 1 a 5."""

    promedio_locacion_plataforma_1_5 = Column(Float, nullable=True)
    """Promedio de calificación (1 a 5) de locación o plataforma."""

    promedio_convocatoria_1_5 = Column(Float, nullable=True)
    """Promedio de calificación (1 a 5) de convocatoria y publicidad."""

    promedio_conferencistas_1_5 = Column(Float, nullable=True)
    """Promedio de calificación (1 a 5) de conferencistas."""

    promedio_relevancia_temas_1_5 = Column(Float, nullable=True)
    """Promedio de calificación (1 a 5) de relevancia de los temas."""

    calificaciones_altas_475_a_500 = Column(Integer, nullable=False, default=0)
    """Cantidad de respuestas con promedio de satisfacción entre 4.75 y 5.00."""

    calificaciones_medias_375_a_474 = Column(Integer, nullable=False, default=0)
    """Cantidad de respuestas con promedio de satisfacción entre 3.75 y 4.74."""

    calificaciones_bajas_menores_375 = Column(Integer, nullable=False, default=0)
    """Cantidad de respuestas con promedio de satisfacción inferior a 3.75."""

    promotores_nps_0_10 = Column(Float, nullable=True)
    """Conteo de promotores (calificación 9-10) cuando existe pregunta NPS 0-10."""

    pasivos_nps_0_10 = Column(Float, nullable=True)
    """Conteo de pasivos (calificación 7-8) cuando existe pregunta NPS 0-10."""

    detractores_nps_0_10 = Column(Float, nullable=True)
    """Conteo de detractores (calificación 0-6) cuando existe pregunta NPS 0-10."""

    nps_oficial_0_10 = Column(Float, nullable=True)
    """Puntaje NPS oficial (-100 a +100); nulo para encuestas históricas Likert 1-5."""

    estado_calculo_nps = Column(String(128), nullable=True)
    """Estado de disponibilidad y cálculo del indicador NPS 0-10."""

    asociacion_evento_origen = Column(String(128), nullable=True)
    """Nota de trazabilidad sobre la disponibilidad de id_evento en la fuente."""
