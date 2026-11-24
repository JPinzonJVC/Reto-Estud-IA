"""Vista compuesta de alto nivel para el tablero ACTHO."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.dashboard.repository import DashboardSilverRepository

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _repository(session: Session) -> DashboardSilverRepository:
    """Crea el repositorio con la sesión proporcionada por la dependencia.

    Args:
        session: Sesión SQLAlchemy administrada por FastAPI.

    Returns:
        Repositorio de consultas Silver para componer el dashboard.

    """
    return DashboardSilverRepository(session)


@dashboard_router.get("/overview")
def get_overview(
    fecha_referencia: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Compone los indicadores ejecutivos disponibles desde la capa Silver.

    Args:
        fecha_referencia: Fecha base para calcular los próximos vencimientos.
        db: Sesión PostgreSQL inyectada mediante ``Depends(get_db)``.

    Returns:
        Indicadores ejecutivos de afiliación, participación y satisfacción.

    """
    return _repository(db).obtener_resumen(fecha_referencia)
