"""Módulo de configuración y conexión a la base de datos PostgreSQL."""

import os
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()


def get_database_url() -> str:
    """Construye la URL de conexión a PostgreSQL a partir de variables de entorno.

    Returns:
        Cadena de conexión en formato compatible con SQLAlchemy y psycopg2.

    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres123")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "estudia_db")

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


DB_ENGINE: Engine | None = None


def get_engine() -> Engine:
    """Obtiene o inicializa el motor de base de datos SQLAlchemy (singleton).

    Returns:
        Instancia de Engine configurada para PostgreSQL.

    """
    global DB_ENGINE
    if DB_ENGINE is None:
        db_url = get_database_url()
        DB_ENGINE = create_engine(db_url, pool_pre_ping=True)
    assert DB_ENGINE is not None
    return DB_ENGINE


def get_session_factory() -> sessionmaker:
    """Genera la fábrica de sesiones para interactuar con la base de datos.

    Returns:
        Fábrica de sesiones sessionmaker vinculada al motor actual.

    """
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Generador de contexto para inyección de sesiones en endpoints de FastAPI.

    Yields:
        Sesión activa de SQLAlchemy para transacciones de base de datos.

    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def ping_database(engine: Engine | None = None) -> bool:
    """Verifica la conectividad activa con el servidor PostgreSQL.

    Args:
        engine: Instancia opcional de Engine a validar. Si es None, usa la global.

    Returns:
        True si la base de datos responde exitosamente al comando SELECT 1.

    """
    target_engine = engine or get_engine()
    try:
        with target_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
