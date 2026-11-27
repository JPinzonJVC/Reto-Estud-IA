"""Resultados versionados y auditables de Machine Learning en Gold."""

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

    id = Column(Integer, primary_key=True, autoincrement=True)
    caso_uso = Column(String(40), nullable=False)
    id_empresa = Column(String(64), nullable=False)
    id_ejecucion = Column(String(36), nullable=False)
    version_modelo = Column(String(64), nullable=False)
    fecha_corte = Column(String(32), nullable=False)
    estado_evaluacion = Column(String(32), nullable=False)
    metodo = Column(String(128), nullable=False)
    score = Column(Float, nullable=True)
    segmento = Column(String(128), nullable=True)
    soporte = Column(Integer, nullable=True)
    justificacion = Column(JSON, nullable=False, default=dict)
    metricas = Column(JSON, nullable=False, default=dict)
    hash_dataset = Column(String(64), nullable=True)
    creado_en = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    actualizado_en = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
