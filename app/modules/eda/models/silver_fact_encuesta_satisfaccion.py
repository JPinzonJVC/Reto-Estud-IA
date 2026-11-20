"""Modelo ORM para encuestas de satisfacción (silver_fact_encuestas_satisfaccion)."""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text

from app.database import Base


class SilverFactEncuestaSatisfaccion(Base):  # type: ignore[misc,valid-type]
    """Tabla de hechos de encuestas de satisfacción en la capa Silver."""

    __tablename__ = "silver_fact_encuestas_satisfaccion"

    id_respuesta = Column(String(64), primary_key=True)
    """Identificador único de la respuesta de encuesta (EP-xxxx o EV-xxxx)."""

    modalidad_encuesta = Column(String(64), nullable=True)
    """Modalidad del formulario de encuesta (Presencial o Virtual)."""

    es_modalidad_presencial = Column(Boolean, nullable=True)
    """Indica si la encuesta corresponde al formulario de eventos presenciales."""

    id_evento = Column(Integer, nullable=True)
    """Identificador del evento (nulo en fuentes históricas sin captura de evento)."""

    fecha_encuesta = Column(String(32), nullable=True)
    """Fecha de diligenciamiento de la encuesta en formato ISO YYYY-MM-DD."""

    periodo_mes_iso = Column(String(32), nullable=True)
    """Periodo mensual de la respuesta en formato YYYY-MM."""

    fecha_hora_inicio = Column(String(64), nullable=True)
    """Marca temporal de inicio de respuesta del formulario."""

    fecha_hora_fin = Column(String(64), nullable=True)
    """Marca temporal de finalización del formulario."""

    duracion_segundos = Column(Integer, nullable=True)
    """Tiempo empleado para responder la encuesta en segundos."""

    calif_locacion_o_plataforma = Column(Integer, nullable=True)
    """Calificación Likert (1 a 5) de la locación física o plataforma virtual."""

    calif_convocatoria_publicidad = Column(Integer, nullable=True)
    """Calificación Likert (1 a 5) del proceso de convocatoria y publicidad."""

    calif_conferencistas = Column(Integer, nullable=True)
    """Calificación Likert (1 a 5) de los conferencistas o panelistas."""

    calif_relevancia_temas = Column(Integer, nullable=True)
    """Calificación Likert (1 a 5) de la pertinencia y relevancia de los temas."""

    promedio_satisfaccion = Column(Float, nullable=True)
    """Promedio aritmético de satisfacción general del encuestado en escala 1 a 5."""

    temarios_sugeridos = Column(Text, nullable=True)
    """Comentarios abiertos o temarios sugeridos por el participante."""

    desea_recibir_actualizaciones = Column(Boolean, nullable=True)
    """Indica si el participante autorizó recibir actualizaciones y dejó sus datos."""

    id_persona = Column(
        String(64), ForeignKey("silver_dim_personas.id_persona"), nullable=True
    )
    """Clave foránea opcional hacia silver_dim_personas (nula en anónimas)."""

    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), nullable=True
    )
    """Clave foránea opcional hacia silver_dim_empresas."""

    ciudad = Column(String(128), nullable=True)
    """Ciudad asociada al participante encuestado."""

    empresa_en_crm = Column(Boolean, nullable=True)
    """Indica si la empresa identificada existe en el maestro del CRM."""

    metodo_asignacion_empresa = Column(String(128), nullable=True)
    """Método utilizado para vincular la empresa (dominio, nombre o sin datos)."""

    estado_resolucion_identidad = Column(String(64), nullable=True)
    """Clasificación de resolución de identidad (completa, parcial o anónima)."""

    tipo_encuesta = Column(String(64), nullable=True)
    """Tipología del instrumento (ENCUESTA_POST_EVENTO_SATISFACCION_1_5)."""

    pregunta_recomendacion_nps_0_10 = Column(Float, nullable=True)
    """Calificación de recomendación NPS en escala 0 a 10 cuando esté disponible."""

    categoria_nps_0_10 = Column(String(64), nullable=True)
    """Categoría NPS 0-10 (Promotor, Pasivo, Detractor o NO_DISPONIBLE_ESCALA_1_5)."""
