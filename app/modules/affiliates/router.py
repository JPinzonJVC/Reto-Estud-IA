"""Enrutador para endpoints del módulo de afiliados."""

from typing import Any

from fastapi import APIRouter

affiliates_router = APIRouter(
    prefix="/affiliates",
    tags=["Afiliados"],
)


@affiliates_router.get("/summary", status_code=200)
def get_affiliates_summary() -> dict[str, Any]:
    """Retorna el resumen de desempeño de la red de afiliados.

    Returns:
        Diccionario con conteo de afiliados, comisiones y referidos.

    """
    return {
        "active_affiliates": 48,
        "monthly_referrals": 620,
        "commission_paid_usd": 12400.0,
    }
