"""Modelos SQLAlchemy ORM para las capas Silver, Gold y Audit del modelo Medallion."""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text

from app.database import Base


class SilverDimKam(Base):  # type: ignore[misc,valid-type]
    """Dimensión de ejecutivas KAM en la capa Silver."""

    __tablename__ = "silver_dim_kams"

    kam_id = Column(String(64), primary_key=True)
    kam_etiqueta_original = Column(String(128), nullable=True)
    responsable_nombre = Column(String(128), nullable=True)
    tiene_seguimiento_eventos = Column(Boolean, nullable=False, default=False)
    es_kam_asignado = Column(Boolean, nullable=False, default=False)


class SilverDimEmpresa(Base):  # type: ignore[misc,valid-type]
    """Dimensión de empresas afiliadas y prospectos en la capa Silver."""

    __tablename__ = "silver_dim_empresas"

    id_empresa = Column(String(64), primary_key=True)
    id_registro_crm = Column(String(128), nullable=True)
    kam_id = Column(String(64), ForeignKey("silver_dim_kams.kam_id"), nullable=False)
    kam_valor_original = Column(String(128), nullable=True)
    es_empresa_activa = Column(Boolean, nullable=False, default=False)
    es_membresia_activa = Column(Boolean, nullable=False, default=False)
    estado_membresia_detalle = Column(String(128), nullable=True)
    segmento_membresia = Column(String(128), nullable=True)
    nivel_membresia = Column(String(128), nullable=True)
    tipo_membresia_original = Column(String(128), nullable=True)
    categoria_membresia_original = Column(String(128), nullable=True)
    sector_economico = Column(String(256), nullable=True)
    subsector_economico = Column(String(256), nullable=True)
    tamano_empresa = Column(String(128), nullable=True)
    rango_empleados = Column(String(128), nullable=True)
    porcentaje_mujeres_num = Column(Float, nullable=True)
    ciudad = Column(String(128), nullable=True)
    region_departamento = Column(String(128), nullable=True)
    pais = Column(String(128), nullable=True)
    fecha_afiliacion = Column(String(32), nullable=True)
    fecha_expiracion = Column(String(32), nullable=True)
    fecha_miembro_desde = Column(String(32), nullable=True)
    fecha_ultima_actividad = Column(String(32), nullable=True)
    fecha_hora_ultima_actividad = Column(String(64), nullable=True)
    fecha_cambio_registro = Column(String(32), nullable=True)
    fecha_hora_cambio_registro = Column(String(64), nullable=True)
    es_independiente = Column(Boolean, nullable=True)
    es_registro_prueba = Column(Boolean, nullable=True)
    bloqueado_crm = Column(Boolean, nullable=True)
    vinculado_comunidades = Column(Boolean, nullable=True)
    pilar_hr_estrategico = Column(Boolean, nullable=True)
    pilar_mas_que_salario = Column(Boolean, nullable=True)
    pilar_talento_que_elige = Column(Boolean, nullable=True)
    pilar_gente_que_crece = Column(Boolean, nullable=True)
    comunidad_mujeres_hr = Column(Boolean, nullable=True)
    es_influenciador = Column(Boolean, nullable=True)
    en_crm_afiliados = Column(Boolean, nullable=False, default=False)


class SilverDimEmpresaScd2(Base):  # type: ignore[misc,valid-type]
    """Dimensión histórica SCD Tipo 2 de membresías de empresas en Silver."""

    __tablename__ = "silver_dim_empresas_scd2"

    sk_empresa_scd2 = Column(String(64), primary_key=True)
    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), nullable=False
    )
    id_registro_crm = Column(String(128), nullable=True)
    kam_id = Column(String(64), ForeignKey("silver_dim_kams.kam_id"), nullable=False)
    es_empresa_activa = Column(Boolean, nullable=False, default=False)
    es_membresia_activa = Column(Boolean, nullable=False, default=False)
    estado_membresia_detalle = Column(String(128), nullable=True)
    tipo_membresia_original = Column(String(128), nullable=True)
    categoria_membresia_original = Column(String(128), nullable=True)
    fecha_inicio_vigencia = Column(String(32), nullable=True)
    fecha_fin_vigencia = Column(String(32), nullable=True)
    fecha_miembro_desde_crm = Column(String(32), nullable=True)
    es_registro_actual = Column(Boolean, nullable=False, default=True)
    fuente_version = Column(String(128), nullable=True)
    version_registro = Column(Integer, nullable=False, default=1)
    total_versiones_empresa = Column(Integer, nullable=False, default=1)
    tiene_fechas_inconsistentes = Column(Boolean, nullable=False, default=False)
    tiene_intervalo_superpuesto = Column(Boolean, nullable=False, default=False)
    clasificacion_historia_scd2 = Column(String(128), nullable=True)
    descripcion_version_scd2 = Column(Text, nullable=True)


