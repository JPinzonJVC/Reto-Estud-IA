"""Modelo SQLAlchemy ORM para la dimensión de empresas (silver_dim_empresas)."""

from sqlalchemy import Boolean, Column, Float, ForeignKey, String

from app.database import Base


class SilverDimEmpresa(Base):  # type: ignore[misc,valid-type]
    """Dimensión de empresas afiliadas y prospectos en la capa Silver."""

    __tablename__ = "silver_dim_empresas"

    id_empresa = Column(String(64), primary_key=True)
    """Identificador único de negocio de la empresa (EMP-xxxx)."""

    id_registro_crm = Column(String(128), nullable=True)
    """Identificador del registro vigente en Zoho CRM."""

    kam_id = Column(String(64), ForeignKey("silver_dim_kams.kam_id"), nullable=False)
    """Clave foránea hacia silver_dim_kams con la ejecutiva asignada."""

    kam_valor_original = Column(String(128), nullable=True)
    """Valor textual original de la ejecutiva antes de la homologación."""

    es_empresa_activa = Column(Boolean, nullable=False, default=False)
    """Indica si el estado general de la empresa en CRM es Activo."""

    es_membresia_activa = Column(Boolean, nullable=False, default=False)
    """Indica si la empresa posee una membresía activa vigente."""

    estado_membresia_detalle = Column(String(128), nullable=True)
    """Estado detallado de la membresía (Activo, Cancelado, Expirado, etc.)."""

    segmento_membresia = Column(String(128), nullable=True)
    """Segmento comercial de la membresía."""

    nivel_membresia = Column(String(128), nullable=True)
    """Nivel o categoría homologada de la membresía (Elite, Premium, Estándar)."""

    tipo_membresia_original = Column(String(128), nullable=True)
    """Tipo de membresía reportado originalmente en el CRM."""

    categoria_membresia_original = Column(String(128), nullable=True)
    """Categoría de membresía reportada originalmente en el CRM."""

    sector_economico = Column(String(256), nullable=True)
    """Sector económico principal de la empresa."""

    subsector_economico = Column(String(256), nullable=True)
    """Subsector económico detallado de la empresa."""

    tamano_empresa = Column(String(128), nullable=True)
    """Clasificación de tamaño empresarial."""

    rango_empleados = Column(String(128), nullable=True)
    """Rango de cantidad de empleados de la organización."""

    porcentaje_mujeres_num = Column(Float, nullable=True)
    """Porcentaje numérico de participación femenina en la empresa."""

    ciudad = Column(String(128), nullable=True)
    """Ciudad principal de ubicación de la empresa."""

    region_departamento = Column(String(128), nullable=True)
    """Departamento o región geográfica de la empresa."""

    pais = Column(String(128), nullable=True)
    """País de ubicación de la empresa."""

    fecha_afiliacion = Column(String(32), nullable=True)
    """Fecha de inicio de la afiliación actual en formato ISO YYYY-MM-DD."""

    fecha_expiracion = Column(String(32), nullable=True)
    """Fecha de expiración de la membresía actual en formato ISO YYYY-MM-DD."""

    fecha_miembro_desde = Column(String(32), nullable=True)
    """Fecha histórica desde la cual la empresa es miembro según el CRM."""

    fecha_ultima_actividad = Column(String(32), nullable=True)
    """Fecha de la última actividad registrada en el CRM (YYYY-MM-DD)."""

    fecha_hora_ultima_actividad = Column(String(64), nullable=True)
    """Marca temporal completa de la última actividad en el CRM."""

    fecha_cambio_registro = Column(String(32), nullable=True)
    """Fecha de la última modificación del registro en el CRM."""

    fecha_hora_cambio_registro = Column(String(64), nullable=True)
    """Marca temporal completa de la última modificación en el CRM."""

    es_independiente = Column(Boolean, nullable=True)
    """Indica si el afiliado corresponde a un profesional independiente."""

    es_registro_prueba = Column(Boolean, nullable=True)
    """Indica si el registro está marcado como cuenta de prueba."""

    bloqueado_crm = Column(Boolean, nullable=True)
    """Indica si el registro se encuentra bloqueado en el CRM."""

    vinculado_comunidades = Column(Boolean, nullable=True)
    """Indica si la empresa participa en comunidades especializadas ACTHO."""

    pilar_hr_estrategico = Column(Boolean, nullable=True)
    """Indica vinculación al pilar de HR Estratégico."""

    pilar_mas_que_salario = Column(Boolean, nullable=True)
    """Indica vinculación al pilar Más que Salario."""

    pilar_talento_que_elige = Column(Boolean, nullable=True)
    """Indica vinculación al pilar Talento que Elige."""

    pilar_gente_que_crece = Column(Boolean, nullable=True)
    """Indica vinculación al pilar Gente que Crece."""

    comunidad_mujeres_hr = Column(Boolean, nullable=True)
    """Indica participación en la comunidad de Mujeres en HR."""

    es_influenciador = Column(Boolean, nullable=True)
    """Indica si la cuenta está clasificada como influenciadora."""

    en_crm_afiliados = Column(Boolean, nullable=False, default=False)
    """Indica si la empresa proviene del maestro de afiliados del CRM."""
