# Diccionario de Datos — Modelo Medallion ACTHO 360 (20 Tablas)

## Capa Silver (Dimensiones y Hechos)

### silver_dim_empresas

Dimensión de empresas afiliadas y prospectos en la capa Silver.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_empresa | String(64), primary_key=True | Identificador único de negocio de la empresa (EMP-xxxx). |
| id_registro_crm | String(128), nullable=True | Identificador del registro vigente en Zoho CRM. |
| kam_id | String(64), ForeignKey('silver_dim_kams.kam_id'), nullable=False | Clave foránea hacia silver_dim_kams con la ejecutiva asignada. |
| kam_valor_original | String(128), nullable=True | Valor textual original de la ejecutiva antes de la homologación. |
| es_empresa_activa | Boolean, nullable=False, default=False | Indica si el estado general de la empresa en CRM es Activo. |
| es_membresia_activa | Boolean, nullable=False, default=False | Indica si la empresa posee una membresía activa vigente. |
| estado_membresia_detalle | String(128), nullable=True | Estado detallado de la membresía (Activo, Cancelado, Expirado, etc.). |
| segmento_membresia | String(128), nullable=True | Segmento comercial de la membresía. |
| nivel_membresia | String(128), nullable=True | Nivel o categoría homologada de la membresía (Elite, Premium, Estándar). |
| tipo_membresia_original | String(128), nullable=True | Tipo de membresía reportado originalmente en el CRM. |
| categoria_membresia_original | String(128), nullable=True | Categoría de membresía reportada originalmente en el CRM. |
| sector_economico | String(256), nullable=True | Sector económico principal de la empresa. |
| subsector_economico | String(256), nullable=True | Subsector económico detallado de la empresa. |
| tamano_empresa | String(128), nullable=True | Clasificación de tamaño empresarial. |
| rango_empleados | String(128), nullable=True | Rango de cantidad de empleados de la organización. |
| porcentaje_mujeres_num | Float, nullable=True | Porcentaje numérico de participación femenina en la empresa. |
| ciudad | String(128), nullable=True | Ciudad principal de ubicación de la empresa. |
| region_departamento | String(128), nullable=True | Departamento o región geográfica de la empresa. |
| pais | String(128), nullable=True | País de ubicación de la empresa. |
| fecha_afiliacion | String(32), nullable=True | Fecha de inicio de la afiliación actual en formato ISO YYYY-MM-DD. |
| fecha_expiracion | String(32), nullable=True | Fecha de expiración de la membresía actual en formato ISO YYYY-MM-DD. |
| fecha_miembro_desde | String(32), nullable=True | Fecha histórica desde la cual la empresa es miembro según el CRM. |
| fecha_ultima_actividad | String(32), nullable=True | Fecha de la última actividad registrada en el CRM (YYYY-MM-DD). |
| fecha_hora_ultima_actividad | String(64), nullable=True | Marca temporal completa de la última actividad en el CRM. |
| fecha_cambio_registro | String(32), nullable=True | Fecha de la última modificación del registro en el CRM. |
| fecha_hora_cambio_registro | String(64), nullable=True | Marca temporal completa de la última modificación en el CRM. |
| es_independiente | Boolean, nullable=True | Indica si el afiliado corresponde a un profesional independiente. |
| es_registro_prueba | Boolean, nullable=True | Indica si el registro está marcado como cuenta de prueba. |
| bloqueado_crm | Boolean, nullable=True | Indica si el registro se encuentra bloqueado en el CRM. |
| vinculado_comunidades | Boolean, nullable=True | Indica si la empresa participa en comunidades especializadas ACTHO. |
| pilar_hr_estrategico | Boolean, nullable=True | Indica vinculación al pilar de HR Estratégico. |
| pilar_mas_que_salario | Boolean, nullable=True | Indica vinculación al pilar Más que Salario. |
| pilar_talento_que_elige | Boolean, nullable=True | Indica vinculación al pilar Talento que Elige. |
| pilar_gente_que_crece | Boolean, nullable=True | Indica vinculación al pilar Gente que Crece. |
| comunidad_mujeres_hr | Boolean, nullable=True | Indica participación en la comunidad de Mujeres en HR. |
| es_influenciador | Boolean, nullable=True | Indica si la cuenta está clasificada como influenciadora. |
| en_crm_afiliados | Boolean, nullable=False, default=False | Indica si la empresa proviene del maestro de afiliados del CRM. |

### silver_dim_empresas_scd2

