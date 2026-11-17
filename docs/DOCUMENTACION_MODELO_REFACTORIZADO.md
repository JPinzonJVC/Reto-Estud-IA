# 🏛️ Documentación Técnica y Diccionario de Datos — ACTHO 360 (Segunda Iteración v2.0)

## 1. Resumen de Correcciones de la Segunda Iteración

1. **Portabilidad (`pathlib.Path` y Configuración Externa)**:
   - Se eliminaron todas las rutas absolutas de Windows en el código ETL y en la suite de pruebas.
   - Se creó `config/etl_config.json` y el cargador `etl/config.py` (`ConfiguracionETL`), que resuelve rutas relativas respecto a la raíz del proyecto o mediante variables de entorno (`ACTHO360_CONFIG_PATH`, `ACTHO360_ORIGEN_DIR`, `ACTHO360_DUPLICADOS_DIR`, `ACTHO360_SALIDA_DIR`), permitiendo ejecutar el ETL desde cualquier directorio de trabajo (`cwd`).
2. **Inmutabilidad en Bronze, Hashes SHA-256 e Idempotencia Analítica**:
   - Antes de ingerir, se valida la existencia y tamaño ($>0$ bytes) de cada archivo fuente y se calcula su hash **SHA-256** en `audit/audit_hashes_fuentes_bronze.csv` (`.parquet`).
   - Si un archivo ya existe en `bronze/`, se verifica su hash SHA-256: si coincide con el origen, **no se sobrescribe** (`CONSERVADO_SIN_SOBRESCRIBIR_HASH_IDENTICO`); si difiere, se lanza `RuntimeError` para impedir sobrescrituras silenciosas.
   - Se separaron los metadatos de tiempo de ejecución (`audit/audit_cargas.csv`) de las tablas analíticas (`silver/` y `gold/`), garantizando que dos ejecuciones sobre las mismas fuentes produzcan DataFrames analíticos **100% idénticos (`pd.testing.assert_frame_equal`)**.
   - Se eliminó el silenciamiento de errores en Parquet: cualquier fallo en `to_parquet()` se registra y lanza `RuntimeError`.
3. **Reconstrucción y Validación de `dim_empresas_scd2` (SCD Tipo 2)**:
   - Se corrigió la colisión de `id_registro_crm` en empresas con múltiples registros inactivos en `Afiliados.csv`, asignando a cada versión histórica su `id_registro_crm` original.
   - **No se inventan fechas**: `fecha_inicio_vigencia` toma exclusivamente `fecha_afiliacion` de la versión correspondiente, manteniendo `fecha_miembro_desde_crm` en una columna separada.
   - Se validan versiones consecutivas (`1..N`) y una única versión actual (`es_registro_actual = True`) por `id_empresa`.
   - Se detectan y marcan explícitamente:
     - `tiene_fechas_inconsistentes` (`fecha_inicio_vigencia > fecha_fin_vigencia`, ej. `EMP-0174`: `2022-03-04 > 2021-12-31`).
     - `tiene_intervalo_superpuesto` (versiones de una misma empresa con fechas de inicio repetidas o intervalos solapados, ej. `EMP-0054`, `EMP-0357`, `EMP-0505`, `EMP-0583`, `EMP-0673`).
     - `clasificacion_historia_scd2`: `VIGENCIA_COMPLETA_RECONSTRUIDA`, `VIGENCIA_PARCIAL_SIN_FECHA_FIN`, `HISTORIA_PARCIAL_SIN_FECHA_INICIO`, `HISTORIA_NO_RECONSTRUIBLE_SIN_FECHAS_EN_ORIGEN`, `FECHA_INCONSISTENTE_INICIO_MAYOR_FIN`, `INTERVALO_SUPERPUESTO_O_AMBIGUO_EN_ORIGEN` y `NO_APLICA_PROSPECTO_SIN_CRM`.
