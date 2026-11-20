"""Paquete de modelos SQLAlchemy ORM para las capas Silver, Gold y Audit."""

from app.modules.eda.models.audit_calidad_datos import AuditCalidadDatos
from app.modules.eda.models.audit_carga import AuditCarga
from app.modules.eda.models.audit_ejecucion_etl import AuditEjecucionEtl
from app.modules.eda.models.audit_hash_fuente_bronze import AuditHashFuenteBronze
from app.modules.eda.models.audit_reconciliacion_origen_destino import (
    AuditReconciliacionOrigenDestino,
)
from app.modules.eda.models.audit_registro_duplicado import AuditRegistroDuplicado
from app.modules.eda.models.audit_registro_rechazado import AuditRegistroRechazado
from app.modules.eda.models.gold_agg_participacion_empresa import (
    GoldAggParticipacionEmpresa,
)
from app.modules.eda.models.gold_agg_retencion_empresa import GoldAggRetencionEmpresa
from app.modules.eda.models.gold_agg_satisfaccion_encuestas import (
    GoldAggSatisfaccionEncuestas,
)
from app.modules.eda.models.silver_dim_empresa import SilverDimEmpresa
from app.modules.eda.models.silver_dim_empresa_scd2 import SilverDimEmpresaScd2
from app.modules.eda.models.silver_dim_evento import SilverDimEvento
from app.modules.eda.models.silver_dim_kam import SilverDimKam
from app.modules.eda.models.silver_dim_persona import SilverDimPersona
from app.modules.eda.models.silver_fact_asistencia import SilverFactAsistencia
from app.modules.eda.models.silver_fact_encuesta_satisfaccion import (
    SilverFactEncuestaSatisfaccion,
)
from app.modules.eda.models.silver_fact_movimiento_crm import SilverFactMovimientoCrm

__all__ = [
    "AuditCalidadDatos",
    "AuditCarga",
    "AuditEjecucionEtl",
    "AuditHashFuenteBronze",
    "AuditReconciliacionOrigenDestino",
    "AuditRegistroDuplicado",
    "AuditRegistroRechazado",
    "GoldAggParticipacionEmpresa",
    "GoldAggRetencionEmpresa",
    "GoldAggSatisfaccionEncuestas",
    "SilverDimEmpresa",
    "SilverDimEmpresaScd2",
    "SilverDimEvento",
    "SilverDimKam",
    "SilverDimPersona",
    "SilverFactAsistencia",
    "SilverFactEncuestaSatisfaccion",
    "SilverFactMovimientoCrm",
]
