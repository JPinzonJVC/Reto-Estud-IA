# ACTHO 360: métricas del dashboard e instalación desde cero

Fecha de actualización: 27 de noviembre de 2026  
Rama de implementación: `codex/ml-actho360-audit`

## 1. Dónde están los modelos y si se exportaron

El código de Machine Learning está en `app/modules/eda/ml/`:

- `common/`: validaciones, preprocesamiento, métricas, cortes temporales y registro de artefactos.
- `fidelity/`: dataset, features RFM-S, entrenamiento/evaluación e inferencia de clusters.
- `recommender/`: dataset de asistencias y afinidad histórica por línea de eventos.
- `churn/`: score heurístico y semáforo de riesgo.
- `persistence.py`: generación y persistencia idempotente de resultados descriptivos, con exportación y reutilización automática del artefacto K-Means RFM-S.

**Exportación y reutilización de artefactos (`.joblib` + `manifest.json`):**
El modelo no supervisado de Fidelización (`fidelidad_rfm_s`) se exporta automáticamente en la primera corrida hacia `ACTHO_ML_ARTIFACTS_DIR` (por defecto `/var/lib/actho/ml_artifacts` en Docker o `./input/ml_artifacts` en local, ambos excluidos de Git). Esto genera:
- `fidelidad_rfm_s/actho-descriptive-v1/fidelidad_rfm_s-actho-descriptive-v1.joblib`
- `fidelidad_rfm_s/actho-descriptive-v1/manifest.json` (con hash criptográfico SHA-256 y `"approved": true`)
- `runs/{execution_id}.json` (bitácora de auditoría por cada inferencia ejecutada)

Cuando ingresan nuevos datos (por ejemplo, una nueva corrida del ETL desde Prefect, el Monitor ETL o `persist_ml_descriptive_results.py`), el sistema **verifica el hash SHA-256 y reutiliza el `.joblib` exportado** sin volver a entrenar el K-Means. Si se desea forzar un re-entrenamiento con una nueva versión, se ejecuta `python -m scripts.persist_ml_descriptive_results --retrain`. Con el artefacto exportado, la tarjeta del dashboard **Modelos aprobados disponibles** pasa de `0` a `1`.

Además, no hay modelos supervisados aprobados para churn, asistencia o conversión de prospectos: faltan etiquetas positivas y negativas verificables. Las vistas de esos tres casos son heurísticas o descriptivas; no deben interpretarse como probabilidades.

## 2. Estado de los resultados persistidos

La base del proyecto está en Alembic `0005_gold_ml_resultados`. El 27 de noviembre de 2026 el ETL cargó 25 tablas y el proceso descriptivo dejó estos registros en `gold_ml_resultados_empresa`:

| Caso | Filas | Significado |
|---|---:|---|
| `fidelidad_rfm_s` | 140 | Score RFM-S y cluster descriptivo para empresas con satisfacción observada. |
| `recomendacion_linea` | 1.197 | Afinidad histórica por línea, con eventos de soporte. |
| `churn_heuristico` | 435 | Puntos y semáforo de negocio ya calculados en Gold. |
| `lead_prioridad` | 720 | Prospectos con al menos una interacción positiva observada. |
| **Total** | **2.492** | Filas resultado, no empresas únicas. |

El corte actual es `2026-11-27`, versión `actho-descriptive-v1`, ejecución `184b501f-8b89-44a2-b272-5498161f2e67`. De los 796 prospectos auditados, 76 no tienen participación observable y se excluyeron sin etiquetarlos como negativos.

## 3. Cómo leer las métricas del dashboard

Los filtros de periodo, KAM, membresía, sector, tamaño, ubicación, línea y modalidad modifican las vistas a las que aplican. El corte de datos aparece en la barra superior.

### Resumen ejecutivo DWH

| Indicador | Definición |
|---|---|
| Afiliados activos | Número de empresas marcadas con membresía activa en Gold para el corte. |
| Permanencia histórica | `afiliados activos / (afiliados activos + ex-afiliados) × 100`. Es una proporción del snapshot; no es una tasa de supervivencia por cohorte. |
| En servicios | Porcentaje de afiliados activos con `total_eventos_anio > 0`; el detalle indica cantidad sobre afiliados activos. Mide participación anual, no satisfacción. |
| Asistencias | Registros de asistencia de los eventos visibles con los filtros actuales. El detalle separa afiliados y leads. No equivale a personas únicas. |
| Renovaciones | Suma de renovaciones registradas en los movimientos CRM que cumplen los filtros actuales. Es un conteo, no una probabilidad ni una tasa. |
| Satisfacción | Promedio ponderado por número de respuestas en escala Likert 1–5. El NPS oficial solo aparece si existen respuestas válidas en escala 0–10. |
| Vencen en 90 días | Afiliaciones activas cuya fecha de fin está entre la fecha de referencia y los 90 días siguientes, inclusive. |
| Semáforo de riesgo | Conteo ROJO/AMARILLO/VERDE proveniente de reglas heurísticas de negocio. No es churn probabilístico. |