Dimensión histórica SCD Tipo 2 de membresías de empresas en Silver.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| sk_empresa_scd2 | String(64), primary_key=True | Clave subrogada única de la versión histórica SCD2 (SCD2-EMP-xxxx). |
| id_empresa | String(64), ForeignKey('silver_dim_empresas.id_empresa'), nullable=False | Clave foránea hacia silver_dim_empresas con el identificador de empresa. |
| id_registro_crm | String(128), nullable=True | Identificador del registro específico en la exportación de Zoho CRM. |
| kam_id | String(64), ForeignKey('silver_dim_kams.kam_id'), nullable=False | Clave foránea hacia silver_dim_kams con la ejecutiva asignada. |
| es_empresa_activa | Boolean, nullable=False, default=False | Indica si la empresa estaba activa en esta versión del registro. |
| es_membresia_activa | Boolean, nullable=False, default=False | Indica si la membresía estaba activa en esta versión histórica. |
| estado_membresia_detalle | String(128), nullable=True | Estado detallado de la membresía en la versión correspondiente. |
| tipo_membresia_original | String(128), nullable=True | Tipo de membresía original asociado a la versión. |
| categoria_membresia_original | String(128), nullable=True | Categoría de membresía original asociada a la versión. |
| fecha_inicio_vigencia | String(32), nullable=True | Fecha de inicio de vigencia de la versión (tomada de fecha_afiliacion). |
| fecha_fin_vigencia | String(32), nullable=True | Fecha de fin de vigencia de la versión (tomada de fecha_expiracion). |
| fecha_miembro_desde_crm | String(32), nullable=True | Fecha de antigüedad miembro desde reportada en el CRM. |
| es_registro_actual | Boolean, nullable=False, default=True | Indica si esta fila representa la versión actual vigente de la empresa. |
| fuente_version | String(128), nullable=True | Clasificación del origen de la versión (única, histórica o consolidada). |
| version_registro | Integer, nullable=False, default=1 | Número secuencial de versión (1..N) dentro de cada id_empresa. |
| total_versiones_empresa | Integer, nullable=False, default=1 | Cantidad total de versiones registradas para la empresa. |
| tiene_fechas_inconsistentes | Boolean, nullable=False, default=False | Indica si fecha_inicio_vigencia es mayor que fecha_fin_vigencia en origen. |
| tiene_intervalo_superpuesto | Boolean, nullable=False, default=False | Indica si la empresa presenta solapamiento temporal entre versiones. |
| clasificacion_historia_scd2 | String(128), nullable=True | Diagnóstico de calidad sobre la reconstrucción temporal del intervalo. |
| descripcion_version_scd2 | Text, nullable=True | Descripción legible del estado y posición de la versión histórica. |

### silver_dim_eventos

Dimensión de eventos en la capa Silver.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_evento | Integer, primary_key=True | Identificador numérico único del evento en el catálogo maestro. |
| archivo_csv | String(256), nullable=True | Nombre del archivo CSV original del evento. |
| fecha_evento | String(32), nullable=True | Fecha principal del evento en formato ISO YYYY-MM-DD. |
| fecha_inicio_evento | String(32), nullable=True | Fecha de inicio del evento en formato ISO YYYY-MM-DD. |
| fecha_fin_evento | String(32), nullable=True | Fecha de finalización del evento en formato ISO YYYY-MM-DD. |
| periodo_mes_iso | String(32), nullable=True | Periodo mensual del evento en formato YYYY-MM. |
| nombre_evento | String(256), nullable=True | Nombre descriptivo oficial del evento. |
| linea_oferta_2027 | String(128), nullable=True | Línea de oferta estratégica 2027 (Anticipar, Evento grande, Foro, Pares). |
| experiencia_detalle | String(256), nullable=True | Tipo o formato detallado de la experiencia del evento. |
| modalidad | String(64), nullable=True | Modalidad de ejecución (Presencial, Virtual o Híbrido). |
| es_presencial | Boolean, nullable=False, default=False | Indica si el evento cuenta con componente presencial. |
| tiene_asistentes_registrados | Boolean, nullable=False, default=False | Indica si el evento posee registros de asistencia en los archivos fuente. |

### silver_dim_kams

Dimensión de ejecutivas KAM en la capa Silver.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| kam_id | String(64), primary_key=True | Identificador canónico de la ejecutiva KAM (KAM A..I o KAM-UNASSIGNED). |
| kam_etiqueta_original | String(128), nullable=True | Etiqueta original de la ejecutiva KAM en los archivos fuente. |
| responsable_nombre | String(128), nullable=True | Nombre de la ejecutiva responsable de la cuenta. |
| tiene_seguimiento_eventos | Boolean, nullable=False, default=False | Indica si la ejecutiva cuenta con portafolio de seguimiento de eventos. |
| es_kam_asignado | Boolean, nullable=False, default=False | Indica si corresponde a una ejecutiva asignada (True) o a KAM-UNASSIGNED. |

### silver_dim_personas

Dimensión de personas asistentes y encuestadas en la capa Silver.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_persona | String(64), primary_key=True | Identificador único de la persona (P-xxxx). |
| id_empresa_principal | String(64), ForeignKey('silver_dim_empresas.id_empresa'), nullable=True | Clave foránea opcional hacia la empresa principal de la persona. |
| estado_resolucion_empresa | String(64), nullable=True | Estado de vinculación empresarial (ASOCIADA o SIN_EMPRESA_ASOCIADA). |
| nivel_cargo | String(128), nullable=True | Nivel jerárquico o segmento de cargo del profesional. |
| ciudad | String(128), nullable=True | Ciudad reportada para el profesional. |
| es_afiliado_principal_nuevo | Boolean, nullable=False, default=False | Indica si la persona figura como contacto principal de nueva afiliación. |
| fecha_afiliacion_nueva | String(32), nullable=True | Fecha de nueva afiliación cuando aplica. |

### silver_fact_asistencias

