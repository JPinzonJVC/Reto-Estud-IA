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


class ResultadoMlResponse(BaseModel):
    """Resultado descriptivo/heurístico de una empresa en Gold ML."""

    id_empresa: str
    id_ejecucion: str
    caso_uso: str
    version: str
    fecha_corte: str
    estado: str
    metodo: str
    score: float | None = None
    segmento_o_linea: str | None = None
    soporte: int | None = None
    justificacion: dict[str, Any]
    metricas: dict[str, Any]


class PaginaResultadosMlResponse(BaseModel):
    """Página filtrada del corte vigente para un caso ML."""

    caso_uso: str
    fecha_corte: str | None
    version: str | None
    id_ejecucion: str | None
    total: int
    limit: int
    offset: int
    items: list[ResultadoMlResponse]


class ResumenCasoMlResponse(BaseModel):
    """Cobertura del último corte y estado real de un caso ML."""

    caso_uso: str
    fecha_corte: str | None
    version: str | None
    estado: str
    empresas_procesadas: int
    resultados_disponibles: int
    tipo_resultado: str


class ResumenMlResponse(BaseModel):
    """Resumen del corte ML vigente y disponibilidad de artefactos aprobados."""

    fecha_corte: str | None
    resultados_totales: int
    modelos_aprobados_disponibles: int
    casos_uso: list[ResumenCasoMlResponse]