4. **Participación, Retención y Periodos Configurables (`agg_participacion_empresa` y `agg_retencion_empresa`)**:
   - Se sustituyeron los periodos fijos por parámetros configurables en `config/etl_config.json`:
     - Trimestre calendario (`asistencias_trimestre_calendario`, ej. `2026-Q3`: Jul–Sep 2026) y trimestre operativo reciente (`asistencias_trimestre_operativo`: Ago–Oct 2026).
     - Ventana móvil de 90 días respecto a la fecha de corte (`asistencias_ventana_movil_90d_corte`) y respecto al último evento registrado (`asistencias_ventana_movil_90d_ultimo_evento`).
   - Se separaron estrictamente las **empresas ya vencidas** (`es_membresia_vencida`: `dias_para_expiracion < 0`, 4 empresas activas) de las **empresas próximas a vencer** (`es_proximo_vencimiento_90d`: `0 <= dias_para_expiracion <= 90`, 269 empresas activas; `es_proximo_vencimiento_60d`: 257 empresas; `es_proximo_vencimiento_30d`: 0 empresas).
   - Se distinguieron los **retiros definitivos actuales** (`es_retiro_definitivo_actual`: empresas cuyo estado vigente en CRM es `Cancelado`, `Expirado` o `Inactivo`) de los **estados inactivos históricos en SCD2** (`estados_inactivos_historicos_scd2`: versiones previas no vigentes en `dim_empresas_scd2`), conservando además `numero_retiros_historicos` documentado.
   - En `meses_sin_participacion`, solo se calcula el valor numérico cuando existe `ultima_fecha_participacion`; para empresas con `total_eventos == 0` se conserva `NaN` y se clasifica en `estado_recencia_participacion = 'SIN_PARTICIPACION_REGISTRADA'`.
5. **Satisfacción y NPS (`agg_satisfaccion_encuestas`)**:
   - Dado que las encuestas originales (`EVENTO~1.XLS - Responses.csv` y `eventos_dos.csv`) no capturan el identificador del evento (`id_evento`), se renombró la agregación Gold a **`agg_satisfaccion_encuestas`** (agrupada por `modalidad_encuesta` y `periodo_mes_iso`), sin asociar encuestas a eventos mediante inferencias.
   - Se mantiene la satisfacción en escala 1–5 separada del NPS en escala 0–10 (`nps_oficial_0_10 = NaN`, `estado_calculo_nps = 'NO_CALCULABLE_SIN_PREGUNTA_RECOMENDACION_0_10'`).
   - Se conservan y contabilizan explícitamente las respuestas anónimas (`respuestas_anonimas_sin_persona`) y sin empresa (`respuestas_sin_empresa`).
6. **Semáforo de Riesgo Heurístico Parametrizado**:
   - Los pesos y umbrales están centralizados en `config/etl_config.json` (`reglas_semaforo_riesgo`).
   - Distingue individualmente: `alerta_membresia_vencida` (+2 pts), `alerta_proximo_vencimiento_90d` (+2 pts), `alerta_baja_participacion` (+2 pts), `alerta_baja_satisfaccion` (+2 pts) y `alerta_monocontacto` (+1 pt).
   - Se documenta explícitamente en `tipo_metodologia_riesgo = 'REGLA_HEURISTICA_NEGOCIO_NO_PREDICTIVA'` que se trata de una regla heurística de priorización operativa y no de un modelo predictivo estadísticamente validado.

---

## 2. Diccionario de Datos Actualizado (Capas Silver, Gold y Audit)

### 2.1 Capa `silver/`
| Tabla | Clave Primaria (PK) | Filas | Columnas Principales y Descripción |
| :--- | :--- | :---: | :--- |
| **`dim_kams`** | `kam_id` | `10` | `kam_id` (`KAM A..I`, `KAM-UNASSIGNED`), `kam_etiqueta_original`, `responsable_nombre`, `tiene_seguimiento_eventos`, `es_kam_asignado`. |
| **`dim_empresas`** | `id_empresa` | `1,851` | Atributos descriptivos y estado actual de afiliación (`id_registro_crm`, `kam_id`, `kam_valor_original`, `es_empresa_activa`, `es_membresia_activa`, `estado_membresia_detalle`, `segmento_membresia`, `nivel_membresia`, `sector_economico`, `ciudad`, `fecha_afiliacion`, `fecha_expiracion`, `fecha_miembro_desde`). Sin métricas acopladas. |
| **`dim_empresas_scd2`** | `sk_empresa_scd2` | `1,872` | Historial SCD Tipo 2 (`id_empresa`, `id_registro_crm`, `version_registro`, `total_versiones_empresa`, `fecha_inicio_vigencia`, `fecha_fin_vigencia`, `fecha_miembro_desde_crm`, `es_registro_actual`, `tiene_fechas_inconsistentes`, `tiene_intervalo_superpuesto`, `clasificacion_historia_scd2`, `descripcion_version_scd2`). |
| **`dim_personas`** | `id_persona` | `2,892` | `id_persona`, `id_empresa_principal` (14 nulos conservados), `estado_resolucion_empresa` (`ASOCIADA` / `SIN_EMPRESA_ASOCIADA`), `nivel_cargo`, `ciudad`, `es_afiliado_principal_nuevo`, `fecha_afiliacion_nueva`. |
| **`dim_eventos`** | `id_evento` | `34` | `id_evento` (`1..34`), `archivo_csv`, `fecha_evento`, `fecha_inicio_evento`, `fecha_fin_evento`, `periodo_mes_iso`, `nombre_evento`, `linea_oferta_2027`, `experiencia_detalle`, `modalidad`, `es_presencial`, `tiene_asistentes_registrados`. |
| **`fact_asistencias`** | `id_asistencia` | `3,401` | `id_asistencia`, `id_evento`, `id_empresa` (15 nulos conservados), `id_persona`, `kam_id`, `kam_valor_original`, `fecha_evento`, `periodo_mes_iso`, `nivel_cargo`, `ciudad_evento`, `tipo_asistencia`, `modalidad_evento`, `estado_resolucion_identidad`. |
| **`fact_encuestas_satisfaccion`** | `id_respuesta` | `725` | `id_respuesta`, `modalidad_encuesta`, `id_evento` (`Int64` nulo sin inferencia), `fecha_encuesta`, `calif_*` (1–5), `promedio_satisfaccion` (1–5), `id_persona`, `id_empresa`, `estado_resolucion_identidad`, `tipo_encuesta`, `pregunta_recomendacion_nps_0_10` (`NaN`), `categoria_nps_0_10`. |
| **`fact_movimientos_crm`** | `id_movimiento` | `77` | `id_movimiento` (`MOV-0001..0077`), `tipo_movimiento`, `es_cierre_facturado`, `es_renovacion`, `fecha_periodo_mes`, `fecha_cierre_o_factura`, `fecha_expiracion_afiliacion`, `kam_id`, `kam_valor_original`, `id_empresa`, `estado_afiliacion_empresa`, `clasificacion_fecha_expiracion`. |

