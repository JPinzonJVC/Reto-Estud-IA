# Frontend de Machine Learning — ACTHO 360

## Integración

La vista ML está dentro del dashboard `/dashboard`, bajo la navegación existente y comparte
el bundle Vite + React + TypeScript del monitor Prefect. No es una aplicación independiente.
`frontend/src/pages/MlDashboard.tsx` compone el dashboard y los cuatro módulos; las llamadas
pasan por `frontend/src/api/ml.ts`. El dashboard existente despacha el evento `ml:activate`
cuando se abre la pestaña. La vista consulta la API al iniciar y al activarse.

El módulo presenta:

- Resumen agregado de resultados, último corte, casos disponibles y manifiestos aprobados.
- Fidelidad RFM-S con distribución y perfiles percentiles por cluster; la cohorte se limita a
  empresas con satisfacción observada.
- Recomendación por línea con porcentaje de afinidad histórica, soporte y explicación.
- Riesgo heurístico y señales observadas; declara que el modelo supervisado de churn no está
  disponible.
- Priorización de prospectos por participación histórica, sin score de conversión.
- Búsqueda de empresa, filtro por segmento/línea/semáforo, paginación, estados de carga, error
  y sin resultados.

No se añadieron dependencias. Los estilos propios están acotados a `.ml-shell`; se adapta al
modo oscuro del dashboard y a pantallas pequeñas. Las API existentes no implementan
autenticación; la vista utiliza los mismos controles de acceso actuales.

## API usada

- `GET /ml/resumen`
- `GET /ml/resultados/fidelidad_rfm_s`
- `GET /ml/resultados/recomendacion_linea`
- `GET /ml/resultados/churn_heuristico`
- `GET /ml/resultados/lead_prioridad`

El endpoint de resultados admite `buscar_empresa`, `segmento`, `estado`, `limit` y `offset`.
No se presentan probabilidades cuando el backend solo entrega segmentos descriptivos,
afinidad o heurísticas.

## Desarrollo local

Desde `frontend/`:

```powershell
npm ci
npm run dev
```

Inicia FastAPI en `http://127.0.0.1:8000`. Vite reenvía `/etl/*` y `/ml/*` a FastAPI. Para
ver la integración en contexto, abre `/dashboard` y selecciona “Machine Learning”.

## Build y despliegue

`npm run build` ejecuta TypeScript (`tsc --noEmit`) y Vite. FastAPI sirve los archivos
compilados desde `/static/react`; Docker vuelve a generarlos durante la build de la imagen.
En el entorno objetivo, migra y carga resultados descriptivos solo tras validar una base de
pruebas; el procedimiento operativo está documentado en `08_integracion_gold.md`.

## Validación visual y pruebas

El proyecto no tiene runner de pruebas de componentes/E2E configurado. No se incorporó uno;
se ejecuta el typecheck/build existente y se validan contratos del backend con pruebas
unitarias. Las capturas se deben tomar de la aplicación ya construida y conectada al backend
con resultados persistidos en el entorno de prueba.