class SilverDimPersona(Base):  # type: ignore[misc,valid-type]
    """Dimensión de personas asistentes y encuestadas en la capa Silver."""

    __tablename__ = "silver_dim_personas"

    id_persona = Column(String(64), primary_key=True)
    id_empresa_principal = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), nullable=True
    )
    estado_resolucion_empresa = Column(String(64), nullable=True)
    nivel_cargo = Column(String(128), nullable=True)
    ciudad = Column(String(128), nullable=True)
    es_afiliado_principal_nuevo = Column(Boolean, nullable=False, default=False)
    fecha_afiliacion_nueva = Column(String(32), nullable=True)


class SilverDimEvento(Base):  # type: ignore[misc,valid-type]
    """Dimensión de eventos en la capa Silver."""

    __tablename__ = "silver_dim_eventos"

    id_evento = Column(Integer, primary_key=True)
    archivo_csv = Column(String(256), nullable=True)
    fecha_evento = Column(String(32), nullable=True)
    fecha_inicio_evento = Column(String(32), nullable=True)
    fecha_fin_evento = Column(String(32), nullable=True)
    periodo_mes_iso = Column(String(32), nullable=True)
    nombre_evento = Column(String(256), nullable=True)
    linea_oferta_2027 = Column(String(128), nullable=True)
    experiencia_detalle = Column(String(256), nullable=True)
    modalidad = Column(String(64), nullable=True)
    es_presencial = Column(Boolean, nullable=False, default=False)
    tiene_asistentes_registrados = Column(Boolean, nullable=False, default=False)


class SilverFactAsistencia(Base):  # type: ignore[misc,valid-type]
    """Tabla de hechos de asistencias a eventos en la capa Silver."""

    __tablename__ = "silver_fact_asistencias"

    id_asistencia = Column(String(64), primary_key=True)
    id_evento = Column(
        Integer, ForeignKey("silver_dim_eventos.id_evento"), nullable=False
    )
    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), nullable=True
    )
    id_persona = Column(
        String(64), ForeignKey("silver_dim_personas.id_persona"), nullable=False
    )
    kam_id = Column(String(64), ForeignKey("silver_dim_kams.kam_id"), nullable=False)
    fecha_evento = Column(String(32), nullable=True)
    periodo_mes_iso = Column(String(32), nullable=True)
    nivel_cargo = Column(String(128), nullable=True)
    ciudad_evento = Column(String(128), nullable=True)
    cantidad_inscritos = Column(Integer, nullable=True)
    es_afiliado = Column(Boolean, nullable=True)
    tiene_costo = Column(Boolean, nullable=True)
    autoriza_tratamiento_datos = Column(Boolean, nullable=True)
    confirmado_ubicacion_principal = Column(Boolean, nullable=True)
    reflejado_en_matriz_general = Column(Boolean, nullable=True)
    conteo_empresa_matriz_general = Column(Integer, nullable=True)
    kam_valor_original = Column(String(128), nullable=True)
    tipo_asistencia = Column(String(64), nullable=True)
    modalidad_evento = Column(String(64), nullable=True)
    estado_resolucion_identidad = Column(String(64), nullable=True)


