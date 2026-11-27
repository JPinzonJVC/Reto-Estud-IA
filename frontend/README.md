# Frontend React

El bundle Vite + React + TypeScript monta el monitor Prefect y el módulo Machine Learning
como dos raíces React dentro del dashboard integrado en FastAPI. Las demás vistas del tablero
siguen usando sus componentes existentes.

## Desarrollo

Desde `frontend/`:

```powershell
npm ci
npm run dev
```

En otra terminal, inicia FastAPI en `http://127.0.0.1:8000`. Vite abre el monitor en
`http://localhost:5173` y reenvía las llamadas `/etl/*` y `/ml/*` a FastAPI. En la aplicación
integrada, abre `/dashboard` y selecciona “Machine Learning”.

## Producción

`npm run build` ejecuta typecheck y Vite; genera archivos en `app/static/react`, servidos
por FastAPI en `/static/react`. Docker hace este build al construir la imagen.

## Organización

- `src/api`: clientes HTTP por área y manejo de errores.
- `src/components`: componentes reutilizables del monitor.
- `src/pages`: vistas Prefect y Machine Learning.
- `src/ml.css`: estilos acotados de la vista ML y responsive.
- `src/types.ts`: contratos TypeScript de ETL y ML.
- `docs/ml/09_frontend.md`: interacción visual, endpoints y estados.
