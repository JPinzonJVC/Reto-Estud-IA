"""Extracción del dataset RFM-S desde Gold y atributos de comunidades Silver."""

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.eda.models.gold_dim_empresa_360 import GoldDimEmpresa360
from app.modules.eda.models.silver_dim_empresa import SilverDimEmpresa


def load_fidelity_dataset(db: Session) -> pd.DataFrame:
    """Carga atributos agregados de afiliados activos sin datos personales.

    La granularidad de salida es empresa. Encuestas anónimas no se enlazan y no
    se consulta información de contacto.
    """
    statement = (
        select(
            GoldDimEmpresa360.id_empresa,
            GoldDimEmpresa360.dias_sin_participacion,
            GoldDimEmpresa360.total_eventos_anio,
            GoldDimEmpresa360.total_asistencias_anio,
            GoldDimEmpresa360.personas_distintas_anio,
            GoldDimEmpresa360.total_ciclos_membresia,
            GoldDimEmpresa360.satisfaccion_promedio_1_5,
            GoldDimEmpresa360.nps_reciente_0_10,
            SilverDimEmpresa.vinculado_comunidades,
            SilverDimEmpresa.pilar_hr_estrategico,
            SilverDimEmpresa.pilar_mas_que_salario,
            SilverDimEmpresa.pilar_talento_que_elige,
            SilverDimEmpresa.pilar_gente_que_crece,
        )
        .join(
            SilverDimEmpresa,
            SilverDimEmpresa.id_empresa == GoldDimEmpresa360.id_empresa,
        )
        .where(GoldDimEmpresa360.tipo_relacion_actho == "AFILIADO_ACTIVO")
        .where(GoldDimEmpresa360.es_membresia_activa.is_(True))
        .order_by(GoldDimEmpresa360.id_empresa)
    )
    records = db.execute(statement).mappings().all()
    columns = [column.key for column in statement.selected_columns]
    return pd.DataFrame.from_records(
        [dict(record) for record in records], columns=columns
    )