class SilverFactEncuestaSatisfaccion(Base):  # type: ignore[misc,valid-type]
    """Tabla de hechos de encuestas de satisfacción en la capa Silver."""

    __tablename__ = "silver_fact_encuestas_satisfaccion"

    id_respuesta = Column(String(64), primary_key=True)
    modalidad_encuesta = Column(String(64), nullable=True)
    es_modalidad_presencial = Column(Boolean, nullable=True)
    id_evento = Column(Integer, nullable=True)
    fecha_encuesta = Column(String(32), nullable=True)
    periodo_mes_iso = Column(String(32), nullable=True)
    fecha_hora_inicio = Column(String(64), nullable=True)
    fecha_hora_fin = Column(String(64), nullable=True)
    duracion_segundos = Column(Integer, nullable=True)
    calif_locacion_o_plataforma = Column(Integer, nullable=True)
    calif_convocatoria_publicidad = Column(Integer, nullable=True)
    calif_conferencistas = Column(Integer, nullable=True)
    calif_relevancia_temas = Column(Integer, nullable=True)
    promedio_satisfaccion = Column(Float, nullable=True)
    temarios_sugeridos = Column(Text, nullable=True)
    desea_recibir_actualizaciones = Column(Boolean, nullable=True)
    id_persona = Column(
        String(64), ForeignKey("silver_dim_personas.id_persona"), nullable=True
    )
    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), nullable=True
    )
    ciudad = Column(String(128), nullable=True)
    empresa_en_crm = Column(Boolean, nullable=True)
    metodo_asignacion_empresa = Column(String(128), nullable=True)
    estado_resolucion_identidad = Column(String(64), nullable=True)
    tipo_encuesta = Column(String(64), nullable=True)
    pregunta_recomendacion_nps_0_10 = Column(Float, nullable=True)
    categoria_nps_0_10 = Column(String(64), nullable=True)


class SilverFactMovimientoCrm(Base):  # type: ignore[misc,valid-type]
    """Tabla de hechos de movimientos y renovaciones CRM en la capa Silver."""

    __tablename__ = "silver_fact_movimientos_crm"

    id_movimiento = Column(String(64), primary_key=True)
    tipo_movimiento = Column(String(128), nullable=True)
    es_cierre_facturado = Column(Boolean, nullable=True)
    es_renovacion = Column(Boolean, nullable=True)
    fecha_periodo_mes = Column(String(32), nullable=True)
    periodo_mes_iso = Column(String(32), nullable=True)
    fecha_cierre_o_factura = Column(String(32), nullable=True)
    fecha_expiracion_afiliacion = Column(String(32), nullable=True)
    fecha_exportacion_reporte = Column(String(32), nullable=True)
    kam_id = Column(String(64), ForeignKey("silver_dim_kams.kam_id"), nullable=False)
    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), nullable=False
    )
    nivel_membresia = Column(String(128), nullable=True)
    id_persona_contacto = Column(String(64), nullable=True)
    kam_valor_original = Column(String(128), nullable=True)
    estado_afiliacion_empresa = Column(String(128), nullable=True)
    clasificacion_fecha_expiracion = Column(String(128), nullable=True)


class GoldAggParticipacionEmpresa(Base):  # type: ignore[misc,valid-type]
    """Agregación analítica de participación por empresa en la capa Gold."""

    __tablename__ = "gold_agg_participacion_empresa"

    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), primary_key=True
    )
    periodo_analisis = Column(String(32), primary_key=True)
    fecha_corte_referencia = Column(String(32), nullable=True)
    etiqueta_trimestre_calendario = Column(String(64), nullable=True)
    kam_id = Column(String(64), nullable=True)
    es_membresia_activa = Column(Boolean, nullable=True)
    nivel_membresia = Column(String(128), nullable=True)
    total_eventos = Column(Integer, nullable=False, default=0)
    total_asistencias = Column(Integer, nullable=False, default=0)
    personas_distintas_participantes = Column(Integer, nullable=False, default=0)
    ultima_fecha_participacion = Column(String(32), nullable=True)
    primera_fecha_participacion = Column(String(32), nullable=True)
    asistencias_trimestre_calendario = Column(Integer, nullable=False, default=0)
    asistencias_trimestre_operativo = Column(Integer, nullable=False, default=0)
    asistencias_ventana_movil_90d_corte = Column(Integer, nullable=False, default=0)
    asistencias_ventana_movil_90d_ultimo_evento = Column(
        Integer, nullable=False, default=0
    )
    participacion_linea_anticipar = Column(Integer, nullable=False, default=0)
    participacion_linea_evento_grande = Column(Integer, nullable=False, default=0)
    participacion_linea_foro = Column(Integer, nullable=False, default=0)
    participacion_linea_pares = Column(Integer, nullable=False, default=0)
    participacion_modalidad_presencial = Column(Integer, nullable=False, default=0)
    participacion_modalidad_virtual = Column(Integer, nullable=False, default=0)
    participacion_modalidad_hibrido = Column(Integer, nullable=False, default=0)
    dias_sin_participacion = Column(Float, nullable=True)
    meses_sin_participacion = Column(Float, nullable=True)
    estado_recencia_participacion = Column(String(64), nullable=True)


