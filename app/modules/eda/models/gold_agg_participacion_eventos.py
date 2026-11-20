"""Modelo ORM para participación por evento y línea (gold_agg_participacion_eventos)."""

from sqlalchemy import Boolean, Column, Float, Integer, String, Text

from app.database import Base


class GoldAggParticipacionEventos(Base):  # type: ignore[misc,valid-type]
    """Agregación analítica de participación por evento, línea 2027 y modalidad."""

    __tablename__ = "gold_agg_participacion_eventos"

    id_evento = Column(String(64), primary_key=True)
    """Identificador único del evento en la capa Silver."""

    nombre_evento = Column(String(255), nullable=True)
    """Nombre oficial del evento o experiencia."""

    fecha_evento = Column(String(32), nullable=True)
    """Fecha principal del evento en formato ISO YYYY-MM-DD."""

    periodo_mes_iso = Column(String(32), nullable=True)
    """Periodo mensual del evento en formato YYYY-MM."""

    linea_oferta_2027 = Column(String(128), nullable=True)
    """Línea estratégica de oferta 2027 asociada al evento."""

    modalidad = Column(String(64), nullable=True)
    """Modalidad del evento (Presencial, Virtual, Híbrido)."""

    es_presencial = Column(Boolean, nullable=True)
    """Indicador booleano de presencialidad del evento."""

    total_asistencias = Column(Integer, nullable=False, default=0)
    """Cantidad total de registros de asistencia al evento."""

    personas_distintas = Column(Integer, nullable=False, default=0)
    """Cantidad de personas únicas participantes en el evento."""

    empresas_distintas = Column(Integer, nullable=False, default=0)
    """Cantidad de empresas únicas representadas en el evento."""

    asistentes_afiliados = Column(Integer, nullable=False, default=0)
    """Cantidad de asistencias correspondientes a empresas afiliadas."""

    asistentes_no_afiliados = Column(Integer, nullable=False, default=0)
    """Cantidad de asistencias de participantes no afiliados (leads)."""

    empresas_afiliadas_distintas = Column(Integer, nullable=False, default=0)
    """Empresas afiliadas únicas que asistieron al evento."""

    empresas_no_afiliadas_distintas = Column(Integer, nullable=False, default=0)
    """Empresas no afiliadas únicas que asistieron al evento."""

    porcentaje_no_afiliados = Column(Float, nullable=False, default=0.0)
    """Porcentaje de asistencias no afiliadas sobre el total del evento."""

    asistentes_con_autorizacion_datos = Column(Integer, nullable=False, default=0)
    """Cantidad de asistencias con autorización explícita de tratamiento de datos."""

    desglose_niveles_cargo = Column(Text, nullable=True)
    """Resumen en formato JSON con el conteo de asistentes por nivel de cargo."""
