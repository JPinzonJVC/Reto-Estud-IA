# Auditoría de viabilidad de Machine Learning — ACTHO 360

**Fecha de auditoría:** 2026-11-27  
**Rama:** `codex/ml-actho360-audit`  
**Alcance:** inspección del código, ORM, migraciones, documentación, archivos locales y
perfilado agregado de PostgreSQL en ejecución. No se entrenaron modelos.

## 1. Resumen ejecutivo

El proyecto ya tiene un modelo dimensional Silver/Gold y columnas Gold reservadas para
varios resultados de ML. También existe `app/modules/machine_learning`, pero su código
actual es de ejemplo: usa nombres de variables genéricos, permite entrenar con cinco
filas sintéticas y no construye datasets desde Silver. Los endpoints `/ml` reportan
espacios reservados; no prueban que haya modelos ACTHO entrenados ni aprobados.

En este worktree, `input/CSV`, `input/normalizados`, `input/bronze`, `input/silver` e
`input/gold` solo contienen `.gitkeep`. El checkout operativo `D:\Retos_StudIA\input`
sí conserva fuentes Bronze y archivos Silver/Gold Parquet; se perfilaron sin imprimir
filas ni identificadores. PostgreSQL se inició desde WSL sobre el volumen existente y se
perfiló con consultas agregadas de solo lectura. Las cifras históricas de
`docs/README_EDA_MEDALLION_ACTHO360.md` coinciden con varias tablas de la base actual,
pero el conteo de prospectos actual es 796 (no 799). No se consultaron ni exportaron
valores de identificación personal.

**Conclusión:** la factibilidad de construir código y datasets estática es buena; la
viabilidad estadística de los cuatro modelos no está demostrada. No se deben ajustar,
calibrar ni publicar modelos hasta disponer de datos reales y verificar las etiquetas.

## 2. Componentes auditados

- ETL: `app/modules/eda/raw_builder.py`, `bronze.py`, `silver.py`, `gold.py`,
  `pipeline.py` y `postgres_loader.py`.
- ORM y migraciones: modelos Silver/Gold en `app/modules/eda/models/` y migraciones
  `rev_0001` a `rev_0004`.
- ML existente: `app/modules/machine_learning/{features,training,prediction,schemas,router}.py`.
- Configuración: `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`,
  `app/modules/eda/config.py` y `app/database.py`.
- Datos en el worktree nuevo: no hay archivos bajo `input/`.
- Datos en checkout operativo `D:\Retos_StudIA\input`: Parquet Silver/Gold y CSV Bronze;
  perfilado con `scripts/profile_ml_source_files.py`.
- PostgreSQL: esquema Silver/Gold presente; se consultaron conteos, nulos, rangos,
  categorías y cobertura agregada.
- Pruebas: `tests/test_features.py`, `test_training.py`, `test_prediction.py`,
  `test_postgres_medallion.py` y `test_dashboard_and_ml_endpoints.py`.

Las dependencias necesarias ya están declaradas: pandas, NumPy, scikit-learn, joblib,
SQLAlchemy y Alembic. No se ve una necesidad inmediata de sumar bibliotecas de ML.

## 3. Variables y trazabilidad disponibles en el esquema

| Caso de uso | Variables/relaciones en Silver y Gold | Etiqueta verificable en el esquema | Limitaciones observadas |
|---|---|---|---|
| Churn | ciclos y fechas de membresía; asistencias; respuestas/NPS; movimientos CRM; atributos de empresa; Gold ya calcula días de expiración, recencia, eventos, personas y alertas | `SilverMembresia` guarda estado y vigencia; movimientos CRM distinguen cierre facturado, tipo y fecha | Hace falta reconstruir ciclos y fecha de renovación/no renovación con datos reales. El estado actual, la inactividad o `es_empresa_activa` no bastan como etiqueta. |
| Fidelidad | Gold contiene eventos/asistencias, personas distintas, ciclos, recencia, satisfacción y NPS; Silver permite volver a agregar historial | No requiere etiqueta supervisada | La población, el corte temporal, la imputación y el perfil de los clusters dependen de datos actuales. La cardinalidad podría ser pequeña para comparar clusters de forma estable. |
| Recomendación de línea | evento tiene fecha, línea, modalidad y detalle; asistencia enlaza empresa/evento/persona; empresa aporta sector/tamaño; encuestas incluyen satisfacción y textos sugeridos | Asistencia observada es positiva | El esquema no registra de forma suficiente empresas convocadas que no asistieron. No se puede tratar toda ausencia de asistencia como negativa. Línea histórica no demuestra preferencia futura para 2027. |
| Lead scoring | empresas incluyen relación, sector, tamaño y KAM; eventos/asistencia identifican invitados; CRM registra movimientos, cierres y fechas | Cierre facturado puede ser positivo si es nueva afiliación y se enlaza con fiabilidad | No se encontró una tabla de oportunidades de prospectos con exposición/seguimiento completo y ventana de conversión. No afiliado no equivale a negativo. |

