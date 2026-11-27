"""Extracción empresa-evento de asistencias para construir afinidad histórica."""

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.eda.models.gold_hechos_y_marts import GoldFactAsistenciasBi


def load_company_event_attendance(db: Session) -> pd.DataFrame:
    """Carga empresa, evento y línea sin incluir personas ni datos de contacto."""
    statement = select(
        GoldFactAsistenciasBi.id_empresa,
        GoldFactAsistenciasBi.id_evento,
        GoldFactAsistenciasBi.linea_oferta_2027,
    ).where(GoldFactAsistenciasBi.id_empresa.is_not(None))
    rows = db.execute(statement).mappings().all()
    columns = [column.key for column in statement.selected_columns]
    return pd.DataFrame.from_records([dict(row) for row in rows], columns=columns)
