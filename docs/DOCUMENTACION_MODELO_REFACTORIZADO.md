# 🏛️ Documentación Técnica, Diccionario de Datos y Reporte de Reconciliación — ACTHO 360 (Issue 2)

## 1. Arquitectura Medallion + PostgreSQL (Bronze → Silver → Gold → Audit → PostgreSQL)

El pipeline ETL de **ACTHO 360** procesa las fuentes normalizadas desde `input/normalizados` a través de las cuatro capas Medallion en `input/` y persiste de forma transaccional e idempotente (mediante `UPSERT` por lotes `ON CONFLICT DO UPDATE`) en **PostgreSQL**:

1. **Capa `bronze/` (`input/bronze/`)**:
   - Conserva las 8 fuentes normalizadas intactas sin aplicar limpieza destructiva.
   - Registra `id_ejecucion`, `fecha_hora_ingesta`, `bytes_origen`, `filas_leidas` y hashes `SHA-256` en `audit_hashes_fuentes_bronze`.
   - Evita sobrescrituras silenciosas: si el hash coincide, conserva el archivo (`CONSERVADO_SIN_SOBRESCRIBIR_HASH_IDENTICO`); si difiere, aborta con `RuntimeError`.
2. **Capa `silver/` (`input/silver/`)**:
   - Separa atributos descriptivos de métricas calculadas, homologa `KAM-UNASSIGNED` conservando `kam_valor_original`, y reconstruye el historial SCD Tipo 2 en `dim_empresas_scd2` sin inventar fechas.
   - Valida claves primarias y conserva cualquier fila rechazada junto con su motivo y archivo Bronze de origen en `audit_registros_rechazados`.
3. **Capa `gold/` (`input/gold/`)**:
   - Genera `agg_participacion_empresa`, `agg_satisfaccion_encuestas` y `agg_retencion_empresa`.
   - Separa estrictamente membresías vencidas (`dias_para_expiracion < 0`) de próximas a vencer (`0 <= dias_para_expiracion <= 90`).
   - Calcula el **NPS Adaptado en escala 1–5** ($\text{NPS}_{\text{adaptado}} = \%\text{Promotores}_{4\text{–}5} - \%\text{Detractores}_{1\text{–}2}$, entre `-100` y `+100`, clasificando `1–2` como Detractores, `3` como Neutros y `4–5` como Promotores) en `agg_satisfaccion_encuestas` y `agg_retencion_empresa`, y deja además preparada la columna `nps_oficial_0_10` para la encuesta de 90 días en escala 0–10.
4. **Capa `audit/` (`input/audit/`)**:
   - Registra `audit_ejecuciones_etl`, `audit_hashes_fuentes_bronze`, `audit_registros_duplicados` (122 registros clasificados), `audit_registros_rechazados`, `audit_calidad_datos`, `audit_reconciliacion_origen_destino` y `audit_cargas`.
5. **Persistencia en PostgreSQL (`app/modules/eda/models/` y `postgres_loader.py`)**:
   - Reutiliza el motor y sesiones centralizadas de `app/database.py`.
   - Gestiona el esquema mediante SQLAlchemy ORM y migraciones **Alembic** (`alembic.ini`, `migrations/versions/rev_0001_initial_medallion_actho360.py`).
   - Ejecuta inserciones masivas con `ON CONFLICT DO UPDATE` dentro de una única transacción atómica (con `rollback` automático ante cualquier error de integridad o conexión).

---

## 2. Diccionario de Datos y Tablas en PostgreSQL (18 Tablas)

### 2.1 Capa Silver (`silver_*`)
| Tabla PostgreSQL | Archivo Parquet/CSV | PK | FK | Filas | Descripción |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `silver_dim_kams` | `silver/dim_kams` | `kam_id` | — | `10` | Catálogo de ejecutivas KAM (`KAM A..I` y `KAM-UNASSIGNED`). |
| `silver_dim_empresas` | `silver/dim_empresas` | `id_empresa` | `kam_id` | `1,851` | Atributos descriptivos, geográficos y estado vigente de empresas. |
| `silver_dim_empresas_scd2` | `silver/dim_empresas_scd2` | `sk_empresa_scd2` | `id_empresa`, `kam_id` | `1,872` | Historial SCD Tipo 2 (`1,851` actuales + `21` históricas) con clasificación temporal. |
| `silver_dim_personas` | `silver/dim_personas` | `id_persona` | `id_empresa_principal` | `2,892` | Profesionales vinculados a asistencias y encuestas (`14` sin empresa conservados). |
| `silver_dim_eventos` | `silver/dim_eventos` | `id_evento` | — | `34` | Catálogo maestro de los 34 eventos de 2026 y línea de oferta 2027. |
| `silver_fact_asistencias` | `silver/fact_asistencias` | `id_asistencia` | `id_evento`, `id_empresa`, `id_persona`, `kam_id` | `3,401` | Transacciones de asistencia (`15` sin empresa conservadas con estado explícito). |
| `silver_fact_encuestas_satisfaccion` | `silver/fact_encuestas_satisfaccion` | `id_respuesta` | `id_persona`, `id_empresa` | `725` | Respuestas Likert 1–5, sin `id_evento` inferido y preparadas para NPS 0–10. |
| `silver_fact_movimientos_crm` | `silver/fact_movimientos_crm` | `id_movimiento` | `kam_id`, `id_empresa` | `77` | Altas, renovaciones y tratos CRM con clave subrogada `MOV-0001..0077`. |

