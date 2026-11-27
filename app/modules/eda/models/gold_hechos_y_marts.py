"""Modelos SQLAlchemy ORM para hechos analíticos BI y evolución mensual en Gold."""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text

from app.database import Base


class GoldFactAsistenciasBi(Base):  # type: ignore[misc,valid-type]
    """Hecho analítico enriquecido de asistencias para filtros cruzados BI."""

    __tablename__ = "gold_fact_asistencias_bi"

    id_asistencia = Column(String(64), primary_key=True)
    """Clave primaria del registro de asistencia."""

    id_evento = Column(
        Integer,
        ForeignKey("gold_dim_evento_kpis.id_evento"),
        nullable=False,
        index=True,
    )
    """Clave foránea hacia gold_dim_evento_kpis."""

    id_empresa = Column(
        String(64),
        ForeignKey("gold_dim_empresa_360.id_empresa"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia gold_dim_empresa_360."""

    id_persona = Column(String(64), nullable=True, index=True)
    """Identificador del participante para conteos COUNT DISTINCT."""

    id_vinculo = Column(Integer, nullable=True)
    """Identificador del vínculo persona-empresa cuando aplica."""

    kam_id_asistencia = Column(String(64), nullable=True)
    """Ejecutiva KAM reportada en la asistencia."""

    fecha_inicio_evento = Column(String(32), nullable=False)
    """Fecha ISO del evento."""

    periodo_mes_iso = Column(String(32), nullable=False, index=True)
    """Periodo mensual YYYY-MM."""

    trimestre_iso = Column(String(32), nullable=False)
    """Trimestre calendario YYYY-Qn."""

    linea_oferta_2027 = Column(String(128), nullable=False)
    """Línea 2027 del evento."""

    modalidad = Column(String(64), nullable=False)
    """Modalidad del evento."""

    tipo_asistencia = Column(String(64), nullable=False)
    """Clasificación ('Afiliado' o 'No Afiliado / Invitado')."""

    nivel_cargo_evento = Column(String(128), nullable=True)
    """Cargo del asistente en el evento."""

    nombre_ciudad_asistente = Column(String(128), nullable=True)
    """Ciudad asociada al asistente."""

    cantidad_inscritos_prov = Column(Integer, nullable=True)
    """Cupos inscritos provisionales."""

    tiene_costo = Column(Boolean, nullable=True)
    """Indica si tuvo costo."""

    autoriza_tratamiento_datos = Column(Boolean, nullable=True)
    """Autorización de tratamiento de datos personales."""


class GoldFactEncuestasBi(Base):  # type: ignore[misc,valid-type]
    """Hecho analítico enriquecido de encuestas para promedios ponderados y NLP."""

    __tablename__ = "gold_fact_encuestas_bi"

    id_respuesta = Column(String(64), primary_key=True)
    """Clave primaria de la respuesta de encuesta."""

    id_evento = Column(
        Integer,
        ForeignKey("gold_dim_evento_kpis.id_evento"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia gold_dim_evento_kpis."""

    id_empresa = Column(
        String(64),
        ForeignKey("gold_dim_empresa_360.id_empresa"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia gold_dim_empresa_360."""

    id_persona = Column(String(64), nullable=True)
    """Identificador de la persona encuestada cuando no es anónima."""

    fecha_encuesta = Column(String(32), nullable=False)
    """Fecha ISO de respuesta."""

    periodo_mes_iso = Column(String(32), nullable=False, index=True)
    """Periodo mensual YYYY-MM."""

    trimestre_iso = Column(String(32), nullable=False)
    """Trimestre calendario YYYY-Qn."""

    tipo_encuesta = Column(String(64), nullable=False, index=True)
    """Tipo ('POST_EVENTO' o 'ENCUESTA_90_DIAS')."""

    modalidad_encuesta = Column(String(64), nullable=False, index=True)
    """Modalidad ('Presencial' o 'Virtual')."""

    nombre_ciudad_encuesta = Column(String(128), nullable=True)
    """Ciudad asociada a la respuesta."""

    calif_locacion_o_plataforma = Column(Integer, nullable=True)
    """Calificación Likert 1-5 de locación o plataforma."""

    calif_convocatoria_publicidad = Column(Integer, nullable=True)
    """Calificación Likert 1-5 de convocatoria."""

    calif_conferencistas = Column(Integer, nullable=True)
    """Calificación Likert 1-5 de conferencistas."""

    calif_relevancia_temas = Column(Integer, nullable=True)
    """Calificación Likert 1-5 de relevancia temática."""

    promedio_respuesta_1_5 = Column(Float, nullable=True)
    """Promedio individual de la respuesta (1.0 a 5.0)."""

    nivel_satisfaccion_1_5 = Column(String(32), nullable=True)
    """Tramo Likert ('ALTA', 'MEDIA' o 'BAJA')."""

    pregunta_recomendacion_nps_0_10 = Column(Integer, nullable=True)
    """Puntaje entero NPS oficial (0 a 10)."""

    categoria_nps_0_10 = Column(String(32), nullable=True)
    """Categoría NPS oficial ('PROMOTOR', 'PASIVO', 'DETRACTOR')."""

    temarios_sugeridos = Column(Text, nullable=True)
    """Texto abierto sugerido por el encuestado."""

    categoria_tema_nlp = Column(String(128), nullable=True, index=True)
    """Categoría temática clasificada mediante reglas NLP."""

    desea_recibir_actualizaciones = Column(Boolean, nullable=True)
    """Autorización de contacto reportada en encuesta."""


class GoldFactEvolucionMembresiasMes(Base):  # type: ignore[misc,valid-type]
    """Serie mensual aditiva de altas, vencimientos, renovaciones y retiros."""

    __tablename__ = "gold_fact_evolucion_membresias_mes"

    id_evolucion_mes = Column(String(256), primary_key=True)
    """Clave primaria compuesta determinística (periodo::kam::segmento::nivel)."""

    periodo_mes_iso = Column(String(32), nullable=False, index=True)
    """Periodo mensual evaluado YYYY-MM."""

    kam_id = Column(String(64), nullable=False, index=True)
    """Ejecutiva KAM asociada."""

    segmento_membresia = Column(String(128), nullable=False)
    """Segmento comercial de membresía."""

    nivel_membresia = Column(String(128), nullable=False)
    """Nivel comercial de membresía."""

    altas_nuevas_mes = Column(Integer, nullable=False, default=0)
    """Nuevas afiliaciones iniciadas en el mes."""

    vencimientos_programados_mes = Column(Integer, nullable=False, default=0)
    """Membresías con fecha de expiración en el mes."""

    renovaciones_efectivas_mes = Column(Integer, nullable=False, default=0)
    """Renovaciones facturadas en el mes."""

    retiros_cancelaciones_mes = Column(Integer, nullable=False, default=0)
    """Membresías expiradas o canceladas en el mes sin renovación."""


class GoldMartSegmentosComunicaciones(Base):  # type: ignore[misc,valid-type]
    """Tabla Gold con los 8 segmentos accionables y validación Habeas Data."""

    __tablename__ = "gold_mart_segmentos_comunicaciones"

    id_registro_segmento = Column(String(160), primary_key=True)
    """Clave primaria compuesta (segmento::id_empresa::id_persona)."""

    orden_segmento = Column(Integer, nullable=False)
    """Orden numérico oficial del segmento (1 a 8)."""

    segmento_codigo = Column(String(64), nullable=False, index=True)
    """Código técnico del segmento."""

    segmento_nombre = Column(String(128), nullable=False)
    """Nombre legible para comunicaciones."""

    id_empresa = Column(
        String(64),
        ForeignKey("gold_dim_empresa_360.id_empresa"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia gold_dim_empresa_360."""

    id_persona = Column(String(64), nullable=True, index=True)
    """Identificador del contacto resuelto."""

    rol_contacto_resuelto = Column(String(64), nullable=False)
    """Origen del contacto ('CONTACTO_ACTUAL_EMPRESA', 'ASISTENTE', 'ENCUESTADO')."""

    kam_id = Column(String(64), nullable=False, index=True)
    """Ejecutiva KAM responsable."""

    nivel_membresia = Column(String(64), nullable=True)
    """Nivel de membresía cuando aplica."""

    sector_economico = Column(String(256), nullable=True)
    """Sector económico de la empresa."""

    nombre_ciudad = Column(String(128), nullable=True)
    """Ciudad asociada al destinatario."""

    semaforo_riesgo_renovacion = Column(String(32), nullable=True)
    """Semáforo de riesgo de la empresa."""

    linea_2027_recomendada_ml = Column(String(128), nullable=True)
    """Línea 2027 sugerida por el recomendador ML."""

    categoria_tema_interes = Column(String(128), nullable=True)
    """Tema o línea de interés específico."""

    detalle_criterio = Column(Text, nullable=False)
    """Justificación de inclusión en el segmento."""

    autoriza_tratamiento_datos = Column(Boolean, nullable=True)
    """Estado conocido de autorización de datos personales."""

    apto_envio_comunicaciones = Column(Boolean, nullable=False, default=False)
    """True únicamente cuando existe autorización explícita verificada."""
