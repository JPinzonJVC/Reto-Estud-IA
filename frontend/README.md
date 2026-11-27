# Frontend React

La vista de orquestación Prefect se migra primero a React + TypeScript. Las
demás vistas del dashboard siguen funcionando en el frontend existente y se
migrarán por módulos para mantener el producto disponible durante el cambio.

## Desarrollo

Desde esta carpeta:

```powershell
npm ci
npm run dev
```

En otra terminal, inicia FastAPI en `http://127.0.0.1:8000`. Vite abre el monitor
en `http://localhost:5173` y reenvía las llamadas `/etl/*` a FastAPI.

## Producción

`npm run build` genera los archivos estáticos en `app/static/react`, que FastAPI
sirve bajo `/static/react`. Los nombres de salida son estables para que la
plantilla Jinja pueda referenciarlos directamente.

## Organización

- `src/api`: comunicación HTTP y manejo común de errores.
- `src/components`: piezas visuales reutilizables.
- `src/pages`: composición de páginas y estado de pantalla.
- `src/types.ts`: contratos de datos del monitor ETL.
