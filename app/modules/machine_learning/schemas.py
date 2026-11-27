"""Esquemas Pydantic para los contratos reservados de Machine Learning ACTHO 360."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class SlotModeloML(BaseModel):
    """Describe el estado de preparación y artefacto de uno de los 4 modelos ML."""

    clave_modelo: str
    """Identificador único del caso de uso ML."""

    nombre_modelo: str
    """Título ejecutivo del modelo predictivo."""

    algoritmo_recomendado: str
    """Arquitectura sugerida para la rama de entrenamiento."""

    estado: str
    """Estado actual ('ESPACIO_RESERVADO' o 'MODELO_ACTIVO')."""

    columna_gold_objetivo: str
    """Columna reservada en gold_dim_empresa_360 que almacenará la inferencia."""

    registros_poblandose: int
    """Cantidad de registros que ya cuentan con puntaje ML no nulo."""

    total_universo_elegible: int
    """Total de empresas elegibles en el Data Warehouse."""

    ruta_endpoint: str
    """Ruta REST reservada para consultar resultados de este modelo."""

    model_config = ConfigDict(from_attributes=True)


class EstadoEspacioMLResponse(BaseModel):
    """Respuesta consolidada del estado de la suite ML reservada."""

    fuente_datos: str
    """Origen efectivo de consulta ('postgresql' o 'parquet')."""

    rama_entrenamiento_separada: bool
    """Indica que los artefactos .pkl se entrenarán en su rama dedicada."""

    insumos_listos: dict[str, int]
    """Conteo de entidades Gold/Silver listas para feature engineering."""

    modelos: list[SlotModeloML]
    """Detalle de los 4 espacios de modelos ML reservados."""

    notas_integracion: dict[str, Any]
    """Instrucciones de conexión automática para la rama ML."""

    model_config = ConfigDict(from_attributes=True)
