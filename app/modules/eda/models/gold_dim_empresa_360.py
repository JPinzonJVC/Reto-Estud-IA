"""Modelo SQLAlchemy ORM para la dimensión maestra Gold 360 (gold_dim_empresa_360)."""

from typing import Any

from sqlalchemy import Boolean, Column, Float, Integer, String

from app.database import Base


class GoldDimEmpresa360(Base):  # type: ignore[misc,valid-type]
    """Dimensión analítica 360° de empresas con membresía, uso, riesgo y ML."""

    __tablename__ = "gold_dim_empresa_360"

    id_empresa: Any = Column(String(64), primary_key=True)
    """Identificador único de la organización."""

    tipo_relacion_actho: Any = Column(String(64), nullable=False, index=True)
    """Población ('AFILIADO_ACTIVO', 'EX_AFILIADO', 'PROSPECTO_NO_AFILIADO')."""

    kam_id: Any = Column(String(64), nullable=False, index=True)
    """Identificador de la ejecutiva KAM asignada."""

    responsable_kam: Any = Column(String(128), nullable=False)
    """Nombre legible de la ejecutiva KAM."""

    kam_con_seguimiento: Any = Column(Boolean, nullable=False, default=False)
    """Indica si la KAM tiene portafolio activo de seguimiento a eventos."""

    id_membresia_actual: Any = Column(String(64), nullable=True)
    """Identificador del último ciclo de membresía registrado."""

    estado_membresia_detalle: Any = Column(String(128), nullable=False)
    """Estado detallado vigente de la membresía."""

    es_membresia_activa: Any = Column(Boolean, nullable=False, default=False)
    """Indica si la empresa tiene una membresía activa actualmente."""

    segmento_membresia: Any = Column(String(128), nullable=True)
    """Segmento o tipo comercial de la membresía."""

    nivel_membresia: Any = Column(String(128), nullable=True, index=True)
    """Nivel homologado de membresía (Estándar, Premium, Elite, Personal)."""

    sector_economico: Any = Column(String(256), nullable=True, index=True)
    """Sector económico de la organización."""

    subsector_economico: Any = Column(String(256), nullable=True)
    """Subsector económico de la organización."""

    tamano_empresa: Any = Column(String(128), nullable=True)
    """Tamaño empresarial (Grande, Mediana, Pequeña, Micro)."""

    rango_empleados: Any = Column(String(128), nullable=True)
    """Rango de cantidad de colaboradores."""

    porcentaje_mujeres_num: Any = Column(Float, nullable=True)
    """Porcentaje de participación femenina."""

    nombre_ciudad: Any = Column(String(128), nullable=True, index=True)
    """Ciudad sede de la empresa desnormalizada desde geografía Silver."""

    nombre_departamento: Any = Column(String(128), nullable=True)
    """Departamento o región de la empresa."""

    nombre_pais: Any = Column(String(128), nullable=True)
    """País sede de la empresa."""

    fecha_miembro_desde: Any = Column(String(32), nullable=True)
    """Fecha histórica de antigüedad en ACTHO."""

    fecha_afiliacion_actual: Any = Column(String(32), nullable=True)
    """Fecha de inicio de la afiliación actual."""

    fecha_inicio_vigencia: Any = Column(String(32), nullable=True)
    """Fecha de inicio del ciclo vigente."""

    fecha_fin_vigencia: Any = Column(String(32), nullable=True)
    """Fecha de expiración del ciclo vigente."""

    dias_para_expiracion: Any = Column(Float, nullable=True)
    """Días restantes hasta la fecha de expiración respecto al corte."""

    tramo_vencimiento: Any = Column(String(64), nullable=False)
    """Tramo ('VENCIDA', '0_30D', '31_60D', '61_90D', 'MAS_90D', 'SIN_MEMBRESIA')."""

    total_ciclos_membresia: Any = Column(Integer, nullable=False, default=0)
    """Cantidad de ciclos reales de membresía en silver_membresias."""

    total_eventos_anio: Any = Column(Integer, nullable=False, default=0)
    """Eventos únicos en los que participó la empresa."""

    total_asistencias_anio: Any = Column(Integer, nullable=False, default=0)
    """Registros totales de asistencia de la empresa."""

    personas_distintas_anio: Any = Column(Integer, nullable=False, default=0)
    """Personas distintas que asistieron por la empresa."""

    asistencias_ultimo_trimestre: Any = Column(Integer, nullable=False, default=0)
    """Asistencias durante el trimestre operativo evaluado."""

    dias_sin_participacion: Any = Column(Float, nullable=True)
    """Días transcurridos desde la última asistencia a eventos."""

    total_encuestas_respondidas: Any = Column(Integer, nullable=False, default=0)
    """Respuestas de encuesta vinculadas a la empresa."""

    satisfaccion_promedio_1_5: Any = Column(Float, nullable=True)
    """Promedio ponderado real de satisfacción en escala Likert 1 a 5."""

    satisfaccion_reciente_1_5: Any = Column(Float, nullable=True)
    """Calificación promedio de la respuesta más reciente (1 a 5)."""

    nps_reciente_0_10: Any = Column(Integer, nullable=True)
    """Calificación reciente de recomendación NPS (0 a 10) cuando aplique."""

    alerta_vencimiento_90d: Any = Column(Boolean, nullable=False, default=False)
    """Indica si la membresía está vencida o vence en <= 90 días."""

    alerta_sin_participacion_trimestre: Any = Column(
        Boolean, nullable=False, default=False
    )
    """Indica ausencia de asistencias en el último trimestre."""

    alerta_baja_satisfaccion: Any = Column(Boolean, nullable=False, default=False)
    """Indica calificación reciente inferior a 3.75."""

    alerta_monocontacto: Any = Column(Boolean, nullable=False, default=False)
    """Indica que solo una única persona ha participado por la empresa."""

    puntaje_riesgo_heuristico: Any = Column(Integer, nullable=True)
    """Puntaje explicable de riesgo (solo poblado en AFILIADO_ACTIVO)."""

    probabilidad_churn_ml: Any = Column(Float, nullable=True)
    """Probabilidad calibrada ML de no renovación (0.0 a 1.0)."""

    semaforo_riesgo_renovacion: Any = Column(String(32), nullable=False, index=True)
    """Semáforo híbrido ('ROJO', 'AMARILLO', 'VERDE' o 'NO_APLICA')."""

    score_fidelidad_ml_0_100: Any = Column(Float, nullable=True)
    """Índice compuesto RFM-S de fidelidad (0 a 100)."""

    arquetipo_fidelidad_ml: Any = Column(String(64), nullable=True)
    """Cluster de fidelidad ('Embajador', 'Fiel Focalizado', 'Nuevo Prometedor', etc.)."""

    score_conversion_lead_ml_0_100: Any = Column(Float, nullable=True)
    """Propensión ML de afiliación (0 a 100) para leads y ex-afiliados."""

    linea_2027_mayor_participacion: Any = Column(String(128), nullable=True)
    """Línea 2027 con mayor asistencia histórica observada."""

    linea_2027_recomendada_ml: Any = Column(String(128), nullable=True)
    """Línea 2027 recomendada por afinidad colaborativa y temas NLP."""

    prob_asistencia_prox_evento_ml: Any = Column(Float, nullable=True)
    """Probabilidad ML estimada de asistencia a próximos espacios."""
