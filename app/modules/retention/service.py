"""Capa de servicios de negocio para el módulo de retención."""

from typing import Any

from sqlalchemy.orm import Session

from app.modules.machine_learning.prediction import predict_cluster
from app.modules.retention.repository import RetentionRepository
from app.modules.retention.risk_engine import assess_customer_profile


class RetentionService:
    """Gestiona la lógica de evaluación y estrategias de retención."""

    def __init__(self, repository: RetentionRepository | None = None) -> None:
        """Inicializa el servicio de retención con su repositorio Gold.

        Args:
            repository: Repositorio opcional de retención.

        """
        self.repository = repository or RetentionRepository()

    def analyze_customer(
        self,
        customer_id: str,
        features: list[float],
    ) -> dict[str, Any]:
        """Procesa y evalúa el riesgo de fuga para un cliente individual.

        Args:
            customer_id: Identificador del cliente.
            features: Vector numérico de métricas de comportamiento.

        Returns:
            Diagnóstico de retención con riesgo estimado y acción sugerida.

        """
        cluster_id = predict_cluster(features)
        return assess_customer_profile(
            customer_id=customer_id,
            features=features,
            cluster_id=cluster_id,
        )

    def get_retention_overview(self, session: Session | None = None) -> dict[str, Any]:
        """Genera métricas consolidadas de retención calculadas directamente desde Gold.

        Args:
            session: Sesión opcional de SQLAlchemy.

        Returns:
            Resumen estadístico real de empresas, semáforo heurístico y vencimientos.

        """
        repo = RetentionRepository(session) if session else self.repository
        return repo.obtener_resumen_retencion()

    def get_companies_by_risk(
        self,
        session: Session | None = None,
        semaforo: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Lista las empresas evaluadas en agg_retencion_empresa por nivel de riesgo.

        Args:
            session: Sesión opcional de SQLAlchemy.
            semaforo: Filtro opcional por categoría del semáforo heurístico.
            limit: Cantidad máxima de empresas a retornar.

        Returns:
            Lista de empresas con sus indicadores de vigencia y riesgo.

        """
        repo = RetentionRepository(session) if session else self.repository
        return repo.listar_empresas_retencion(semaforo=semaforo, limit=limit)