### 2.2 Capa Gold (`gold_*`)
| Tabla PostgreSQL | Archivo Parquet/CSV | PK | Filas | Indicadores Principales |
| :--- | :--- | :--- | :---: | :--- |
| `gold_agg_participacion_empresa` | `gold/agg_participacion_empresa` | `(id_empresa, periodo_analisis)` | `1,851` | `total_eventos`, `total_asistencias`, `personas_distintas_participantes`, trimestre calendario/operativo, ventana 90d, `ultima_fecha_participacion`, recencia. |
| `gold_agg_participacion_eventos` | `gold/agg_participacion_eventos` | `id_evento` | `34` | `nombre_evento`, `linea_oferta_2027`, `modalidad`, `total_asistencias`, `asistentes_afiliados`, `asistentes_no_afiliados` (leads), `desglose_niveles_cargo`, autorización de datos. |
| `gold_agg_satisfaccion_encuestas` | `gold/agg_satisfaccion_encuestas` | `(tipo_encuesta, modalidad_encuesta, periodo_mes_iso)` | `25+` | `total_respuestas`, promedios 1–5 por dimensión, NPS adaptado 1–5, preparación NPS oficial 0–10 (`POST_EVENTO` vs `ENCUESTA_90_DIAS`) y `temarios_sugeridos_resumen`. |
| `gold_agg_retencion_empresa` | `gold/agg_retencion_empresa` | `id_empresa` | `1,851` | Estado de afiliación, `fecha_expiracion`, `dias_para_expiracion`, cortes `30d`/`60d`/`90d`, `puntaje_heuristico_riesgo` y `semaforo_riesgo_renovacion`. |
| `gold_agg_segmentos_comunicaciones` | `gold/agg_segmentos_comunicaciones` | `id_registro_segmento` | Variable | Los 8 segmentos accionables de la Sección 05 (exportados también en `gold/segmentos_comunicaciones/*.csv`) con `kam_id`, riesgo y `autoriza_tratamiento_datos`. |

### 2.3 Capa Audit (`audit_*`)
| Tabla PostgreSQL | Archivo Parquet/CSV | PK | Filas | Propósito |
| :--- | :--- | :--- | :---: | :--- |
| `audit_ejecuciones_etl` | `audit/audit_ejecuciones_etl` | `id_ejecucion` | `1` (por corrida) | Resumen por ejecución: inicio, fin, archivos, leídos, cargados, rechazados, duplicados, errores y estado. |
| `audit_hashes_fuentes_bronze` | `audit/audit_hashes_fuentes_bronze` | `tabla_fuente` | `8` | Hashes `SHA-256`, `id_ejecucion`, `fecha_hora_ingesta` y acción de protección Bronze. |
| `audit_registros_duplicados` | `audit/audit_registros_duplicados` | `id_duplicado` | `122` | Trazabilidad de los 122 registros duplicados clasificados por tipología. |
| `audit_registros_rechazados` | `audit/audit_registros_rechazados` | `id_rechazo` | `0` (en dataset limpio) | Conservación de registros rechazados con `motivo_rechazo`, `archivo_origen_bronze` y JSON original. |
| `audit_calidad_datos` | `audit/audit_calidad_datos` | `id_incidencia` | `8` | Registro de reglas de calidad e integridad aplicadas en Silver. |
| `audit_reconciliacion_origen_destino` | `audit/audit_reconciliacion_origen_destino` | `Tabla` | `8` | Conciliación exacta de filas entre Bronze, Silver y Rechazados (`Diferencia_Filas = 0`). |
| `audit_cargas` | `audit/audit_cargas` | `(id_ejecucion, fuente)` | `11` | Bitácora detallada de cada paso de transformación Bronze → Silver → Gold → Audit. |

---

## 3. Reporte de Validación y Reconciliación (Bronze vs. Silver)