Tabla de hechos de asistencias a eventos en la capa Silver.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_asistencia | String(64), primary_key=True | Identificador único del registro de asistencia (A-xxxxx). |
| id_evento | Integer, ForeignKey('silver_dim_eventos.id_evento'), nullable=False | Clave foránea hacia silver_dim_eventos con el evento asistido. |
| id_empresa | String(64), ForeignKey('silver_dim_empresas.id_empresa'), nullable=True | Clave foránea opcional hacia silver_dim_empresas. |
| id_persona | String(64), ForeignKey('silver_dim_personas.id_persona'), nullable=False | Clave foránea hacia silver_dim_personas con el asistente. |
| kam_id | String(64), ForeignKey('silver_dim_kams.kam_id'), nullable=False | Clave foránea hacia silver_dim_kams con la ejecutiva responsable. |
| fecha_evento | String(32), nullable=True | Fecha del evento asistido en formato ISO YYYY-MM-DD. |
| periodo_mes_iso | String(32), nullable=True | Periodo mensual de la asistencia en formato YYYY-MM. |
| nivel_cargo | String(128), nullable=True | Nivel de cargo del asistente en el momento del evento. |
| ciudad_evento | String(128), nullable=True | Ciudad asociada al registro de asistencia. |
| cantidad_inscritos | Integer, nullable=True | Cantidad de cupos o inscritos reportados en la transacción. |
| es_afiliado | Boolean, nullable=True | Indica si el asistente participaba en calidad de afiliado. |
| tiene_costo | Boolean, nullable=True | Indica si la inscripción tuvo costo asociado. |
| autoriza_tratamiento_datos | Boolean, nullable=True | Indica si el participante autorizó el tratamiento de datos personales. |
| confirmado_ubicacion_principal | Boolean, nullable=True | Indica confirmación de asistencia en la ubicación principal. |
| reflejado_en_matriz_general | Boolean, nullable=True | Indica si la asistencia de la empresa aparece en la matriz consolidada. |
| conteo_empresa_matriz_general | Integer, nullable=True | Conteo reportado para la empresa en la matriz general de asistencia. |
| kam_valor_original | String(128), nullable=True | Valor original del campo KAM antes de la homologación. |
| tipo_asistencia | String(64), nullable=True | Clasificación de asistencia (Afiliado vs No Afiliado / Invitado). |
| modalidad_evento | String(64), nullable=True | Modalidad del evento obtenida del catálogo maestro de eventos. |
| estado_resolucion_identidad | String(64), nullable=True | Estado de resolución de empresa y persona en el registro. |

### silver_fact_encuestas_satisfaccion

Tabla de hechos de encuestas de satisfacción en la capa Silver.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_respuesta | String(64), primary_key=True | Identificador único de la respuesta de encuesta (EP-xxxx o EV-xxxx). |
| modalidad_encuesta | String(64), nullable=True | Modalidad del formulario de encuesta (Presencial o Virtual). |
| es_modalidad_presencial | Boolean, nullable=True | Indica si la encuesta corresponde al formulario de eventos presenciales. |
| id_evento | Integer, nullable=True | Identificador del evento (nulo en fuentes históricas sin captura de evento). |
| fecha_encuesta | String(32), nullable=True | Fecha de diligenciamiento de la encuesta en formato ISO YYYY-MM-DD. |
| periodo_mes_iso | String(32), nullable=True | Periodo mensual de la respuesta en formato YYYY-MM. |
| fecha_hora_inicio | String(64), nullable=True | Marca temporal de inicio de respuesta del formulario. |
| fecha_hora_fin | String(64), nullable=True | Marca temporal de finalización del formulario. |
| duracion_segundos | Integer, nullable=True | Tiempo empleado para responder la encuesta en segundos. |
| calif_locacion_o_plataforma | Integer, nullable=True | Calificación Likert (1 a 5) de la locación física o plataforma virtual. |
| calif_convocatoria_publicidad | Integer, nullable=True | Calificación Likert (1 a 5) del proceso de convocatoria y publicidad. |
| calif_conferencistas | Integer, nullable=True | Calificación Likert (1 a 5) de los conferencistas o panelistas. |
| calif_relevancia_temas | Integer, nullable=True | Calificación Likert (1 a 5) de la pertinencia y relevancia de los temas. |
| promedio_satisfaccion | Float, nullable=True | Promedio aritmético de satisfacción general del encuestado en escala 1 a 5. |
| temarios_sugeridos | Text, nullable=True | Comentarios abiertos o temarios sugeridos por el participante. |
| desea_recibir_actualizaciones | Boolean, nullable=True | Indica si el participante autorizó recibir actualizaciones y dejó sus datos. |
| id_persona | String(64), ForeignKey('silver_dim_personas.id_persona'), nullable=True | Clave foránea opcional hacia silver_dim_personas (nula en anónimas). |
| id_empresa | String(64), ForeignKey('silver_dim_empresas.id_empresa'), nullable=True | Clave foránea opcional hacia silver_dim_empresas. |
| ciudad | String(128), nullable=True | Ciudad asociada al participante encuestado. |
| empresa_en_crm | Boolean, nullable=True | Indica si la empresa identificada existe en el maestro del CRM. |
| metodo_asignacion_empresa | String(128), nullable=True | Método utilizado para vincular la empresa (dominio, nombre o sin datos). |
| estado_resolucion_identidad | String(64), nullable=True | Clasificación de resolución de identidad (completa, parcial o anónima). |
| tipo_encuesta | String(64), nullable=True | Tipología del instrumento (ENCUESTA_POST_EVENTO_SATISFACCION_1_5). |
| categoria_nps_adaptado_1_5 | String(64), nullable=True | Clasificación NPS adaptado 1-5 (PROMOTOR: 4-5, NEUTRO: 3, DETRACTOR: 1-2). |
| pregunta_recomendacion_nps_0_10 | Float, nullable=True | Calificación de recomendación NPS en escala 0 a 10 cuando esté disponible. |
| categoria_nps_0_10 | String(64), nullable=True | Categoría NPS 0-10 (Promotor, Pasivo, Detractor o NO_DISPONIBLE_ESCALA_1_5). |

### silver_fact_movimientos_crm

