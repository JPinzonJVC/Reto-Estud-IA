"""Modelo SQLAlchemy ORM para movimientos CRM (silver_fact_movimientos_crm)."""

from sqlalchemy import Boolean, Column, ForeignKey, String

from app.database import Base


class SilverFactMovimientoCrm(Base):  # type: ignore[misc,valid-type]
    """Tabla de hechos de movimientos y renovaciones CRM en la capa Silver."""

    __tablename__ = "silver_fact_movimientos_crm"

    id_movimiento = Column(String(64), primary_key=True)
    """Clave primaria subrogada del movimiento CRM (MOV-xxxx)."""

    tipo_movimiento = Column(String(128), nullable=True)
    """Tipo de operación CRM (Nueva Afiliación, Renovación, Trato en Estado)."""

    es_cierre_facturado = Column(Boolean, nullable=True)
    """Indica si el movimiento corresponde a un cierre efectivo facturado."""

    es_renovacion = Column(Boolean, nullable=True)
    """Indica si el movimiento corresponde a una renovación de membresía."""

    fecha_periodo_mes = Column(String(32), nullable=True)
    """Fecha base del periodo mensual reportado."""

    periodo_mes_iso = Column(String(32), nullable=True)
    """Periodo mensual del movimiento en formato ISO YYYY-MM."""

    fecha_cierre_o_factura = Column(String(32), nullable=True)
    """Fecha de cierre o facturación del movimiento en formato YYYY-MM-DD."""

    fecha_expiracion_afiliacion = Column(String(32), nullable=True)
    """Fecha de expiración asociada a la afiliación o renovación."""

    fecha_exportacion_reporte = Column(String(32), nullable=True)
    """Fecha de corte o exportación del reporte fuente de CRM."""

    kam_id = Column(String(64), ForeignKey("silver_dim_kams.kam_id"), nullable=False)
    """Clave foránea hacia silver_dim_kams con la ejecutiva responsable."""

    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), nullable=False
    )
    """Clave foránea hacia silver_dim_empresas con la empresa del movimiento."""

    nivel_membresia = Column(String(128), nullable=True)
    """Nivel o categoría de membresía involucrada en el movimiento."""

    id_persona_contacto = Column(String(64), nullable=True)
    """Identificador de la persona de contacto principal cuando figura en el reporte."""

    kam_valor_original = Column(String(128), nullable=True)
    """Valor original del campo KAM antes de la homologación."""

    estado_afiliacion_empresa = Column(String(128), nullable=True)
    """Estado de afiliación vigente de la empresa en el maestro Silver."""

    clasificacion_fecha_expiracion = Column(String(128), nullable=True)
    """Clasificación de completitud de la fecha de expiración en el movimiento."""