## 4. Perfilado real de PostgreSQL

Consulta agregada en la base `estudia_db`; corte observado de tablas/fechas disponibles,
sin descargar registros individuales.

| Tabla | Filas | Hallazgo de cobertura |
|---|---:|---|
| `silver_dim_empresas` / `gold_dim_empresa_360` | 1.851 / 1.851 | Gold: 435 afiliados activos, 620 ex-afiliados y 796 prospectos no afiliados |
| `silver_membresias` | 1.057 | 1.055 empresas distintas; 339 sin inicio, 428 sin fin; 71 ciclos “Sin dato” sin ninguna fecha |
| `silver_fact_movimientos_crm` | 77 | 39 tratos abiertos sin membresía/cierre; 14 nuevas afiliaciones Zoho cerradas; 10 nuevos afiliados de listado cerrados; 14 renovaciones cerradas |
| `silver_fact_asistencias` | 3.401 | 1.197 empresas distintas; 15 sin empresa; las 3.401 tienen persona y autorización conocida; 33 eventos referenciados |
| `silver_fact_encuestas_satisfaccion` | 725 | 329 empresas distintas; 142 sin empresa, 139 sin persona; ninguna tiene NPS; todas tienen autorización de actualizaciones conocida |
| `silver_dim_eventos` | 34 | 4 líneas; 23 presenciales, 10 virtuales y 1 híbrido; fechas 2026-01-05 a 2026-10-27 |
| `gold_fact_encuestas_bi` | 725 | 546 tienen texto sugerido; 514 tienen categoría NLP; ninguna está enlazada a un evento |

Los identificadores primarios no presentan duplicados en los Parquet perfilados de las
tablas indicadas. Este control no descarta duplicados semánticos por claves de negocio
alternativas. Las 725 encuestas son `POST_EVENTO`, pero `id_evento` está nulo en todas;
no hay NPS observado. En Silver empresa, el sector falta en 1.124/1.851 y el tamaño en
1.389/1.851; los faltantes se concentran en prospectos/ex-afiliados. La autorización de
tratamiento está definida para las 3.401 asistencias y las 725 encuestas (sí/no).

Los movimientos CRM enlazan con empresa y membresía cuando hay `id_membresia`; los 39
tratos no cerrados no tienen membresía. En Gold, todos los 435 afiliados activos tienen
un puntaje heurístico y semáforo calculado. Las columnas `probabilidad_churn_ml`,
`score_fidelidad_ml_0_100`, `score_conversion_lead_ml_0_100`,
`linea_2027_recomendada_ml` y `prob_asistencia_prox_evento_ml` están pobladas en **0**
filas.

Detalle de membresías: 493 `Cancelado` (252 sin inicio y 345 sin fin), 436 `Activo` (12
sin inicio y 11 sin fin), 71 `Sin dato` sin fechas, 33 `Periodo de Gracia`, 14 `Expirado`,
8 `Pronto a Expirar` y 2 `Inactivo`. Hay ciclos con fecha final en 2027, así que el
horizonte de observación y la fecha de corte deben fijarse antes de asignar no-renovación.

Una exploración de ventanas de 90 días, limitada a ciclos con inicio/fin y madurados al
2026-10-29, encontró 129 ciclos en 129 empresas. Ninguno tiene un ciclo siguiente dentro
de 90 días ni un movimiento de renovación facturado en la ventana de ±90 días. Esto no
demuestra que los 129 sean churn: también puede reflejar que el historial de ciclos no
está completo. No se obtiene una clase positiva verificable de renovación desde esta
cohorte.

Cobertura Gold por población: afiliados activos — 344 con asistencia, 140 con encuesta,
15 sin sector y 83 sin tamaño; ex-afiliados — 133 con asistencia, 52 con encuesta, 313
sin sector y 510 sin tamaño; prospectos — 720 con asistencia, 137 con encuesta y 796 sin
sector y tamaño. No se encontraron movimientos CRM etiquetados como leads perdidos ni
una tabla de convocatorias empresariales.

Otros campos presentes: `autoriza_tratamiento_datos` en asistencias, `desea_recibir_actualizaciones`
en encuestas, y controles derivados en `gold_mart_segmentos_comunicaciones` (`apto_envio_comunicaciones`).
Estos permisos deben respetarse en cualquier uso de contacto; no son etiquetas de propensión.

## 5. Calidad, cobertura y problemas de identificación

Aunque hay tablas en PostgreSQL, los CSV/Parquet locales no están presentes. Se midieron
conteos, nulos y categorías en tablas principales; quedan pendientes duplicados por
claves de negocio, rangos de todas las features y conciliación fuente-destino.

Riesgos identificados por esquema y transformaciones:

- Encuestas anónimas o sin vínculo (`id_empresa`/`id_persona` nulos) no se deben asignar
  artificialmente a empresas; el histórico documenta 142 encuestas sin empresa.
- Asistencias sin empresa o persona no permiten agregación confiable por empresa; el
  histórico documenta 15 asistencias sin empresa.