Tabla de hechos de movimientos y renovaciones CRM en la capa Silver.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_movimiento | String(64), primary_key=True | Clave primaria subrogada del movimiento CRM (MOV-xxxx). |
| tipo_movimiento | String(128), nullable=True | Tipo de operación CRM (Nueva Afiliación, Renovación, Trato en Estado). |
| es_cierre_facturado | Boolean, nullable=True | Indica si el movimiento corresponde a un cierre efectivo facturado. |
| es_renovacion | Boolean, nullable=True | Indica si el movimiento corresponde a una renovación de membresía. |
| fecha_periodo_mes | String(32), nullable=True | Fecha base del periodo mensual reportado. |
| periodo_mes_iso | String(32), nullable=True | Periodo mensual del movimiento en formato ISO YYYY-MM. |
| fecha_cierre_o_factura | String(32), nullable=True | Fecha de cierre o facturación del movimiento en formato YYYY-MM-DD. |
| fecha_expiracion_afiliacion | String(32), nullable=True | Fecha de expiración asociada a la afiliación o renovación. |
| fecha_exportacion_reporte | String(32), nullable=True | Fecha de corte o exportación del reporte fuente de CRM. |
| kam_id | String(64), ForeignKey('silver_dim_kams.kam_id'), nullable=False | Clave foránea hacia silver_dim_kams con la ejecutiva responsable. |
| id_empresa | String(64), ForeignKey('silver_dim_empresas.id_empresa'), nullable=False | Clave foránea hacia silver_dim_empresas con la empresa del movimiento. |
| nivel_membresia | String(128), nullable=True | Nivel o categoría de membresía involucrada en el movimiento. |
| id_persona_contacto | String(64), nullable=True | Identificador de la persona de contacto principal cuando figura en el reporte. |
| kam_valor_original | String(128), nullable=True | Valor original del campo KAM antes de la homologación. |
| estado_afiliacion_empresa | String(128), nullable=True | Estado de afiliación vigente de la empresa en el maestro Silver. |
| clasificacion_fecha_expiracion | String(128), nullable=True | Clasificación de completitud de la fecha de expiración en el movimiento. |

## Capa Gold (Agregaciones y Segmentos)

### gold_agg_participacion_empresa

Agregación analítica de participación por empresa en la capa Gold.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_empresa | String(64), ForeignKey('silver_dim_empresas.id_empresa'), primary_key=True | Clave primaria y foránea hacia silver_dim_empresas. |
| periodo_analisis | String(32), primary_key=True | Etiqueta del periodo consolidado de análisis (ej. 2026-ANUAL). |
| fecha_corte_referencia | String(32), nullable=True | Fecha de corte utilizada como referencia para ventanas móviles y recencia. |
| etiqueta_trimestre_calendario | String(64), nullable=True | Etiqueta del trimestre calendario evaluado (ej. 2026-Q3). |
| kam_id | String(64), nullable=True | Identificador de la ejecutiva KAM asignada a la empresa. |
| es_membresia_activa | Boolean, nullable=True | Indica si la membresía de la empresa se encuentra activa. |
| nivel_membresia | String(128), nullable=True | Nivel de membresía vigente de la empresa. |
| total_eventos | Integer, nullable=False, default=0 | Cantidad de eventos únicos a los que asistió la empresa. |
| total_asistencias | Integer, nullable=False, default=0 | Cantidad total de participaciones o asistencias registradas. |
| personas_distintas_participantes | Integer, nullable=False, default=0 | Cantidad de profesionales distintos que participaron por la empresa. |
| ultima_fecha_participacion | String(32), nullable=True | Fecha del último evento en el que participó la empresa (YYYY-MM-DD). |
| primera_fecha_participacion | String(32), nullable=True | Fecha del primer evento en el que participó la empresa (YYYY-MM-DD). |
| asistencias_trimestre_calendario | Integer, nullable=False, default=0 | Total de asistencias durante el trimestre calendario configurado. |
| asistencias_trimestre_operativo | Integer, nullable=False, default=0 | Total de asistencias durante el trimestre operativo configurado. |
| asistencias_ventana_movil_90d_corte | Integer, nullable=False, default=0 | Asistencias en la ventana móvil de 90 días previos a la fecha de corte. |
| asistencias_ventana_movil_90d_ultimo_evento | Integer, nullable=False, default=0 | Asistencias en la ventana móvil de 90 días previos al último evento global. |
| participacion_linea_anticipar | Integer, nullable=False, default=0 | Cantidad de asistencias en eventos de la línea Anticipar. |
| participacion_linea_evento_grande | Integer, nullable=False, default=0 | Cantidad de asistencias en eventos de la línea Evento grande. |
| participacion_linea_foro | Integer, nullable=False, default=0 | Cantidad de asistencias en eventos de la línea Foro. |
| participacion_linea_pares | Integer, nullable=False, default=0 | Cantidad de asistencias en eventos de la línea Pares. |
| participacion_modalidad_presencial | Integer, nullable=False, default=0 | Cantidad de asistencias en eventos de modalidad Presencial. |
| participacion_modalidad_virtual | Integer, nullable=False, default=0 | Cantidad de asistencias en eventos de modalidad Virtual. |
| participacion_modalidad_hibrido | Integer, nullable=False, default=0 | Cantidad de asistencias en eventos de modalidad Híbrido. |
| dias_sin_participacion | Float, nullable=True | Días transcurridos desde la última participación hasta la fecha de corte. |
| meses_sin_participacion | Float, nullable=True | Meses de inactividad desde la última participación (nulo si total_eventos=0). |
| estado_recencia_participacion | String(64), nullable=True | Clasificación del estado de recencia de participación de la empresa. |

### gold_agg_participacion_eventos

