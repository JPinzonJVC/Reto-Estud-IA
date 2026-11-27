"""Modelo SQLAlchemy ORM para KPIs por evento (gold_dim_evento_kpis)."""

from sqlalchemy import Column, Float, Integer, String

from app.database import Base


class GoldDimEventoKpis(Base):  # type: ignore[misc,valid-type]
    """Dimensión analítica de eventos con KPIs de convocatoria y niveles de cargo."""

    __tablename__ = "gold_dim_evento_kpis"

    id_evento = Column(Integer, primary_key=True)
    """Identificador entero único del evento."""

    nombre_evento = Column(String(256), nullable=False)
    """Nombre oficial del evento."""

    fecha_inicio_evento = Column(String(32), nullable=False)
    """Fecha ISO YYYY-MM-DD de inicio."""

    fecha_fin_evento = Column(String(32), nullable=False)
    """Fecha ISO YYYY-MM-DD de fin."""

    periodo_mes_iso = Column(String(32), nullable=False, index=True)
    """Mes del evento en formato YYYY-MM."""

    trimestre_iso = Column(String(32), nullable=False)
    """Trimestre calendario del evento (YYYY-Qn)."""

    linea_oferta_2027 = Column(String(128), nullable=False, index=True)
    """Línea estratégica 2027 (Anticipar, Evento grande, Foro, Pares)."""

    experiencia_detalle = Column(String(256), nullable=True)
    """Formato detallado de la experiencia."""

    modalidad = Column(String(64), nullable=False)
    """Modalidad (Presencial, Virtual o Híbrido)."""

    nombre_ciudad_evento = Column(String(128), nullable=True)
    """Ciudad sede cuando el evento es presencial."""

    total_registros_asistencia = Column(Integer, nullable=False, default=0)
    """Total de registros individuales de asistencia."""

    total_cupos_inscritos_prov = Column(Integer, nullable=False, default=0)
    """Suma provisional del campo cantidad_inscritos."""

    personas_unicas_evento = Column(Integer, nullable=False, default=0)
    """Personas distintas participantes en el evento (no aditivo entre eventos)."""

    empresas_unicas_evento = Column(Integer, nullable=False, default=0)
    """Empresas distintas representadas en el evento (no aditivo entre eventos)."""

    asistentes_afiliados = Column(Integer, nullable=False, default=0)
    """Registros de asistencia de afiliados."""

    asistentes_no_afiliados = Column(Integer, nullable=False, default=0)
    """Registros de asistencia de no afiliados (leads)."""

    tasa_penetracion_afiliados_pct = Column(Float, nullable=False, default=0.0)
    """Porcentaje de empresas afiliadas activas que participaron en el evento."""

    cargos_alta_direccion = Column(Integer, nullable=False, default=0)
    """Asistentes de Alta Dirección (C-level / VP)."""

    cargos_direccion_gerencia = Column(Integer, nullable=False, default=0)
    """Asistentes de Dirección o Gerencia."""

    cargos_jefatura_coordinacion = Column(Integer, nullable=False, default=0)
    """Asistentes de Jefatura o Coordinación."""

    cargos_profesional_analista = Column(Integer, nullable=False, default=0)
    """Asistentes de nivel Profesional, Analista o Consultor."""

    cargos_otro_sin_dato = Column(Integer, nullable=False, default=0)
    """Asistentes con otro cargo o sin dato reportado."""

    satisfaccion_promedio_evento_1_5 = Column(Float, nullable=True)
    """Promedio de satisfacción 1 a 5 cuando existan encuestas con id_evento."""

    nps_evento_0_10 = Column(Float, nullable=True)
    """Puntaje NPS oficial (-100 a +100) del evento cuando aplique."""
