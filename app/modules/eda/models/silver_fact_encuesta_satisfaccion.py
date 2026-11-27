"""Modelo SQLAlchemy ORM para encuestas (silver_fact_encuestas_satisfaccion)."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text

from app.database import Base


class SilverFactEncuestaSatisfaccion(Base):  # type: ignore[misc,valid-type]
    """Tabla de hechos de respuestas individuales a encuestas en Silver."""

    __tablename__ = "silver_fact_encuestas_satisfaccion"

    id_respuesta = Column(String(64), primary_key=True)
    """Identificador único de la respuesta (EP-xxxx o EV-xxxx)."""

    id_evento = Column(
        Integer,
        ForeignKey("silver_dim_eventos.id_evento"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia el evento (NULL en fuentes sin captura)."""

    id_persona = Column(
        String(64),
        ForeignKey("silver_dim_personas.id_persona"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia la persona (NULL en encuestas anónimas)."""

    id_empresa = Column(
        String(64),
        ForeignKey("silver_dim_empresas.id_empresa"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia la empresa cuando existe asociación confiable."""

    id_ciudad_encuesta = Column(
        Integer,
        ForeignKey("silver_dim_ciudad.id_ciudad"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia la ciudad reportada en la respuesta."""

    fecha_encuesta = Column(String(32), nullable=False)
    """Fecha ISO YYYY-MM-DD de diligenciamiento de la encuesta."""

    modalidad_encuesta = Column(String(64), nullable=False)
    """Modalidad del instrumento ('Presencial' o 'Virtual')."""

    tipo_encuesta = Column(String(64), nullable=False)
    """Tipología de la encuesta ('POST_EVENTO' o 'ENCUESTA_90_DIAS')."""

    duracion_segundos = Column(Integer, nullable=True)
    """Duración en segundos empleada para responder el formulario."""

    calif_locacion_o_plataforma = Column(Integer, nullable=True)
    """Calificación Likert (1 a 5) de locación física o plataforma virtual."""

    calif_convocatoria_publicidad = Column(Integer, nullable=True)
    """Calificación Likert (1 a 5) de convocatoria y publicidad."""

    calif_conferencistas = Column(Integer, nullable=True)
    """Calificación Likert (1 a 5) de conferencistas o panelistas."""

    calif_relevancia_temas = Column(Integer, nullable=True)
    """Calificación Likert (1 a 5) de pertinencia y relevancia de temas."""

    pregunta_recomendacion_nps_0_10 = Column(Integer, nullable=True)
    """Calificación entera (0 a 10) de recomendación NPS cuando esté disponible."""

    temarios_sugeridos = Column(Text, nullable=True)
    """Comentarios abiertos y temas solicitados por el participante."""

    desea_recibir_actualizaciones = Column(Boolean, nullable=True)
    """Indica autorización para recibir comunicaciones y actualizaciones."""