- Los movimientos CRM tienen fechas nulas en el conjunto histórico (63 expiraciones
  sin fecha, según documentación); deben excluirse o tratarse como censurados.
- Fechas ISO están modeladas como texto; parsing estricto y cobertura temporal son
  prerrequisitos para cualquier split temporal.
- Membresías repetidas por empresa requieren orden y resolución de solapamientos antes
  de construir ciclos. No asumir que “último registro” por orden de archivo sea el último
  cronológicamente.
- Algunos datos de actividad aparecen agregados en Gold para un periodo de análisis;
  validar que la ventana y fecha de corte correspondan a cada etiqueta.
- Varias claves foráneas de asistencia/encuesta son opcionales; medir cobertura real de
  `id_empresa`, `id_persona` e `id_evento` al recuperar los datos.

## 6. Riesgo de leakage

- Churn: excluir estado de ciclo, fecha de expiración posterior al corte, cierres de
  renovación y cualquier interacción posterior a la fecha de predicción.
- Fidelidad: calcular recencia, frecuencia, antigüedad y satisfacción solo con eventos
  disponibles hasta un corte explícito. No usar agregados Gold que incluyan periodos
  posteriores al corte.
- Recomendador: no usar fecha, asistencia, encuesta o atributos de un evento ocurrido
  después de la predicción. Para negativos de asistencia, exigir evidencia de invitación.
- Lead scoring: excluir movimientos de cierre, estados finales y variables CRM creadas
  después de la fecha inicial de scoring. Excluir negativos con ventana de seguimiento
  incompleta (censura).
- La normalización, imputación, codificación, selección de variables y calibración deben
  ajustarse dentro del fold de entrenamiento; nunca antes del split temporal.

## 7. Matriz de viabilidad

| Modelo | Variables disponibles | Etiquetas disponibles | Cobertura temporal | Viabilidad actual |
|---|---|---|---|---|
| Churn | Sí; 1.057 ciclos | 129 ventanas maduras sin renovación observable; cero renovaciones asociadas en esa cohorte | Ciclos desde 1977 hasta 2027; 339/1.057 sin inicio y 428/1.057 sin fin | **No entrenable: no hay dos clases verificadas ni evidencia completa de historial** |
| Fidelidad | Sí; 435 afiliados activos, hechos de asistencia y métricas Gold | No requiere | 344/435 activos con asistencia; 140/435 con satisfacción; 0% NPS | **RFM-S exploratorio evaluado en 140; score/cluster no representativo de los 435 todavía** |
| Recomendador | Parcialmente sí; 34 eventos y 4 líneas | 3.401 positivos observados; faltan negativos de convocatorias verificables | Eventos entre enero y octubre de 2026; ninguna encuesta Gold enlazada a evento | **Afinidad histórica posible; propensión de asistencia no entrenable aún** |
| Lead scoring | Parcial; 796 prospectos, atributos sin sector/tamaño en el universo actual | 24 cierres de alta (14 Zoho + 10 listado) son candidatos positivos; negativos calificados no verificados | CRM disponible en el periodo reciente; 39 tratos abiertos | **No entrenable; pocos positivos y sin negativos con seguimiento completo** |

## 8. Recomendaciones y bloqueos

1. El perfilado agregado de tablas y llaves primarias se puede reproducir con
   `scripts/profile_ml_readiness.py` (PostgreSQL) y
   `scripts/profile_ml_source_files.py D:\Retos_StudIA\input` (archivos). Aún falta
   contrastar duplicados semánticos y conciliación Bronze–Silver.
2. Conseguir historial completo de ciclos y confirmar fechas reales de renovación; definir
   fecha de corte, horizonte y censura para churn y lead scoring.
3. Resolver la procedencia verificable de convocatorias/no asistencias para el modelo
   empresa-evento.
4. Construir splits temporales y reportar tamaños de train/validación/test, distribución
   de clases y número de periodos independientes antes de seleccionar algoritmos.
5. Mantener fidelidad como score descriptivo hasta comprobar estabilidad e interpretación
   comercial; no presentar clusters como predicciones de retención.
6. No guardar artefactos de los modelos sintéticos actuales como modelos de producción.
   `bootstrap_default_models()` genera artefactos con datos artificiales y debe retirarse
   o quedar claramente separado de la ruta de entrenamiento real.
7. Usar `gold_dim_empresa_360` para valores al nivel empresa. La probabilidad por
   empresa-evento necesita una tabla con clave compuesta empresa/evento y metadatos del
   modelo; no cabe correctamente en una sola columna de la dimensión.

## 9. Próxima puerta de fase

La fase 0 de inspección de código y perfilado agregado de Silver/Gold está completada.
Antes de entrenar, siguen pendientes la revisión de duplicados desde fuentes, las reglas
de corte/horizonte y la validación de etiquetas. La ausencia de convocatorias y de
negativos de conversión impide entrenar dos modelos supervisados en su definición actual.
Esto no se sustituirá con etiquetas inferidas a partir de inactividad o ausencia de
asistencia.