Agregación analítica de participación por evento, línea 2027 y modalidad.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_evento | String(64), primary_key=True | Identificador único del evento en la capa Silver. |
| nombre_evento | String(255), nullable=True | Nombre oficial del evento o experiencia. |
| fecha_evento | String(32), nullable=True | Fecha principal del evento en formato ISO YYYY-MM-DD. |
| periodo_mes_iso | String(32), nullable=True | Periodo mensual del evento en formato YYYY-MM. |
| linea_oferta_2027 | String(128), nullable=True | Línea estratégica de oferta 2027 asociada al evento. |
| modalidad | String(64), nullable=True | Modalidad del evento (Presencial, Virtual, Híbrido). |
| es_presencial | Boolean, nullable=True | Indicador booleano de presencialidad del evento. |
| total_asistencias | Integer, nullable=False, default=0 | Cantidad total de registros de asistencia al evento. |
| personas_distintas | Integer, nullable=False, default=0 | Cantidad de personas únicas participantes en el evento. |
| empresas_distintas | Integer, nullable=False, default=0 | Cantidad de empresas únicas representadas en el evento. |
| asistentes_afiliados | Integer, nullable=False, default=0 | Cantidad de asistencias correspondientes a empresas afiliadas. |
| asistentes_no_afiliados | Integer, nullable=False, default=0 | Cantidad de asistencias de participantes no afiliados (leads). |
| empresas_afiliadas_distintas | Integer, nullable=False, default=0 | Empresas afiliadas únicas que asistieron al evento. |
| empresas_no_afiliadas_distintas | Integer, nullable=False, default=0 | Empresas no afiliadas únicas que asistieron al evento. |
| porcentaje_no_afiliados | Float, nullable=False, default=0.0 | Porcentaje de asistencias no afiliadas sobre el total del evento. |
| asistentes_con_autorizacion_datos | Integer, nullable=False, default=0 | Cantidad de asistencias con autorización explícita de tratamiento de datos. |
| desglose_niveles_cargo | Text, nullable=True | Resumen en formato JSON con el conteo de asistentes por nivel de cargo. |

### gold_agg_retencion_empresa

Agregación analítica de retención y semáforo de riesgo por empresa en Gold.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_empresa | String(64), ForeignKey('silver_dim_empresas.id_empresa'), primary_key=True | Clave primaria y foránea hacia silver_dim_empresas. |
| kam_id | String(64), nullable=True | Identificador homologado de la ejecutiva KAM responsable. |
| en_crm_afiliados | Boolean, nullable=True | Indica si la empresa está registrada en el maestro de afiliados CRM. |
| es_empresa_activa | Boolean, nullable=True | Indica si la empresa tiene estado general Activo en el CRM. |
| es_membresia_activa | Boolean, nullable=True | Indica si la membresía actual de la empresa está activa. |
| estado_membresia_detalle | String(128), nullable=True | Estado detallado de la membresía vigente en el CRM. |
| segmento_membresia | String(128), nullable=True | Segmento comercial de la membresía. |
| nivel_membresia | String(128), nullable=True | Nivel de la membresía vigente. |
| fecha_afiliacion | String(32), nullable=True | Fecha de afiliación vigente en formato ISO YYYY-MM-DD. |
| fecha_expiracion | String(32), nullable=True | Fecha de expiración o vencimiento de la membresía (YYYY-MM-DD). |
| fecha_ultima_actividad | String(32), nullable=True | Fecha de última actividad registrada en el CRM. |
| renovaciones_registradas_2026 | Integer, nullable=False, default=0 | Cantidad de movimientos de renovación registrados para la empresa. |
| estados_inactivos_historicos_scd2 | Integer, nullable=False, default=0 | Cantidad de versiones previas no vigentes con estado inactivo en SCD2. |
| numero_retiros_historicos | Integer, nullable=False, default=0 | Total acumulado de versiones con estado inactivo o cancelado en SCD2. |
| total_eventos | Integer, nullable=False, default=0 | Cantidad de eventos únicos en los que participó la empresa. |
| total_asistencias | Integer, nullable=False, default=0 | Total de asistencias registradas para la empresa. |
| personas_distintas_participantes | Integer, nullable=False, default=0 | Cantidad de personas distintas que han asistido por la empresa. |
| asistencias_trimestre_calendario | Integer, nullable=False, default=0 | Asistencias registradas en el trimestre calendario. |
| asistencias_trimestre_operativo | Integer, nullable=False, default=0 | Asistencias registradas en el trimestre operativo. |
| asistencias_ventana_movil_90d_corte | Integer, nullable=False, default=0 | Asistencias en la ventana móvil de 90 días respecto a la fecha de corte. |
| asistencias_ventana_movil_90d_ultimo_evento | Integer, nullable=False, default=0 | Asistencias en la ventana móvil de 90 días respecto al último evento. |
| ultima_fecha_participacion | String(32), nullable=True | Fecha de la última participación en eventos (YYYY-MM-DD). |
| dias_sin_participacion | Float, nullable=True | Días transcurridos desde la última participación en eventos. |
| meses_sin_participacion | Float, nullable=True | Meses de inactividad desde la última participación. |
| estado_recencia_participacion | String(64), nullable=True | Categoría de recencia de participación de la empresa. |
| respuestas_encuestas_total | Integer, nullable=False, default=0 | Cantidad de encuestas de satisfacción respondidas por la empresa. |
| satisfaccion_promedio_1_5 | Float, nullable=True | Promedio histórico de satisfacción de la empresa en escala 1 a 5. |
| satisfaccion_reciente_1_5 | Float, nullable=True | Calificación de satisfacción más reciente registrada para la empresa (1 a 5). |
| nps_adaptado_empresa_1_5 | Float, nullable=True | Puntaje NPS adaptado (-100 a +100) de la empresa (%Promotores - %Detractores). |
| fecha_ultima_encuesta | String(32), nullable=True | Fecha de la última encuesta respondida por la empresa. |
| en_seguimiento_kam | Boolean, nullable=True | Indicador de origen sobre inclusión en el portafolio de seguimiento KAM. |
| asistio_segun_kam | Boolean, nullable=True | Indicador de origen reportado por la ejecutiva KAM sobre asistencia. |
| eventos_reportados_kam | Float, nullable=True | Cantidad de eventos reportados en la matriz de seguimiento KAM. |
| es_retiro_definitivo_actual | Boolean, nullable=True | Indica si el estado vigente actual de la empresa en CRM es retiro/inactivo. |
| fecha_ultima_interaccion_global | String(32), nullable=True | Fecha máxima de interacción entre actividad CRM, eventos y encuestas. |
| dias_para_expiracion | Float, nullable=True | Días restantes hasta la fecha de expiración respecto a la fecha de corte. |
| es_membresia_vencida | Boolean, nullable=True | Indica si la membresía ya se encuentra vencida (dias_para_expiracion < 0). |
| es_proximo_vencimiento_30d | Boolean, nullable=True | Indica si la membresía vence entre 0 y 30 días. |
| es_proximo_vencimiento_60d | Boolean, nullable=True | Indica si la membresía vence entre 0 y 60 días. |
| es_proximo_vencimiento_90d | Boolean, nullable=True | Indica si la membresía vence entre 0 y 90 días (excluye vencidas < 0). |
| estado_vigencia_expiracion | String(64), nullable=True | Clasificación del tramo de vigencia o vencimiento de la membresía. |
| alerta_membresia_vencida | Boolean, nullable=True | Señal booleana de alerta por membresía con fecha de expiración vencida. |
| alerta_proximo_vencimiento_90d | Boolean, nullable=True | Señal booleana de alerta por vencimiento próximo dentro de 90 días. |
| alerta_baja_participacion | Boolean, nullable=True | Señal booleana de alerta por nula participación en eventos. |
| alerta_baja_satisfaccion | Boolean, nullable=True | Señal booleana de alerta por satisfacción reciente inferior al umbral (3.75). |
| alerta_monocontacto | Boolean, nullable=True | Señal booleana de alerta cuando solo participa una única persona. |
| puntaje_heuristico_riesgo | Integer, nullable=False, default=0 | Puntaje acumulado de riesgo según los pesos configurados en etl_config.json. |
| semaforo_riesgo_renovacion | String(64), nullable=True | Clasificación del semáforo heurístico (ROJO, AMARILLO, VERDE o NO_APLICA). |
| tipo_metodologia_riesgo | String(128), nullable=True | Identificador metodológico (REGLA_HEURISTICA_NEGOCIO_NO_PREDICTIVA). |

