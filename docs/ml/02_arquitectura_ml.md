# Arquitectura propuesta de Machine Learning — ACTHO 360

## Estado

La auditoría y la base común de validación/evaluación están implementadas. Fidelity tiene
un flujo exploratorio de features, entrenamiento, inferencia y comparación de clusters.
No hay modelos supervisados aprobados; ya existe persistencia descriptiva versionada en Gold.

## Límites del diseño

- Leer Silver como fuente de hechos y atributos; usar Gold como salida analítica.
- No cambiar transformaciones Silver existentes para acomodar un modelo.
- Mantener feature engineering puro y separado de consultas/persistencia.
- Separar entrenamiento supervisado, inferencia y análisis no supervisado.
- Un entrenamiento solo puede aprobarse con dataset, corte y evaluación registrados.
- El entrenamiento no debe ser parte obligatoria de cada ETL.
- No registrar datos personales crudos en el registro de modelos ni en logs.

## Estructura objetivo

La propuesta original `app/modules/eda/ml/` encaja con la frontera Medallion y evita
mezclar casos de uso nuevos con el módulo de ejemplo `app/modules/machine_learning/`.
Se recomienda evolucionar así, una vez disponibles los datos:

```text
app/modules/eda/ml/
  common/
    datasets.py       # lecturas limitadas a tablas y columnas aprobadas
    validation.py     # contratos, nulos, rangos, fechas y corte
    preprocessing.py # transformadores sklearn reutilizables
    metrics.py        # métricas por tarea y split
    registry.py       # metadatos de modelo/dataset/ejecución
    artifacts.py      # lectura/escritura segura de joblib fuera del repositorio
  churn/
    dataset.py features.py train.py predict.py scoring.py
  fidelity/
    dataset.py features.py train.py predict.py archetypes.py
  recommender/
    dataset.py features.py train.py predict.py recommendation.py
  lead_scoring/
    dataset.py features.py train.py predict.py
  pipeline.py        # inferencia y entrenamiento son comandos separados
```

El código ML existente (`app/modules/machine_learning`) no debe importarse como fuente
de datasets: contiene estimadores de juguete y fallback de inferencia no compatible con
un modelo aprobado. Los endpoints `/ml/status` son estado de integración, no prueba de
validación estadística.

Implementado en esta rama: `common/validation.py`, `common/preprocessing.py`,
`common/temporal.py`, `common/metrics.py`, `common/registry.py`, `churn/scoring.py`,
`fidelity/{dataset,features,train,predict}.py` y un baseline de afinidad en
`recommender/{dataset,recommendation,train}.py`. Los perfiles reproducibles están en
`scripts/profile_ml_readiness.py` y `scripts/profile_ml_source_files.py`.

## Versionado y persistencia

Cada ejecución aprobada deberá registrar al menos: `model_id`, nombre/versión, algoritmo,
fecha de entrenamiento, corte temporal, versión del esquema de features, tamaño de
muestra, métricas de validación, ruta/hash del artefacto, `execution_id` y fecha de
predicción. El artefacto deberá quedar fuera de Git y de la imagen de producción, con
permisos de lectura restringidos y hash comprobado al cargar.

Se recomienda una tabla de registro de modelos/ejecuciones, separada de `audit_*` ETL.
Las predicciones empresa-nivel pueden actualizar únicamente las columnas ML ya presentes
en `gold_dim_empresa_360`. Deben actualizarse en una transacción idempotente y solo tras
validar población, rango, valores finitos y versión aprobada.

La probabilidad de asistencia es específica del evento. Cuando haya convocatoria válida,
se persistirá en una tabla de granularidad empresa-evento (clave compuesta de empresa,
evento y versión/ejecución del modelo), no en una probabilidad ambigua por empresa.

## Flujo

1. Validar que Silver existe, que las claves y fechas son utilizables y que el corte está
   disponible.
2. Construir dataset y manifiesto de fuentes/columnas, sin extraer información personal
   innecesaria.
3. Validar etiquetas, ventanas, censura, población y fuga temporal.
4. Entrenar modelos reproducibles dentro de pipeline scikit-learn y comparar con una
   referencia simple.
5. Evaluar con corte temporal; seleccionar y aprobar versión fuera de la ruta de
   inferencia.
6. Ejecutar inferencia solo con artefactos aprobados y el esquema de features esperado.
7. Validar resultados y registrar ejecución.
8. Persistir Gold de forma atómica e idempotente; fallar sin tocar Gold si hay inválidos.

## Decisiones por modelo

- **Churn:** unidad de entrenamiento = empresa-ciclo al corte. La etiqueta depende de
  renovación/no renovación observada dentro del horizonte y debe excluir casos censurados.
  La heurística existente sigue separada de la probabilidad del clasificador.
- **Fidelidad:** primero score RFM-S determinista y validación de perfiles; comparar
  KMeans/GaussianMixture solo después de medir escala, estabilidad e interpretabilidad.
  Los nombres comerciales se asignan tras perfilar clusters.
- **Recomendación:** línea recomendada y probabilidad de asistencia son tareas distintas.
  Las líneas pueden tener baseline por afinidad histórica; la asistencia requiere
  oportunidades verificables de convocatoria.
- **Lead scoring:** unidad = empresa prospecto al inicio de oportunidad; exigir conversión
  definida y seguimiento completo para negativos. La probabilidad calibrada se transforma
  a score 0–100, sin presentarlo como garantía.

## Ejecución disponible y límites

La base común permite dividir datasets por fecha, encapsular imputación/escala/codificación
en pipelines, validar etiquetas binarias y calcular métricas fuera de muestra. Fidelity
separa `train_fidelity_model` de `predict_fidelity_clusters`; su inferencia exige features
en la escala de percentiles de la cohorte del modelo.

La evaluación de fidelidad se ejecuta con `python -m app.modules.eda.ml.fidelity.train`;
lee PostgreSQL y no modifica Gold. El entrenamiento de churn, lead scoring y propensión
de asistencia no se habilita hasta que existan etiquetas y poblaciones verificadas.

## Pendientes para diseño detallado

- Acordar horizontes y reglas de censura de churn y conversión.
- Medir volumen, calidad, cobertura por año y clases de cada dataset real.
- Acordar de dónde sale la evidencia de empresas convocadas y la política de acceso a
  datos personales.
- Elegir almacén y retención de artefactos/auditoría en el entorno de despliegue.

## Integración implementada en esta rama

La migración `0005_gold_ml_resultados` agrega una tabla versionada por empresa, caso,
versión y fecha de corte. `python scripts/persist_ml_descriptive_results.py` persiste
segmentos RFM-S solo para empresas con satisfacción observada, afinidad histórica con
soporte, el score heurístico que ya existe en Gold y una priorización descriptiva de
prospectos con interacción observada. La tabla guarda método, estado, explicación,
métricas y hash de dataset cuando corresponde. El upsert es idempotente para el mismo
corte y conserva los cortes/versiones previos.

Consulta REST: `GET /ml/resultados/{caso_uso}` con filtro opcional `id_empresa` y `limit`.
Casos: `fidelidad_rfm_s`, `recomendacion_linea`, `churn_heuristico` y `lead_prioridad`.
Estos resultados se distinguen como `EXPERIMENTAL`, `DESCRIPTIVO` o `HEURISTICO` y no
llenan columnas de probabilidad reservadas ni se generan por petición HTTP.

Aplicación local después de disponer de PostgreSQL:

```powershell
python -m alembic upgrade head
python scripts/persist_ml_descriptive_results.py
```
