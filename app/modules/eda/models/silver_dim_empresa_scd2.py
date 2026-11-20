"""Modelo SQLAlchemy ORM para el historial SCD Tipo 2 (silver_dim_empresas_scd2)."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text

from app.database import Base


class SilverDimEmpresaScd2(Base):  # type: ignore[misc,valid-type]
    """Dimensión histórica SCD Tipo 2 de membresías de empresas en Silver."""

    __tablename__ = "silver_dim_empresas_scd2"

    sk_empresa_scd2 = Column(String(64), primary_key=True)
    """Clave subrogada única de la versión histórica SCD2 (SCD2-EMP-xxxx)."""

    id_empresa = Column(
        String(64), ForeignKey("silver_dim_empresas.id_empresa"), nullable=False
    )
    """Clave foránea hacia silver_dim_empresas con el identificador de empresa."""

    id_registro_crm = Column(String(128), nullable=True)
    """Identificador del registro específico en la exportación de Zoho CRM."""

    kam_id = Column(String(64), ForeignKey("silver_dim_kams.kam_id"), nullable=False)
    """Clave foránea hacia silver_dim_kams con la ejecutiva asignada."""

    es_empresa_activa = Column(Boolean, nullable=False, default=False)
    """Indica si la empresa estaba activa en esta versión del registro."""

    es_membresia_activa = Column(Boolean, nullable=False, default=False)
    """Indica si la membresía estaba activa en esta versión histórica."""

    estado_membresia_detalle = Column(String(128), nullable=True)
    """Estado detallado de la membresía en la versión correspondiente."""

    tipo_membresia_original = Column(String(128), nullable=True)
    """Tipo de membresía original asociado a la versión."""

    categoria_membresia_original = Column(String(128), nullable=True)
    """Categoría de membresía original asociada a la versión."""

    fecha_inicio_vigencia = Column(String(32), nullable=True)
    """Fecha de inicio de vigencia de la versión (tomada de fecha_afiliacion)."""

    fecha_fin_vigencia = Column(String(32), nullable=True)
    """Fecha de fin de vigencia de la versión (tomada de fecha_expiracion)."""

    fecha_miembro_desde_crm = Column(String(32), nullable=True)
    """Fecha de antigüedad miembro desde reportada en el CRM."""

    es_registro_actual = Column(Boolean, nullable=False, default=True)
    """Indica si esta fila representa la versión actual vigente de la empresa."""

    fuente_version = Column(String(128), nullable=True)
    """Clasificación del origen de la versión (única, histórica o consolidada)."""

    version_registro = Column(Integer, nullable=False, default=1)
    """Número secuencial de versión (1..N) dentro de cada id_empresa."""

    total_versiones_empresa = Column(Integer, nullable=False, default=1)
    """Cantidad total de versiones registradas para la empresa."""

    tiene_fechas_inconsistentes = Column(Boolean, nullable=False, default=False)
    """Indica si fecha_inicio_vigencia es mayor que fecha_fin_vigencia en origen."""

    tiene_intervalo_superpuesto = Column(Boolean, nullable=False, default=False)
    """Indica si la empresa presenta solapamiento temporal entre versiones."""

    clasificacion_historia_scd2 = Column(String(128), nullable=True)
    """Diagnóstico de calidad sobre la reconstrucción temporal del intervalo."""

    descripcion_version_scd2 = Column(Text, nullable=True)
    """Descripción legible del estado y posición de la versión histórica."""
