"""Modelo SQLAlchemy ORM para movimientos CRM (silver_fact_movimientos_crm)."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from app.database import Base


class SilverFactMovimientoCrm(Base):  # type: ignore[misc,valid-type]
    """Tabla de hechos de operaciones y oportunidades comerciales en CRM."""

    __tablename__ = "silver_fact_movimientos_crm"

    id_movimiento = Column(String(64), primary_key=True)
    """Clave primaria subrogada del movimiento CRM (MOV-xxxx)."""

    id_empresa = Column(
        String(64),
        ForeignKey("silver_dim_empresas.id_empresa"),
        nullable=False,
        index=True,
    )
    """Clave foránea obligatoria hacia la empresa asociada al movimiento."""

    id_membresia = Column(
        String(64),
        ForeignKey("silver_membresias.id_membresia"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia la membresía (NULL en tratos no cerrados)."""

    kam_id = Column(
        String(64),
        ForeignKey("silver_dim_kams.kam_id"),
        nullable=False,
        index=True,
    )
    """Clave foránea hacia la ejecutiva KAM responsable del movimiento."""

    id_persona_contacto = Column(
        String(64),
        ForeignKey("silver_dim_personas.id_persona"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia el contacto principal del movimiento."""

    id_cat_membresia_movimiento = Column(
        Integer,
        ForeignKey("silver_dim_catalogo_membresia.id_cat_membresia"),
        nullable=True,
        index=True,
    )
    """Clave foránea opcional hacia la categoría negociada en el movimiento."""

    tipo_movimiento = Column(String(128), nullable=False)
    """Tipo de operación CRM (Nueva Afiliación, Renovación, Trato en Estado)."""

    estado_movimiento_crm = Column(String(128), nullable=True)
    """Fotografía histórica del estado operativo del movimiento."""

    es_cierre_facturado = Column(Boolean, nullable=False, default=False)
    """Indica si el movimiento corresponde a un cierre efectivo facturado."""

    fecha_cierre_o_factura = Column(String(32), nullable=True)
    """Fecha ISO YYYY-MM-DD de cierre o facturación cuando aplica."""

    fecha_expiracion_afiliacion = Column(String(32), nullable=True)
    """Fecha ISO YYYY-MM-DD de expiración reportada en el movimiento."""
