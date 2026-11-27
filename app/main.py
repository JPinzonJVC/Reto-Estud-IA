"""Punto de entrada principal de la aplicación FastAPI, DWH y analítica ACTHO 360."""

from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.modules.affiliates.router import affiliates_router
from app.modules.analytics.router import analytics_router
from app.modules.dashboard.router import dashboard_router
from app.modules.eda.router import eda_router
from app.modules.machine_learning.router import ml_router
from app.modules.retention.router import retention_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="ACTHO 360 - Data Warehouse, Analítica & ML",
    version="2.0.0",
    description="Plataforma ejecutiva sobre arquitectura Medallion (Silver 3NF + Gold).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(retention_router)
app.include_router(analytics_router)
app.include_router(affiliates_router)
app.include_router(dashboard_router)
app.include_router(eda_router)
app.include_router(ml_router)


@app.get("/health", status_code=200)
def health_check() -> dict[str, str]:
    """Verifica el estado operativo del servicio y sus dependencias.

    Returns:
        Diccionario confirmando el estado de salud y versión de la API.

    """
    return {"status": "ok", "app": "Reto EstudIA", "version": "2.0.0"}


@app.get("/dashboard", response_class=HTMLResponse)
def render_main_dashboard(request: Request) -> Any:
    """Renderiza el tablero ejecutivo principal en la ruta unificada /dashboard.

    Args:
        request: Solicitud HTTP requerida por Jinja2Templates.

    Returns:
        Respuesta HTML con el tablero Horizon UI conectado al DWH.

    """
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={"title": "ACTHO 360 - Dashboard Ejecutivo"},
    )


@app.get("/", response_class=HTMLResponse)
def render_dashboard(request: Request) -> Any:
    """Renderiza la vista raíz reutilizando la plantilla principal del tablero.

    Args:
        request: Objeto Request requerido por Jinja2Templates.

    Returns:
        Respuesta HTML con la plantilla renderizada del dashboard.

    """
    dashboard_template = BASE_DIR / "templates" / "dashboard" / "index.html"
    if dashboard_template.exists():
        return templates.TemplateResponse(
            request=request,
            name="dashboard/index.html",
            context={"title": "ACTHO 360 - Dashboard Ejecutivo"},
        )
    return HTMLResponse("<h1>ACTHO 360 - Plataforma de Analítica y ML</h1>")


@app.get("/dashboard/silver", include_in_schema=False)
@app.get("/dashboard/silvers", include_in_schema=False)
def redirect_legacy_silver_dashboard() -> RedirectResponse:
    """Redirige rutas heredadas /dashboard/silver hacia /dashboard."""
    return RedirectResponse(url="/dashboard", status_code=307)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