El NPS oficial se calcula como `(% respuestas 9–10) − (% respuestas 0–6)`; las respuestas 7–8 son neutrales. Con los datos actuales no hay respuestas NPS válidas, por eso puede aparecer como no disponible. El NPS adaptado a escala 1–5 que algunas vistas históricas muestran no es el NPS oficial.

### Eventos y KPIs

Las vistas de participación agrupan asistencias por evento, línea de oferta y modalidad. Incluyen conteos de asistencias, afiliados/leads, empresas y personas distintas, promedio por evento, participación de leads y penetración de afiliados activos. La penetración relaciona empresas afiliadas asistentes con la población activa usada por el KPI; no representa conversión comercial.

La evolución mensual presenta altas nuevas, vencimientos programados, renovaciones efectivas y retiros/cancelaciones. La tasa de renovación se calcula como `renovaciones efectivas / vencimientos programados × 100`; la tasa de retiros usa el mismo denominador. Si no hay vencimientos en el periodo, la tasa no se calcula.

### Sectores, cartera y satisfacción

Los KPIs de cartera segmentan empresas por sector, subsector, tamaño, rango de empleados, nivel y datos de membresía. Según la dimensión muestran cantidad de empresas, afiliados activos/ex-afiliados/prospectos, participación anual, riesgo y satisfacción observada. Los resultados son descriptivos del conjunto filtrado.

Las vistas de satisfacción reportan respuestas y promedio Likert 1–5, dimensiones de experiencia y temas de texto/NLP disponibles. La ausencia de respuesta no se imputa como satisfacción neutral ni negativa.

### Dashboard de Machine Learning

| Métrica | Qué significa |
|---|---|
| Resultados disponibles | Filas almacenadas para los cuatro casos en el corte vigente. Una misma empresa puede aparecer en más de un caso; no es un conteo de empresas únicas. |
| Último corte | Fecha de corte de resultados ML; se conserva aparte del momento en que el usuario abrió la pantalla. |
| Métodos activos | Casos de uso con resultados en el corte vigente, de un máximo de cuatro. No significa que sean modelos supervisados aprobados. |
| Modelos aprobados disponibles | Manifiestos con `approved=true` encontrados bajo `ACTHO_ML_ARTIFACTS_DIR`. Con el artefacto K-Means RFM-S exportado muestra `1` (o `0` antes de la primera corrida). |
| Fidelización RFM-S | Promedio de cinco percentiles de cohorte: recencia inversa, frecuencia de eventos, amplitud de participación, antigüedad/ciclos y satisfacción. Va de 0 a 100 y es relativo a la cohorte del corte; solo cubre empresas con satisfacción observada. |
| Segmentos RFM-S | Grupos KMeans descriptivos. El cluster no es probabilidad de retención ni etiqueta comercial validada. |
| Afinidad histórica | `eventos distintos de la línea recomendada / eventos distintos de la empresa × 100`. El soporte es el número de eventos distintos observados en esa línea. No es probabilidad de asistir. |
| Riesgo heurístico | Puntos de reglas y semáforo heredados de Gold, acompañados por señales explicativas. No es una probabilidad de churn. |
| Prioridad de prospecto | Orden por eventos históricos observados; el soporte indica la interacción. No hay score numérico ni probabilidad de conversión. |

En la evaluación exploratoria de fidelización, el candidato KMeans con `k=2` obtuvo silhouette `0,332`, Davies–Bouldin `1,225`, Calinski–Harabasz `83,500` y ARI entre semillas `1,000`. Son métricas de estructura y estabilidad del clustering; no validan impacto de negocio ni predicen permanencia. No hay ROC-AUC, PR-AUC ni Brier de churn/asistencia/conversión porque no existe una cohorte supervisada con etiquetas confiables.

## 4. Instalación completa desde cero

### Requisitos

- Git.
- Docker Desktop iniciado, con Docker Compose v2.
- El paquete de datos ACTHO autorizado. Los archivos bajo `input/` no se distribuyen en Git.
- Puertos locales disponibles: `5432` (PostgreSQL), `8000` (FastAPI) y `4200` (Prefect).

