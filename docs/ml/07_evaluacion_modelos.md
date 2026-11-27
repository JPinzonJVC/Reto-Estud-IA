# Evaluación de modelos ACTHO 360

## Churn

No evaluado: no existe una cohorte actual con dos clases de renovación verificadas.
Las métricas de churn no se inventan ni se reemplazan por métricas heurísticas.

## Fidelidad

Evaluación no supervisada en 140 empresas con satisfacción observada. Cinco semillas,
KMeans y GaussianMixture, k=2…6. Los resultados completos se imprimen con
`python -m app.modules.eda.ml.fidelity.train` y se resumen en
`04_modelo_fidelidad.md`. El candidato KMeans k=2 tiene silhouette 0,332, Davies–Bouldin
1,225, Calinski–Harabasz 83,500 y ARI medio entre semillas 1,000.

La estabilidad medida solo varía la semilla sobre el mismo snapshot; falta bootstrap o
validación temporal. No hay métrica de negocio ni aprobación de arquetipos.

## Recomendación de asistencia y lead scoring

No evaluados por ausencia de negativos confiables. No aplicar accuracy, ROC-AUC ni PR-AUC
sin etiquetas válidas y ambas clases con cobertura temporal.

## Validación de implementación

En la revisión final, 39 pruebas dirigidas de ML, predicción y endpoints pasaron en Windows. Flake8 y `git diff --check` quedaron limpios; el build frontend ejecutó TypeScript y Vite correctamente. El host Windows no tiene Alembic y omite la prueba de compilación DDL cuando el paquete falta.

La suite completa y el caso `test_dashboard_overview_filtros_y_evolucion` no terminan en este host: el fixture se queda al entrar en `TestClient(app)` antes de enviar la primera petición. Esto sitúa el bloqueo en el arranque de Starlette/AnyIO con el event loop de Windows, no en la consulta del dashboard. WSL devuelve `WSL/E_ACCESSDENIED`, por lo que no se pudo completar la repetición en Linux durante esta fase. La migración 0005 y el flujo de downgrade/reaplicación quedan pendientes de validar en una base de pruebas PostgreSQL accesible; no se aplicaron cambios en la base compartida.