### gold_agg_satisfaccion_encuestas

Agregación analítica de satisfacción por tipo, modalidad y mes en la capa Gold.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| tipo_encuesta | String(64), primary_key=True | Tipo de encuesta (POST_EVENTO, ENCUESTA_90_DIAS, etc.) para separar NPS. |
| modalidad_encuesta | String(64), primary_key=True | Modalidad del instrumento evaluado (Presencial o Virtual). |
| periodo_mes_iso | String(32), primary_key=True | Periodo mensual de aplicación de la encuesta en formato YYYY-MM. |
| total_respuestas | Integer, nullable=False, default=0 | Cantidad total de respuestas recibidas en la modalidad y periodo. |
| respuestas_con_empresa_resuelta | Integer, nullable=False, default=0 | Cantidad de respuestas donde se identificó la empresa del participante. |
| respuestas_sin_empresa | Integer, nullable=False, default=0 | Cantidad de respuestas sin empresa vinculada. |
| respuestas_anonimas_sin_persona | Integer, nullable=False, default=0 | Cantidad de respuestas anónimas sin identificador de persona. |
| promedio_satisfaccion_general_1_5 | Float, nullable=True | Promedio general de satisfacción en escala Likert de 1 a 5. |
| promedio_locacion_plataforma_1_5 | Float, nullable=True | Promedio de calificación (1 a 5) de locación o plataforma. |
| promedio_convocatoria_1_5 | Float, nullable=True | Promedio de calificación (1 a 5) de convocatoria y publicidad. |
| promedio_conferencistas_1_5 | Float, nullable=True | Promedio de calificación (1 a 5) de conferencistas. |
| promedio_relevancia_temas_1_5 | Float, nullable=True | Promedio de calificación (1 a 5) de relevancia de los temas. |
| calificaciones_altas_475_a_500 | Integer, nullable=False, default=0 | Cantidad de respuestas con promedio de satisfacción entre 4.75 y 5.00. |
| calificaciones_medias_375_a_474 | Integer, nullable=False, default=0 | Cantidad de respuestas con promedio de satisfacción entre 3.75 y 4.74. |
| calificaciones_bajas_menores_375 | Integer, nullable=False, default=0 | Cantidad de respuestas con promedio de satisfacción inferior a 3.75. |
| promotores_nps_adaptado_1_5 | Integer, nullable=False, default=0 | Conteo de promotores adaptados (calificación 4 a 5 en escala Likert 1-5). |
| neutros_nps_adaptado_1_5 | Integer, nullable=False, default=0 | Conteo de neutros adaptados (calificación 3 en escala Likert 1-5). |
| detractores_nps_adaptado_1_5 | Integer, nullable=False, default=0 | Conteo de detractores adaptados (calificación 1 a 2 en escala Likert 1-5). |
| porcentaje_promotores_adaptado_1_5 | Float, nullable=True | Porcentaje de promotores adaptados (0 a 100%) en escala 1-5. |
| porcentaje_neutros_adaptado_1_5 | Float, nullable=True | Porcentaje de neutros adaptados (0 a 100%) en escala 1-5. |
| porcentaje_detractores_adaptado_1_5 | Float, nullable=True | Porcentaje de detractores adaptados (0 a 100%) en escala 1-5. |
| nps_adaptado_1_5 | Float, nullable=True | Puntaje NPS adaptado (-100 a +100) como %Promotores(4-5) - %Detractores(1-2). |
| promotores_nps_0_10 | Float, nullable=True | Conteo de promotores (calificación 9-10) cuando existe pregunta NPS 0-10. |
| pasivos_nps_0_10 | Float, nullable=True | Conteo de pasivos (calificación 7-8) cuando existe pregunta NPS 0-10. |
| detractores_nps_0_10 | Float, nullable=True | Conteo de detractores (calificación 0-6) cuando existe pregunta NPS 0-10. |
| nps_oficial_0_10 | Float, nullable=True | Puntaje NPS oficial (-100 a +100); nulo para encuestas históricas Likert 1-5. |
| estado_calculo_nps | String(128), nullable=True | Estado de disponibilidad y cálculo del indicador NPS 0-10. |
| asociacion_evento_origen | String(128), nullable=True | Nota de trazabilidad sobre la disponibilidad de id_evento en la fuente. |
| temarios_sugeridos_resumen | Text, nullable=True | Resumen de temas y comentarios solicitados en las respuestas del periodo. |