| Tabla | Filas Bronze | Cols Bronze | Filas Silver | Cols Silver | Filas Rechazadas | Diferencia Filas | Estado de Reconciliación |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `dim_kams` | `10` | `11` | `10` | `5` | `0` | `0` | 100% conciliado (`Sin asignar (cuenta ACTHO)` → `KAM-UNASSIGNED`). |
| `dim_empresas` | `1,851` | `46` | `1,851` | `37` | `0` | `0` | 100% conciliado (`1,872` versiones en `dim_empresas_scd2`). |
| `dim_personas` | `2,892` | `13` | `2,892` | `7` | `0` | `0` | 100% conciliado (`14` personas sin empresa clasificadas). |
| `dim_eventos` | `34` | `16` | `34` | `12` | `0` | `0` | 100% conciliado (métricas de archivo movidas a auditoría). |
| `fact_asistencias` | `3,401` | `16` | `3,401` | `20` | `0` | `0` | 100% conciliado (`15` asistencias sin empresa conservadas). |
| `fact_encuestas_satisfaccion` | `725` | `20` | `725` | `25` | `0` | `0` | 100% conciliado (`139` anónimas sin persona conservadas; sin NPS ficticio). |
| `fact_movimientos_crm` | `77` | `12` | `77` | `16` | `0` | `0` | 100% conciliado (PK subrogada `MOV-0001..0077`). |
| `audit_registros_duplicados` | `122` | `13` | `122` | `18` | `0` | `0` | 100% conservados y clasificados en 4 tipologías. |

---

## 4. Integración con el Backend (Servicios y Repositorios)

- **Módulo de Afiliados (`app/modules/affiliates/`)**:
  - `AffiliatesRepository` y `AffiliatesService` consultan `gold_agg_retencion_empresa` y `gold_agg_participacion_empresa` (vía PostgreSQL `Session` o Parquet en `input/gold/`).
  - Endpoints: `GET /affiliates/summary` y `GET /affiliates/participation`.
- **Módulo de Analítica (`app/modules/analytics/`)**:
  - `AnalyticsRepository` y `AnalyticsService` consultan `gold_agg_participacion_empresa` y `gold_agg_satisfaccion_encuestas`.
  - Endpoints: `GET /analytics/metrics` y `GET /analytics/satisfaction`.
- **Módulo de Retención (`app/modules/retention/`)**:
  - `RetentionRepository` y `RetentionService` consultan `gold_agg_retencion_empresa`.
  - Endpoints: `GET /retention/overview`, `GET /retention/companies` y `POST /retention/evaluate`.

---

## 5. Entregable 6: Recomendaciones de Captura de Datos (ACTHO)

Para garantizar que el modelo Medallion y el tablero se mantengan actualizados sin reprocesos manuales ni pérdida de trazabilidad, se recomiendan los siguientes ajustes operativos en la captura de información:

1. **Identificador único de empresa y persona en todos los formularios:**
   - Exigir **NIT / código de empresa** y **documento o correo corporativo** en los formularios de inscripción a eventos y en las encuestas de satisfacción, evitando registros anónimos o vínculos ambiguos por texto libre.
2. **Catálogo cerrado de ejecutivas KAM y campos del CRM:**
   - Usar listas desplegables cerradas para `ejecutiva_kam`, `nivel_membresia` (`Conectar`, `Crecer`, `Liderar`), `sector_economico` y `ciudad`, evitando variantes de escritura (`"Sin asignar"` vs `"Sin asignar (cuenta ACTHO)"`).
3. **Trazabilidad explícita de `id_evento` en encuestas:**
   - Incluir el identificador o código del evento (`id_evento`) como parámetro oculto (UTM / query param) en el enlace de cada encuesta post-evento, para permitir el cálculo de **Satisfacción y NPS por evento y línea 2027**.
4. **Estandarización de la pregunta NPS (escala 0–10) y Encuesta de 90 días:**
   - Incorporar la pregunta estándar *"¿Qué tan probable es que recomiende ACTHO a un colega? (0 a 10)"* tanto en encuestas post-evento como en la nueva encuesta de 90 días, marcando el campo `tipo_encuesta` (`POST_EVENTO` vs `ENCUESTA_90_DIAS`) para que Gold calcule el **NPS de ACTHO** sin mezclarlo con el **NPS por evento**.
5. **Control de fechas y autorización de datos:**
   - Validar formato ISO (`YYYY-MM-DD`) en `fecha_afiliacion` y `fecha_expiracion` en CRM, y mantener obligatorio el campo booleano `autoriza_tratamiento_datos` para habilitar la exportación segura de los 8 segmentos de comunicaciones.
