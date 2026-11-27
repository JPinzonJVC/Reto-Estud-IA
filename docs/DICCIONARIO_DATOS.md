# Diccionario de Datos — Data Warehouse Medallion ACTHO 360 (25 Tablas)

## 1. Capa Silver (Core Data Warehouse 3NF — 13 Tablas)

### 1.1 Área Geografía (`3NF`)
- **`silver_dim_pais`** (`dim_pais.parquet`):
  - `id_pais` (`Integer`, PK, `NOT NULL`): Clave primaria del país.
  - `nombre_pais` (`String(128)`, `UNIQUE`, `NOT NULL`): Nombre oficial del país.
- **`silver_dim_departamento`** (`dim_departamento.parquet`):
  - `id_departamento` (`Integer`, PK, `NOT NULL`): Clave primaria del departamento.
  - `id_pais` (`Integer`, FK → `silver_dim_pais`, `NOT NULL`): País contenedor.
  - `nombre_departamento` (`String(128)`, `NOT NULL`): Nombre normalizado (`UK` con `id_pais`).
- **`silver_dim_ciudad`** (`dim_ciudad.parquet`):
  - `id_ciudad` (`Integer`, PK, `NOT NULL`): Clave primaria de la ciudad.
  - `id_departamento` (`Integer`, FK → `silver_dim_departamento`, `NOT NULL`): Departamento contenedor.
  - `nombre_ciudad` (`String(128)`, `NOT NULL`): Nombre canónico (`UK` con `id_departamento`).

### 1.2 Área Entidades Principales y Puente N:N
- **`silver_dim_kams`** (`dim_kams.parquet`):
  - `kam_id` (`String(64)`, PK, `NOT NULL`): Identificador homologado (`KAM A..I` o `KAM-UNASSIGNED`).
  - `responsable_nombre` (`String(128)`, `NOT NULL`): Nombre de la ejecutiva responsable.
  - `tiene_seguimiento_eventos` (`Boolean`, `NOT NULL`): Indica si gestiona cartera con seguimiento activo.
- **`silver_dim_empresas`** (`dim_empresas.parquet`):
  - `id_empresa` (`String(64)`, PK, `NOT NULL`): Identificador único de negocio (`EMP-xxxx`).
  - `id_registro_crm` (`String(128)`, `NULLABLE`): Registro vigente en Zoho CRM.
  - `kam_id` (`String(64)`, FK → `silver_dim_kams`, `NOT NULL`): KAM actualmente asignado.
  - `id_ciudad_empresa` (`Integer`, FK → `silver_dim_ciudad`, `NULLABLE`): Ciudad sede de la empresa.
  - `es_empresa_activa` (`Boolean`, `NOT NULL`): Estado operativo general en CRM.
  - `sector_economico`, `subsector_economico`, `tamano_empresa`, `rango_empleados`, `porcentaje_mujeres_num`, `fecha_ultima_actividad_crm` y banderas de comunidades/pilares (`NULLABLE`).
- **`silver_dim_personas`** (`dim_personas.parquet`):
  - `id_persona` (`String(64)`, PK, `NOT NULL`): Identificador único del profesional (`P-xxxxx`).
  - `id_ciudad_persona` (`Integer`, FK → `silver_dim_ciudad`, `NULLABLE`): Ciudad asociada a la persona.
  - `nivel_cargo_actual` (`String(128)`, `NULLABLE`): Cargo jerárquico actual conocido.
- **`silver_bridge_persona_empresa`** (`bridge_persona_empresa.parquet`):
  - `id_vinculo` (`Integer`, PK, `NOT NULL`): Clave primaria del vínculo persona-empresa.
  - `id_persona` (`String(64)`, FK → `silver_dim_personas`, `NOT NULL`) + `id_empresa` (`String(64)`, FK → `silver_dim_empresas`, `NOT NULL`) con `UK(id_persona, id_empresa)`.
  - `nivel_cargo`, `fecha_primera_evidencia`, `fecha_ultima_evidencia` (`NULLABLE`).
  - `fuente_relacion` (`CRM` | `ASISTENCIA` | `ENCUESTA`), `estado_validacion` (`CONFIRMADO_CRM` | `REPORTADO_FORMULARIO` | `INFERIDO_DOMINIO`) y `es_vinculo_actual` (`Boolean`, `NOT NULL`).
- **`silver_dim_eventos`** (`dim_eventos.parquet`):
  - `id_evento` (`Integer`, PK, `NOT NULL`): Identificador numérico del evento (`1..34`).
  - `id_ciudad_evento` (`Integer`, FK → `silver_dim_ciudad`, `NULLABLE`): Ciudad sede en eventos presenciales explícitos.
  - `nombre_evento`, `fecha_inicio_evento`, `fecha_fin_evento`, `linea_oferta_2027`, `modalidad` (`NOT NULL`), `experiencia_detalle` (`NULLABLE`).

### 1.3 Área Membresías (Ciclos Reales de Afiliación)
- **`silver_dim_catalogo_membresia`** (`dim_catalogo_membresia.parquet`):
  - `id_cat_membresia` (`Integer`, PK, `NOT NULL`), `segmento_membresia`, `nivel_membresia`, `nombre_categoria` (`UK(segmento_membresia, nivel_membresia)`).
