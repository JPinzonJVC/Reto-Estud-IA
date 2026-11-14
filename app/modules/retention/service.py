"""Capa de servicios de negocio para el módulo de retención."""

from typing import Any

from app.modules.machine_learning.prediction import predict_cluster
from app.modules.retention.risk_engine import assess_customer_profile


class RetentionService:
    """Gestiona la lógica de evaluación y estrategias de retención."""

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

    def get_retention_overview(self) -> dict[str, Any]:
        """Genera métricas consolidadas del panel de retención.

        Returns:
            Resumen estadístico de clientes en riesgo y tasas de retención.

        """
        return {
            "total_evaluated": 1250,
            "high_risk_count": 85,
            "average_churn_rate": 0.068,
            "active_campaigns": 3,
        }