### 2.2 Capa `gold/`
| Tabla | Clave Primaria (PK) | Filas | Descripción de Indicadores |
| :--- | :--- | :---: | :--- |
| **`agg_participacion_empresa`** | `(id_empresa, periodo_analisis)` | `1,851` | `total_eventos`, `total_asistencias`, `personas_distintas_participantes`, `asistencias_trimestre_calendario`, `asistencias_trimestre_operativo`, `asistencias_ventana_movil_90d_corte`, `asistencias_ventana_movil_90d_ultimo_evento`, `ultima_fecha_participacion`, `dias_sin_participacion`, `meses_sin_participacion` (`NaN` si `total_eventos == 0`), `estado_recencia_participacion`, desglose por línea y modalidad. |
| **`agg_satisfaccion_encuestas`** | `(modalidad_encuesta, periodo_mes_iso)` | `12` | `total_respuestas`, `respuestas_con_empresa_resuelta`, `respuestas_sin_empresa`, `respuestas_anonimas_sin_persona`, promedios 1–5 por aspecto, conteos por tramo de satisfacción y `nps_oficial_0_10 = NaN` (`NO_CALCULABLE_SIN_PREGUNTA_RECOMENDACION_0_10`). |
| **`agg_retencion_empresa`** | `id_empresa` | `1,851` | Estado actual, `dias_para_expiracion`, separación entre `es_membresia_vencida` ($<0$ días) y `es_proximo_vencimiento_90d` ($0..90$ días), distinción entre `es_retiro_definitivo_actual` y `estados_inactivos_historicos_scd2`, alertas individuales, `puntaje_heuristico_riesgo`, `semaforo_riesgo_renovacion` y `tipo_metodologia_riesgo`. |

---

## 3. Limitaciones de las Fuentes Originales que No Pueden Resolverse sin Captura Nueva

1. **Ausencia de `id_evento` en las encuestas de satisfacción (`EVENTO~1.XLS - Responses.csv` y `eventos_dos.csv`)**: Los formularios originales no capturan a qué evento corresponde cada respuesta; por rigor metodológico no se infiere el evento por proximidad de fecha y se agrupa en `agg_satisfaccion_encuestas` por modalidad y mes.
2. **Ausencia de pregunta NPS (escala 0–10) en encuestas históricas**: Las encuestas actuales evalúan 4 aspectos operativos en escala Likert de 1 a 5; por tanto, el NPS oficial se documenta como `NaN` hasta que se incorpore la pregunta de recomendación 0–10 y la encuesta de 90 días.
3. **Registros en `Afiliados.csv` sin fechas de afiliación/expiración (`HISTORIA_NO_RECONSTRUIBLE_SIN_FECHAS_EN_ORIGEN`)**: 301 registros en CRM carecen tanto de `Fecha de Afiliación` como de `Fecha de Expiración` en la exportación de Zoho CRM, y 1 registro (`EMP-0174`) presenta `fecha_afiliacion > fecha_expiracion` en origen; se clasifican explícitamente en `dim_empresas_scd2` sin inventar fechas.
4. **Respuestas de encuesta anónimas (`139` sin persona y `142` sin empresa) y `15` asistencias sin empresa**: Se conservan íntegramente clasificadas mediante `estado_resolucion_identidad`.