- **`silver_membresias`** (`membresias.parquet`):
  - Granularidad: **1 fila por ciclo real de membresía de una empresa** (sin duplicar versiones técnicas de CRM).
  - `id_membresia` (`String(64)`, PK, `NOT NULL`), `id_empresa` (FK `NOT NULL`), `id_cat_membresia` (FK `NOT NULL`), `kam_id` (FK `NULLABLE`), `id_registro_crm_origen` (`NULLABLE`), `estado_membresia_detalle` (`NOT NULL`), `es_membresia_activa` (`Boolean`, `NOT NULL`), `fecha_miembro_desde`, `fecha_afiliacion`, `fecha_inicio_vigencia`, `fecha_fin_vigencia` (`NULLABLE`).

### 1.4 Área Tablas de Hechos
- **`silver_fact_asistencias`** (`fact_asistencias.parquet`):
  - `id_asistencia` (PK), `id_evento` (FK `NOT NULL`), `id_persona` (FK `NULLABLE`), `id_empresa` (FK `NULLABLE`), `id_vinculo` (FK `NULLABLE`), `kam_id` (FK `NULLABLE`), `id_ciudad_asistente` (FK `NULLABLE`), `nivel_cargo_evento`, `tipo_asistencia` (`NOT NULL`), `cantidad_inscritos` (*provisional*), `tiene_costo`, `autoriza_tratamiento_datos`.
- **`silver_fact_encuestas_satisfaccion`** (`fact_encuestas_satisfaccion.parquet`):
  - `id_respuesta` (PK), `id_evento` (FK `NULLABLE`), `id_persona` (FK `NULLABLE`), `id_empresa` (FK `NULLABLE`), `id_ciudad_encuesta` (FK `NULLABLE`), `fecha_encuesta` (`NOT NULL`), `modalidad_encuesta` (`NOT NULL`), `tipo_encuesta` (`NOT NULL`), `duracion_segundos`, las 4 calificaciones Likert `1–5`, `pregunta_recomendacion_nps_0_10` (`Integer`, `NULLABLE`), `temarios_sugeridos`, `desea_recibir_actualizaciones`.
- **`silver_fact_movimientos_crm`** (`fact_movimientos_crm.parquet`):
  - `id_movimiento` (PK), `id_empresa` (FK `NOT NULL`), `id_membresia` (FK `NULLABLE` para tratos en estado), `kam_id` (FK `NOT NULL`), `id_persona_contacto` (FK `NULLABLE`), `id_cat_membresia_movimiento` (FK `NULLABLE`), `tipo_movimiento` (`NOT NULL`), `estado_movimiento_crm`, `es_cierre_facturado` (`NOT NULL`), `fecha_cierre_o_factura`, `fecha_expiracion_afiliacion`.

---

## 2. Capa Gold (Esquema Estrella Analítico + ML — 6 Tablas)

1. **`gold_dim_empresa_360`** (`dim_empresa_360.parquet`, PK: `id_empresa`):
   - Consolida estado 360° de la organización (`AFILIADO_ACTIVO`, `EX_AFILIADO`, `PROSPECTO_NO_AFILIADO`), filtros comerciales y geográficos, vencimientos (`0_30D`, `31_60D`, `61_90D`, `VENCIDA`), métricas anuales, **Semáforo Híbrido de Riesgo**, `probabilidad_churn_ml`, `score_fidelidad_ml_0_100`, `arquetipo_fidelidad_ml`, `score_conversion_lead_ml_0_100` y `linea_2027_recomendada_ml`.
2. **`gold_dim_evento_kpis`** (`dim_evento_kpis.parquet`, PK: `id_evento` entero):
   - KPIs de convocatoria por evento, línea 2027, modalidad, tasa de penetración en base activa y conteos explícitos por nivel de cargo.
3. **`gold_fact_asistencias_bi`** (`fact_asistencias_bi.parquet`, PK: `id_asistencia`):
   - Hecho enriquecido conectado a `gold_dim_empresa_360` y `gold_dim_evento_kpis` para filtros dinámicos y conteos `COUNT(DISTINCT)` sin doble conteo.
4. **`gold_fact_encuestas_bi`** (`fact_encuestas_bi.parquet`, PK: `id_respuesta`):
   - Respuestas enriquecidas con `promedio_respuesta_1_5` (para medias ponderadas exactas), separación estricta de `categoria_nps_0_10` y clasificación `categoria_tema_nlp`.
5. **`gold_fact_evolucion_membresias_mes`** (`fact_evolucion_membresias_mes.parquet`, PK: `id_evolucion_mes`):
   - Conteos mensuales aditivos de `altas_nuevas_mes`, `vencimientos_programados_mes`, `renovaciones_efectivas_mes` y `retiros_cancelaciones_mes`.
6. **`gold_mart_segmentos_comunicaciones`** (`mart_segmentos_comunicaciones.parquet`, PK: `id_registro_segmento`):
   - Los 8 segmentos oficiales de campaña con resolución de contacto en `bridge_persona_empresa` y control de Habeas Data (`apto_envio_comunicaciones`).

---

## 3. Capa Audit (Gobierno y Reconciliación — 6 Tablas)

1. **`audit_hashes_fuentes_bronze`**: Verificación criptográfica SHA-256 de las 7 fuentes Bronze.
2. **`audit_registros_rechazados`**: Cuarentena de registros con PK nula o duplicada.
3. **`audit_calidad_datos`**: Reglas de homologación, limpieza y saneamiento aplicadas.
4. **`audit_reconciliacion_origen_destino`**: Conciliación exacta de filas Bronze vs. Silver (`Diferencia_Filas = 0`).
5. **`audit_cargas`**: Trazabilidad operativa por paso de transformación.
6. **`audit_ejecuciones_etl`**: Resumen global por corrida del pipeline ETL.