Docker construye el bundle React y las dependencias Python. Node.js solo hace falta si se desarrollará el frontend fuera de Docker.

### 4.1 Clonar la rama y preparar datos

```powershell
git clone --branch codex/ml-actho360-audit https://github.com/JPinzonJVC/Reto-Estud-IA.git
Set-Location .\Reto-Estud-IA
```

Si el paquete autorizado es `input.zip` y contiene la carpeta `input/`, extráelo en la raíz del proyecto en una instalación limpia:

```powershell
Expand-Archive -LiteralPath .\input.zip -DestinationPath . -Force
```

Comprueba que estén disponibles, al menos, `input/normalizados/`, `input/normalizados/duplicados/` y las fuentes en `input/CSV/`. No subas `input.zip`, CSV, Parquet ni `.env` al repositorio.

### 4.2 Configurar y levantar servicios

Compose admite valores por defecto de desarrollo. Para personalizarlos, crea `.env` en la raíz (está ignorado por Git), por ejemplo:

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=cambia-esta-clave-local
POSTGRES_DB=estudia_db
EDA_SCHEDULE_CRON=0 6 * * 1
EDA_SCHEDULE_TIMEZONE=America/Bogota
EDA_DEPLOYMENT_NAME=eda-medallion-weekly
```

Levanta la aplicación, PostgreSQL, Prefect Server y Prefect Worker:

```powershell
docker compose up --build -d
docker compose ps
```

Espera a que PostgreSQL, la aplicación y Prefect estén saludables. Para revisar el arranque:

```powershell
docker compose logs --tail=100 app postgres prefect-server prefect-worker
```

### 4.3 Aplicar migraciones, cargar DWH y generar resultados ML

Ejecuta los pasos en orden desde la raíz del repositorio:

```powershell
docker compose exec app python -m alembic upgrade head
docker compose exec app python -m app.modules.eda
docker compose exec app python -m scripts.validate_ml_postgres_integration
docker compose exec app python -m scripts.persist_ml_descriptive_results
```

- Alembic instala `gold_ml_resultados_empresa` y deja el esquema al día.
- El ETL reconstruye Silver/Gold desde los archivos de entrada y los persiste en PostgreSQL.
- El validador crea una tabla en un esquema temporal, prueba upgrade/downgrade/re-upgrade y dos ejecuciones idempotentes; revierte esa transacción al terminar. Requiere que el ETL ya haya cargado datos.
- El último comando persiste los resultados descriptivos reales al corte del día. Puede repetirse para el mismo corte/version sin duplicar filas.

No ejecutes el ETL sobre una base con cambios que deban conservarse sin revisar primero sus efectos. No uses `docker compose down -v` como apagado normal: elimina `postgres_data` y reinicia las bases de ACTHO y Prefect. Para detener servicios preservando datos usa `docker compose down`.

### 4.4 Abrir y verificar

- Dashboard ACTHO: `http://localhost:8000/dashboard`
- Documentación OpenAPI: `http://localhost:8000/docs`
- Prefect UI: `http://localhost:4200`
- Resumen ML: `http://localhost:8000/ml/resumen`
- Resultados ML: `http://localhost:8000/ml/resultados/fidelidad_rfm_s` (también `recomendacion_linea`, `churn_heuristico` y `lead_prioridad`)

`/ml/resumen` debe mostrar el total del corte, métodos activos y modelos aprobados. Los endpoints de resultados aceptan `buscar_empresa`, `segmento`, `estado`, `limit` y `offset`.

### 4.5 Desarrollo del frontend sin reconstruir la imagen

Con API y PostgreSQL activos, en otra terminal:

```powershell
Set-Location .\frontend
npm ci
npm run dev
```

Usa la ruta integrada `http://localhost:8000/dashboard` para revisar la aplicación servida por FastAPI. Vite está disponible en `http://localhost:5173` para el ciclo de desarrollo. Al cambiar el bundle que se sirve en Docker, reconstruye `app` con `docker compose up --build -d app`.

### 4.6 Artefactos de modelos futuros

Si se incorpora un modelo aprobado, define `ACTHO_ML_ARTIFACTS_DIR` en el servicio que lo entrena/consume y monta ahí un directorio o volumen persistente **fuera del repositorio**. El registro genera `{modelo}/{versión}/{modelo}-{versión}.joblib` y `manifest.json`, verifica SHA-256 al cargar y rechaza manifiestos no aprobados. No exportes artefactos a Git ni a la carpeta `input/`.