class GoldAggSatisfaccionEncuestas(Base):  # type: ignore[misc,valid-type]
    """Agregación analítica de satisfacción por modalidad y mes en la capa Gold."""

    __tablename__ = "gold_agg_satisfaccion_encuestas"

    modalidad_encuesta = Column(String(64), primary_key=True)
    periodo_mes_iso = Column(String(32), primary_key=True)
    total_respuestas = Column(Integer, nullable=False, default=0)
    respuestas_con_empresa_resuelta = Column(Integer, nullable=False, default=0)
    respuestas_sin_empresa = Column(Integer, nullable=False, default=0)
    respuestas_anonimas_sin_persona = Column(Integer, nullable=False, default=0)
    promedio_satisfaccion_general_1_5 = Column(Float, nullable=True)
    promedio_locacion_plataforma_1_5 = Column(Float, nullable=True)
    promedio_convocatoria_1_5 = Column(Float, nullable=True)
    promedio_conferencistas_1_5 = Column(Float, nullable=True)
    promedio_relevancia_temas_1_5 = Column(Float, nullable=True)
    calificaciones_altas_475_a_500 = Column(Integer, nullable=False, default=0)
    calificaciones_medias_375_a_474 = Column(Integer, nullable=False, default=0)
    calificaciones_bajas_menores_375 = Column(Integer, nullable=False, default=0)
    promotores_nps_0_10 = Column(Float, nullable=True)
    pasivos_nps_0_10 = Column(Float, nullable=True)
    detractores_nps_0_10 = Column(Float, nullable=True)
    nps_oficial_0_10 = Column(Float, nullable=True)
    estado_calculo_nps = Column(String(128), nullable=True)
    asociacion_evento_origen = Column(String(128), nullable=True)