### gold_agg_segmentos_comunicaciones

Tabla Gold con los 8 segmentos accionables para campañas de comunicaciones.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_registro_segmento | String(160), primary_key=True | Clave primaria compuesta determinística (segmento::empresa::persona). |
| orden_segmento | Integer, nullable=False | Número de orden oficial del segmento (1 a 8). |
| segmento_codigo | String(64), nullable=False, index=True | Código técnico estandarizado del segmento de comunicaciones. |
| segmento_nombre | String(128), nullable=False | Nombre legible del segmento de comunicaciones para negocio. |
| id_empresa | String(64), nullable=True, index=True | Identificador de la empresa asociada al registro del segmento. |
| id_persona | String(64), nullable=True, index=True | Identificador de la persona asociada cuando el segmento es a nivel contacto. |
| kam_id | String(64), nullable=True, index=True | Identificador homologado de la ejecutiva KAM responsable de la cuenta. |
| nivel_membresia | String(64), nullable=True | Nivel de membresía de la empresa (Conectar, Crecer, Liderar, etc.). |
| estado_vigencia_expiracion | String(64), nullable=True | Clasificación temporal de vigencia o vencimiento de la membresía. |
| semaforo_riesgo_renovacion | String(64), nullable=True | Categoría del semáforo heurístico de riesgo de no renovación. |
| detalle_criterio | Text, nullable=True | Descripción del criterio específico por el cual ingresó al segmento. |
| autoriza_tratamiento_datos | Boolean, nullable=True | Indicador de autorización de datos cuando proviene de asistencias/encuestas. |

## Capa Audit (Gobierno y Trazabilidad)

### audit_calidad_datos

Registro de reglas e incidencias de calidad de datos aplicadas.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_incidencia | String(64), primary_key=True | Identificador único de la regla o incidencia de calidad (DQ-xxxx). |
| tabla_analizada | String(128), nullable=True | Nombre de la tabla Silver evaluada por la regla de calidad. |
| campo_afectado | String(256), nullable=True | Campo o conjunto de columnas verificadas. |
| tipo_inconsistencia | String(128), nullable=True | Tipología de la inconsistencia o regla de negocio aplicada. |
| registros_afectados | Integer, nullable=True | Cantidad de filas impactadas por la regla o hallazgo. |
| valor_original | Text, nullable=True | Descripción del estado o valor original en la capa Bronze. |
| valor_corregido | Text, nullable=True | Acción de estandarización o conservación aplicada en Silver. |
| fecha_corte_modelo | String(32), nullable=True | Fecha de corte de referencia del modelo. |
| estado_resolucion | String(128), nullable=True | Estado final de la regla (CORREGIDO_HOMOLOGADO, DOCUMENTADO_CONSERVADO, etc.). |

### audit_cargas

Registro de metadatos operativos por tabla cargada en el pipeline ETL.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_ejecucion | String(128), primary_key=True | Identificador único de la corrida del pipeline ETL. |
| fuente | String(256), primary_key=True | Descripción del flujo de transformación (origen -> destino). |
| fecha_inicio | String(64), nullable=True | Marca temporal de inicio del procesamiento de la tabla. |
| fecha_finalizacion | String(64), nullable=True | Marca temporal de finalización del procesamiento de la tabla. |
| registros_leidos | Integer, nullable=True | Cantidad de registros leídos en el paso. |
| registros_procesados | Integer, nullable=True | Cantidad de registros procesados tras validaciones. |
| registros_insertados | Integer, nullable=True | Cantidad de registros escritos en la capa destino. |
| registros_actualizados | Integer, nullable=True | Cantidad de registros homologados o actualizados. |
| registros_rechazados | Integer, nullable=True | Cantidad de registros rechazados por validación de claves. |
| estado_ejecucion | String(64), nullable=True | Estado final del paso de carga (EXITOSO o FALLIDO). |

### audit_ejecuciones_etl

Resumen consolidado de auditoría por ejecución del pipeline Medallion.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_ejecucion | String(128), primary_key=True | Identificador único de la ejecución del pipeline ETL. |
| fecha_inicio | String(64), nullable=False | Fecha y hora de inicio global de la ejecución. |
| fecha_finalizacion | String(64), nullable=False | Fecha y hora de finalización global de la ejecución. |
| archivos_procesados | Integer, nullable=False, default=0 | Cantidad total de archivos fuente procesados en Bronze. |
| registros_leidos | Integer, nullable=False, default=0 | Suma total de registros leídos desde las fuentes Bronze. |
| registros_cargados | Integer, nullable=False, default=0 | Suma total de registros cargados en las tablas destino. |
| registros_rechazados | Integer, nullable=False, default=0 | Cantidad total de registros rechazados en la ejecución. |
| duplicados_identificados | Integer, nullable=False, default=0 | Cantidad total de registros duplicados clasificados en auditoría. |
| errores | Text, nullable=True | Detalle de errores registrados o 'NINGUNO' si fue exitoso. |
| estado_ejecucion | String(64), nullable=False | Estado general de la corrida del pipeline (EXITOSO o FALLIDO). |

