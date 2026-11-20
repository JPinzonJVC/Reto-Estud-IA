"""Modelo ORM para auditoría de hashes Bronze (audit_hashes_fuentes_bronze)."""

from sqlalchemy import Boolean, Column, Integer, String

from app.database import Base


class AuditHashFuenteBronze(Base):  # type: ignore[misc,valid-type]
    """Registro de auditoría de hashes SHA-256 de archivos en la capa Bronze."""

    __tablename__ = "audit_hashes_fuentes_bronze"

    tabla_fuente = Column(String(128), primary_key=True)
    """Nombre lógico de la tabla fuente verificada en la capa Bronze."""

    id_ejecucion = Column(String(128), nullable=True)
    """Identificador único de la ejecución ETL que verificó el archivo."""

    fecha_hora_ingesta = Column(String(64), nullable=True)
    """Fecha y hora ISO en que se realizó la validación e ingesta en Bronze."""

    archivo_nombre = Column(String(256), nullable=True)
    """Nombre del archivo CSV fuente procesado."""

    bytes_origen = Column(Integer, nullable=True)
    """Tamaño en bytes del archivo fuente."""

    filas_leidas = Column(Integer, nullable=True)
    """Cantidad total de filas leídas desde el archivo Bronze."""

    columnas_leidas = Column(Integer, nullable=True)
    """Cantidad total de columnas del archivo Bronze."""

    sha256_origen = Column(String(64), nullable=True)
    """Hash criptográfico SHA-256 calculado sobre el archivo de entrada."""

    sha256_bronze = Column(String(64), nullable=True)
    """Hash criptográfico SHA-256 calculado sobre la copia en Bronze."""

    integridad_verificada = Column(Boolean, nullable=True)
    """Indica si los hashes de origen y Bronze coinciden exactamente."""

    accion_bronze = Column(String(128), nullable=True)
    """Acción ejecutada (COPIADO_INICIAL_VERIFICADO o CONSERVADO_SIN_SOBRESCRIBIR)."""