class GoldAggRetencionEmpresa(Base):  # type: ignore[misc,valid-type]
    """Agregación analítica de retención y semáforo de riesgo por empresa en Gold."""

    __tablename__ = "gold_agg_retencion_empresa"

    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), primary_key=True
    )
    kam_id = Column(String(64), nullable=True)
    en_crm_afiliados = Column(Boolean, nullable=True)
    es_empresa_activa = Column(Boolean, nullable=True)
    es_membresia_activa = Column(Boolean, nullable=True)
    estado_membresia_detalle = Column(String(128), nullable=True)
    segmento_membresia = Column(String(128), nullable=True)
    nivel_membresia = Column(String(128), nullable=True)
    fecha_afiliacion = Column(String(32), nullable=True)
    fecha_expiracion = Column(String(32), nullable=True)
    fecha_ultima_actividad = Column(String(32), nullable=True)
    renovaciones_registradas_2026 = Column(Integer, nullable=False, default=0)
    estados_inactivos_historicos_scd2 = Column(Integer, nullable=False, default=0)
    numero_retiros_historicos = Column(Integer, nullable=False, default=0)
    total_eventos = Column(Integer, nullable=False, default=0)
    total_asistencias = Column(Integer, nullable=False, default=0)
    personas_distintas_participantes = Column(Integer, nullable=False, default=0)
    asistencias_trimestre_calendario = Column(Integer, nullable=False, default=0)
    asistencias_trimestre_operativo = Column(Integer, nullable=False, default=0)
    asistencias_ventana_movil_90d_corte = Column(Integer, nullable=False, default=0)
    asistencias_ventana_movil_90d_ultimo_evento = Column(
        Integer, nullable=False, default=0
    )
    ultima_fecha_participacion = Column(String(32), nullable=True)
    dias_sin_participacion = Column(Float, nullable=True)
    meses_sin_participacion = Column(Float, nullable=True)
    estado_recencia_participacion = Column(String(64), nullable=True)
    respuestas_encuestas_total = Column(Integer, nullable=False, default=0)
    satisfaccion_promedio_1_5 = Column(Float, nullable=True)
    satisfaccion_reciente_1_5 = Column(Float, nullable=True)
    fecha_ultima_encuesta = Column(String(32), nullable=True)
    en_seguimiento_kam = Column(Boolean, nullable=True)
    asistio_segun_kam = Column(Boolean, nullable=True)
    eventos_reportados_kam = Column(Float, nullable=True)
    es_retiro_definitivo_actual = Column(Boolean, nullable=True)
    fecha_ultima_interaccion_global = Column(String(32), nullable=True)
    dias_para_expiracion = Column(Float, nullable=True)
    es_membresia_vencida = Column(Boolean, nullable=True)
    es_proximo_vencimiento_30d = Column(Boolean, nullable=True)
    es_proximo_vencimiento_60d = Column(Boolean, nullable=True)
    es_proximo_vencimiento_90d = Column(Boolean, nullable=True)
    estado_vigencia_expiracion = Column(String(64), nullable=True)
    alerta_membresia_vencida = Column(Boolean, nullable=True)
    alerta_proximo_vencimiento_90d = Column(Boolean, nullable=True)
    alerta_baja_participacion = Column(Boolean, nullable=True)
    alerta_baja_satisfaccion = Column(Boolean, nullable=True)
    alerta_monocontacto = Column(Boolean, nullable=True)
    puntaje_heuristico_riesgo = Column(Integer, nullable=False, default=0)
    semaforo_riesgo_renovacion = Column(String(64), nullable=True)
    tipo_metodologia_riesgo = Column(String(128), nullable=True)


class AuditHashFuenteBronze(Base):  # type: ignore[misc,valid-type]
    """Registro de auditoría de hashes SHA-256 de archivos en la capa Bronze."""

    __tablename__ = "audit_hashes_fuentes_bronze"

    tabla_fuente = Column(String(128), primary_key=True)
    id_ejecucion = Column(String(128), nullable=True)
    fecha_hora_ingesta = Column(String(64), nullable=True)
    archivo_nombre = Column(String(256), nullable=True)
    bytes_origen = Column(Integer, nullable=True)
    filas_leidas = Column(Integer, nullable=True)
    columnas_leidas = Column(Integer, nullable=True)
    sha256_origen = Column(String(64), nullable=True)
    sha256_bronze = Column(String(64), nullable=True)
    integridad_verificada = Column(Boolean, nullable=True)
    accion_bronze = Column(String(128), nullable=True)


class AuditRegistroDuplicado(Base):  # type: ignore[misc,valid-type]
    """Registro de auditoría de los 122 duplicados identificados y clasificados."""

    __tablename__ = "audit_registros_duplicados"

    id_duplicado = Column(String(64), primary_key=True)
    tabla_normalizada_afectada = Column(String(128), nullable=True)
    archivo_origen_csv = Column(String(256), nullable=True)
    fila_origen_csv = Column(Integer, nullable=True)
    tipo_duplicado = Column(String(256), nullable=True)
    llave_negocio = Column(String(256), nullable=True)
    id_empresa = Column(String(64), nullable=True)
    id_persona = Column(String(64), nullable=True)
    id_evento = Column(Float, nullable=True)
    fecha_iso = Column(String(32), nullable=True)
    regla_identificacion = Column(Text, nullable=True)
    detalle_primera_aparicion = Column(Text, nullable=True)
    detalle_duplicado = Column(Text, nullable=True)
    categoria_duplicidad = Column(String(128), nullable=True)
    id_registro_conservado = Column(String(128), nullable=True)
    fecha_deteccion = Column(String(32), nullable=True)
    estado_revision = Column(String(128), nullable=True)
    accion_aplicada = Column(String(128), nullable=True)


