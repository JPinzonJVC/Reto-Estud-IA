"""Servicio de negocio para consulta de afiliados y participación en Gold."""

from typing import Any

from sqlalchemy.orm import Session

from app.modules.affiliates.repository import AffiliatesRepository


class AffiliatesService:
    """Orquesta la consulta de métricas de empresas afiliadas desde la capa Gold."""

    def __init__(self, repository: AffiliatesRepository | None = None) -> None:
        """Inicializa el servicio de afiliados.

        Args:
            repository: Repositorio opcional de afiliados.

        """
        self.repository = repository or AffiliatesRepository()

    def get_summary(self, session: Session | None = None) -> dict[str, Any]:
        """Obtiene el resumen de afiliados calculado directamente desde la capa Gold.

        Args:
            session: Sesión opcional de SQLAlchemy.

        Returns:
            Diccionario con métricas reales de afiliados activos y participación.

        """
        repo = AffiliatesRepository(session) if session else self.repository
        return repo.obtener_resumen_afiliados()

    def get_participation_list(
        self, session: Session | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Obtiene el listado de participación por empresa desde Gold.

        Args:
            session: Sesión opcional de SQLAlchemy.
            limit: Límite de registros a consultar.

        Returns:
            Lista de empresas con sus indicadores de participación.

        """
        repo = AffiliatesRepository(session) if session else self.repository
        return repo.listar_participacion_empresas(limit=limit)
