"""Resultados versionados y auditables de Machine Learning en Gold."""

from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)

from app.database import Base


class GoldMlResultado(Base):  # type: ignore[misc,valid-type]
    """Resultado descriptivo por empresa, sin mezclar ejecuciones experimentales."""

    __tablename__ = "gold_ml_resultados_empresa"
    __table_args__ = (
        UniqueConstraint(
            "caso_uso",
            "id_empresa",
            "version_modelo",
            "fecha_corte",
            name="uq_gold_ml_resultado_caso_empresa_version_corte",
        ),
        Index("ix_gold_ml_resultados_empresa", "id_empresa"),
        Index("ix_gold_ml_resultados_caso_estado", "caso_uso", "estado_evaluacion"),
    )

    id: Any = Column(Integer, primary_key=True, autoincrement=True)
    caso_uso: Any = Column(String(40), nullable=False)
    id_empresa: Any = Column(String(64), nullable=False)
    id_ejecucion: Any = Column(String(36), nullable=False)
    version_modelo: Any = Column(String(64), nullable=False)
    fecha_corte: Any = Column(String(32), nullable=False)
    estado_evaluacion: Any = Column(String(32), nullable=False)
    metodo: Any = Column(String(128), nullable=False)
    score: Any = Column(Float, nullable=True)
    segmento: Any = Column(String(128), nullable=True)
    soporte: Any = Column(Integer, nullable=True)
    justificacion: Any = Column(JSON, nullable=False, default=dict)
    metricas: Any = Column(JSON, nullable=False, default=dict)
    hash_dataset: Any = Column(String(64), nullable=True)
    creado_en: Any = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    actualizado_en: Any = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
