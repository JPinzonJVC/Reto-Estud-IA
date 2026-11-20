"""Servicio de negocio para consulta de indicadores analíticos en capa Gold."""

from typing import Any

from sqlalchemy.orm import Session

from app.modules.analytics.repository import AnalyticsRepository


class AnalyticsService:
    """Orquesta la consulta de métricas de participación y satisfacción en Gold."""

    def __init__(self, repository: AnalyticsRepository | None = None) -> None:
        """Inicializa el servicio de analítica.

        Args:
            repository: Repositorio opcional de analítica.

        """
        self.repository = repository or AnalyticsRepository()

    def get_metrics(self, session: Session | None = None) -> dict[str, Any]:
        """Obtiene métricas globales de analítica calculadas directamente desde Gold.

        Args:
            session: Sesión opcional de SQLAlchemy.

        Returns:
            Diccionario con métricas reales de participación y satisfacción Gold.

        """
        repo = AnalyticsRepository(session) if session else self.repository
        return repo.obtener_metricas_analitica()

    def get_satisfaction_breakdown(
        self, session: Session | None = None
    ) -> list[dict[str, Any]]:
        """Obtiene el desglose de satisfacción por modalidad y mes desde Gold.

        Args:
            session: Sesión opcional de SQLAlchemy.

        Returns:
            Lista de registros de satisfacción de encuestas.

        """
        repo = AnalyticsRepository(session) if session else self.repository
        return repo.listar_satisfaccion_encuestas()