### audit_hashes_fuentes_bronze

Registro de auditoría de hashes SHA-256 de archivos en la capa Bronze.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| tabla_fuente | String(128), primary_key=True | Nombre lógico de la tabla fuente verificada en la capa Bronze. |
| id_ejecucion | String(128), nullable=True | Identificador único de la ejecución ETL que verificó el archivo. |
| fecha_hora_ingesta | String(64), nullable=True | Fecha y hora ISO en que se realizó la validación e ingesta en Bronze. |
| archivo_nombre | String(256), nullable=True | Nombre del archivo CSV fuente procesado. |
| bytes_origen | Integer, nullable=True | Tamaño en bytes del archivo fuente. |
| filas_leidas | Integer, nullable=True | Cantidad total de filas leídas desde el archivo Bronze. |
| columnas_leidas | Integer, nullable=True | Cantidad total de columnas del archivo Bronze. |
| sha256_origen | String(64), nullable=True | Hash criptográfico SHA-256 calculado sobre el archivo de entrada. |
| sha256_bronze | String(64), nullable=True | Hash criptográfico SHA-256 calculado sobre la copia en Bronze. |
| integridad_verificada | Boolean, nullable=True | Indica si los hashes de origen y Bronze coinciden exactamente. |
| accion_bronze | String(128), nullable=True | Acción ejecutada (COPIADO_INICIAL_VERIFICADO o CONSERVADO_SIN_SOBRESCRIBIR). |

### audit_reconciliacion_origen_destino

Registro de reconciliación de conteos entre las capas Bronze y Silver.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| Tabla | String(128), primary_key=True | Nombre lógico de la tabla reconciliada entre Bronze y Silver. |
| Filas_Bronze | Integer, nullable=True | Cantidad de filas leídas en la capa Bronze. |
| Cols_Bronze | Integer, nullable=True | Cantidad de columnas presentes en la capa Bronze. |
| Filas_Silver | Integer, nullable=True | Cantidad de filas válidas persistidas en la capa Silver. |
| Cols_Silver | Integer, nullable=True | Cantidad de columnas estructuradas en la capa Silver. |
| Filas_Rechazadas | Integer, nullable=True | Cantidad de filas enviadas a audit_registros_rechazados. |
| Diferencia_Filas | Integer, nullable=True | Diferencia neta de filas: (Filas_Silver + Filas_Rechazadas) - Filas_Bronze. |
| Explicacion_Reconciliacion | Text, nullable=True | Explicación técnica de la conciliación y separación de métricas. |

### audit_registros_duplicados

Registro de auditoría de los 122 duplicados identificados y clasificados.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_duplicado | String(64), primary_key=True | Identificador único del registro duplicado auditado (DUP-xxxx). |
| tabla_normalizada_afectada | String(128), nullable=True | Nombre de la tabla normalizada donde se detectó la duplicidad. |
| archivo_origen_csv | String(256), nullable=True | Ruta relativa del archivo CSV crudo original. |
| fila_origen_csv | Integer, nullable=True | Número de fila dentro del archivo CSV original. |
| tipo_duplicado | String(256), nullable=True | Descripción detallada del tipo de duplicado encontrado en el EDA. |
| llave_negocio | String(256), nullable=True | Expresión de la llave de negocio involucrada en la colisión. |
| id_empresa | String(64), nullable=True | Identificador de empresa asociado al registro duplicado cuando aplica. |
| id_persona | String(64), nullable=True | Identificador de persona asociado al registro duplicado cuando aplica. |
| id_evento | Float, nullable=True | Identificador del evento asociado cuando corresponde a asistencias. |
| fecha_iso | String(32), nullable=True | Fecha asociada al registro en formato ISO YYYY-MM-DD. |
| regla_identificacion | Text, nullable=True | Regla aplicada durante la normalización para detectar la duplicidad. |
| detalle_primera_aparicion | Text, nullable=True | Resumen de atributos del registro principal conservado. |
| detalle_duplicado | Text, nullable=True | Resumen de atributos del registro repetido o histórico. |
| categoria_duplicidad | String(128), nullable=True | Categoría estandarizada (DUPLICADO_EXACTO, HISTORICO_SCD2, etc.). |
| id_registro_conservado | String(128), nullable=True | Identificador del registro principal trazable en la capa Silver. |
| fecha_deteccion | String(32), nullable=True | Fecha de corte en la que se documentó el duplicado. |
| estado_revision | String(128), nullable=True | Estado de gobierno del registro en auditoría. |
| accion_aplicada | String(128), nullable=True | Acción de negocio aplicada (incorporado en SCD2 o conservado con traza). |

### audit_registros_rechazados

Registro de auditoría de filas rechazadas durante la validación Silver.

| Columna | Tipo / Restricciones | Descripción |
| :--- | :--- | :--- |
| id_rechazo | String(64), primary_key=True | Identificador único del rechazo registrado (REJ-xxxx). |
| id_ejecucion | String(128), nullable=True | Identificador de la ejecución ETL donde se detectó el rechazo. |
| tabla_destino | String(128), nullable=True | Nombre de la tabla Silver en la que falló la validación. |
| archivo_origen_bronze | String(256), nullable=True | Nombre del archivo Bronze del cual provenía el registro. |
| motivo_rechazo | Text, nullable=True | Causa técnica del rechazo (PK nula, vacía o duplicada). |
| registro_original_json | Text, nullable=True | Contenido íntegro de la fila rechazada serializado en formato JSON. |
| fecha_corte_modelo | String(32), nullable=True | Fecha de corte del modelo analítico. |
