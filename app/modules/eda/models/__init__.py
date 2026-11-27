"""Paquete de modelos SQLAlchemy ORM para el Data Warehouse Medallion ACTHO 360."""

from app.modules.eda.models.audit_calidad_datos import AuditCalidadDatos
from app.modules.eda.models.audit_carga import AuditCarga
from app.modules.eda.models.audit_ejecucion_etl import AuditEjecucionEtl
from app.modules.eda.models.audit_hash_fuente_bronze import AuditHashFuenteBronze
from app.modules.eda.models.audit_ingestion_watermark import AuditIngestionWatermark
from app.modules.eda.models.audit_reconciliacion_origen_destino import (
    AuditReconciliacionOrigenDestino,
)
from app.modules.eda.models.audit_registro_rechazado import AuditRegistroRechazado
from app.modules.eda.models.gold_dim_empresa_360 import GoldDimEmpresa360
from app.modules.eda.models.gold_dim_evento_kpis import GoldDimEventoKpis
from app.modules.eda.models.gold_hechos_y_marts import (
    GoldFactAsistenciasBi,
    GoldFactEncuestasBi,
    GoldFactEvolucionMembresiasMes,
    GoldMartSegmentosComunicaciones,
)
from app.modules.eda.models.silver_dim_empresa import SilverDimEmpresa
from app.modules.eda.models.silver_dim_evento import SilverDimEvento
from app.modules.eda.models.silver_dim_geografia import (
    SilverDimCiudad,
    SilverDimDepartamento,
    SilverDimPais,
)
from app.modules.eda.models.silver_dim_kam import SilverDimKam
from app.modules.eda.models.silver_dim_persona import (
    SilverBridgePersonaEmpresa,
    SilverDimPersona,
)
from app.modules.eda.models.silver_fact_asistencia import SilverFactAsistencia
from app.modules.eda.models.silver_fact_encuesta_satisfaccion import (
    SilverFactEncuestaSatisfaccion,
)
from app.modules.eda.models.silver_fact_movimiento_crm import SilverFactMovimientoCrm
from app.modules.eda.models.silver_membresia import (
    SilverDimCatalogoMembresia,
    SilverMembresia,
)

__all__ = [
    "AuditCalidadDatos",
    "AuditCarga",
    "AuditEjecucionEtl",
    "AuditHashFuenteBronze",
    "AuditIngestionWatermark",
    "AuditReconciliacionOrigenDestino",
    "AuditRegistroRechazado",
    "GoldDimEmpresa360",
    "GoldDimEventoKpis",
    "GoldFactAsistenciasBi",
    "GoldFactEncuestasBi",
    "GoldFactEvolucionMembresiasMes",
    "GoldMartSegmentosComunicaciones",
    "SilverBridgePersonaEmpresa",
    "SilverDimCatalogoMembresia",
    "SilverDimCiudad",
    "SilverDimDepartamento",
    "SilverDimEmpresa",
    "SilverDimEvento",
    "SilverDimKam",
    "SilverDimPais",
    "SilverDimPersona",
    "SilverFactAsistencia",
    "SilverFactEncuestaSatisfaccion",
    "SilverFactMovimientoCrm",
    "SilverMembresia",
]