class AuditRegistroRechazado(Base):  # type: ignore[misc,valid-type]
    """Registro de auditoría de filas rechazadas durante la validación Silver."""

    __tablename__ = "audit_registros_rechazados"

    id_rechazo = Column(String(64), primary_key=True)
    id_ejecucion = Column(String(128), nullable=True)
    tabla_destino = Column(String(128), nullable=True)
    archivo_origen_bronze = Column(String(256), nullable=True)
    motivo_rechazo = Column(Text, nullable=True)
    registro_original_json = Column(Text, nullable=True)
    fecha_corte_modelo = Column(String(32), nullable=True)


class AuditCalidadDatos(Base):  # type: ignore[misc,valid-type]
    """Registro de reglas e incidencias de calidad de datos aplicadas."""

    __tablename__ = "audit_calidad_datos"

    id_incidencia = Column(String(64), primary_key=True)
    tabla_analizada = Column(String(128), nullable=True)
    campo_afectado = Column(String(256), nullable=True)
    tipo_inconsistencia = Column(String(128), nullable=True)
    registros_afectados = Column(Integer, nullable=True)
    valor_original = Column(Text, nullable=True)
    valor_corregido = Column(Text, nullable=True)
    fecha_corte_modelo = Column(String(32), nullable=True)
    estado_resolucion = Column(String(128), nullable=True)


class AuditReconciliacionOrigenDestino(Base):  # type: ignore[misc,valid-type]
    """Registro de reconciliación de conteos entre las capas Bronze y Silver."""

    __tablename__ = "audit_reconciliacion_origen_destino"

    Tabla = Column(String(128), primary_key=True)
    Filas_Bronze = Column(Integer, nullable=True)
    Cols_Bronze = Column(Integer, nullable=True)
    Filas_Silver = Column(Integer, nullable=True)
    Cols_Silver = Column(Integer, nullable=True)
    Filas_Rechazadas = Column(Integer, nullable=True)
    Diferencia_Filas = Column(Integer, nullable=True)
    Explicacion_Reconciliacion = Column(Text, nullable=True)


class AuditCarga(Base):  # type: ignore[misc,valid-type]
    """Registro de metadatos operativos por tabla cargada en el pipeline ETL."""

    __tablename__ = "audit_cargas"

    id_ejecucion = Column(String(128), primary_key=True)
    fuente = Column(String(256), primary_key=True)
    fecha_inicio = Column(String(64), nullable=True)
    fecha_finalizacion = Column(String(64), nullable=True)
    registros_leidos = Column(Integer, nullable=True)
    registros_procesados = Column(Integer, nullable=True)
    registros_insertados = Column(Integer, nullable=True)
    registros_actualizados = Column(Integer, nullable=True)
    registros_rechazados = Column(Integer, nullable=True)
    estado_ejecucion = Column(String(64), nullable=True)


class AuditEjecucionEtl(Base):  # type: ignore[misc,valid-type]
    """Resumen consolidado de auditoría por ejecución del pipeline Medallion."""

    __tablename__ = "audit_ejecuciones_etl"

    id_ejecucion = Column(String(128), primary_key=True)
    fecha_inicio = Column(String(64), nullable=False)
    fecha_finalizacion = Column(String(64), nullable=False)
    archivos_procesados = Column(Integer, nullable=False, default=0)
    registros_leidos = Column(Integer, nullable=False, default=0)
    registros_cargados = Column(Integer, nullable=False, default=0)
    registros_rechazados = Column(Integer, nullable=False, default=0)
    duplicados_identificados = Column(Integer, nullable=False, default=0)
    errores = Column(Text, nullable=True)
    estado_ejecucion = Column(String(64), nullable=False)
