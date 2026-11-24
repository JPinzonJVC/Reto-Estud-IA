"""Repositorio ligero de watermarks de ingesta en PostgreSQL."""

from datetime import datetime, timezone

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.modules.eda.models.audit_ingestion_watermark import AuditIngestionWatermark


def _utc_now_iso() -> str:
    """Retorna el timestamp UTC actual en formato ISO-8601.

    Args:
        None.

    Returns:
        Cadena con fecha y hora UTC en formato '%Y-%m-%dT%H:%M:%SZ'.

    Raises:
        None.

    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_watermark(engine: Engine, source_name: str) -> AuditIngestionWatermark | None:
    """Consulta el watermark actual para una fuente externa.

    Args:
        engine: Motor SQLAlchemy conectado a PostgreSQL.
        source_name: Identificador único de la fuente.

    Returns:
        Instancia de AuditIngestionWatermark si existe, o None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: Si falla la consulta a la base de datos.

    """
    AuditIngestionWatermark.__table__.create(bind=engine, checkfirst=True)
    with Session(engine) as session:
        return session.get(AuditIngestionWatermark, source_name)


def upsert_watermark(
    engine: Engine,
    *,
    source_name: str,
    last_status: str,
    last_cursor: str | None = None,
    last_sync_at: str | None = None,
    records_extracted: int = 0,
    details: str | None = None,
) -> AuditIngestionWatermark:
    """Inserta o actualiza el watermark de sincronización para una fuente.

    Args:
        engine: Motor SQLAlchemy conectado a PostgreSQL.
        source_name: Identificador único de la fuente.
        last_status: Estado de la corrida ('SUCCESS', 'SKIPPED', 'FAILED').
        last_cursor: Cursor/checksum nuevo (conserva el anterior si es None).
        last_sync_at: Timestamp ISO-8601 de sincronización exitosa.
        records_extracted: Cantidad de registros o archivos extraídos.
        details: Información adicional o mensaje de error.

    Returns:
        Registro AuditIngestionWatermark persistido.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: Si falla el commit o creación de tabla.

    """
    AuditIngestionWatermark.__table__.create(bind=engine, checkfirst=True)
    now_iso = _utc_now_iso()
    with Session(engine) as session:
        record = session.get(AuditIngestionWatermark, source_name)
        if record is None:
            record = AuditIngestionWatermark(
                source_name=source_name,
                last_sync_at=last_sync_at,
                last_cursor=last_cursor,
                last_status=last_status,
                records_extracted=records_extracted,
                details=details,
                updated_at=now_iso,
            )
            session.add(record)
        else:
            if last_sync_at is not None:
                record.last_sync_at = last_sync_at
            if last_cursor is not None:
                record.last_cursor = last_cursor
            record.last_status = last_status
            record.records_extracted = records_extracted
            record.details = details
            record.updated_at = now_iso
        session.commit()
        session.refresh(record)
        return record
