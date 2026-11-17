"""Pruebas unitarias para el módulo de base de datos PostgreSQL."""

import os
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine

from app.database import (
    get_database_url,
    get_db,
    ping_database,
)


class TestDatabase(unittest.TestCase):
    """Casos de prueba para configuración y utilidades de base de datos."""

    def test_get_database_url_default(self) -> None:
        """Verifica la generación de la URL por defecto con variables de entorno."""
        with patch.dict(os.environ, {}, clear=True):
            url = get_database_url()
            self.assertEqual(
                url,
                "postgresql://postgres:postgres123@localhost:5432/estudia_db",
            )

    def test_get_database_url_from_custom_env(self) -> None:
        """Verifica que la variable DATABASE_URL tenga precedencia si existe."""
        custom_url = "postgresql://user:pass@remotehost:5432/custom_db"
        with patch.dict(os.environ, {"DATABASE_URL": custom_url}):
            url = get_database_url()
            self.assertEqual(url, custom_url)

    def test_ping_database_success(self) -> None:
        """Verifica ping exitoso utilizando un motor SQLite en memoria."""
        in_memory_engine = create_engine("sqlite:///:memory:")
        result = ping_database(in_memory_engine)
        self.assertTrue(result)

    def test_ping_database_failure(self) -> None:
        """Verifica que ping_database retorne False ante fallos de conexión."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = RuntimeError("Fallo de conexión")
        result = ping_database(mock_engine)
        self.assertFalse(result)

    def test_get_db_session_lifecycle(self) -> None:
        """Verifica el ciclo de vida del generador de sesiones get_db."""
        mock_session = MagicMock()
        with patch(
            "app.database.get_session_factory",
            return_value=MagicMock(return_value=mock_session),
        ):
            db_gen = get_db()
            session = next(db_gen)
            self.assertEqual(session, mock_session)
            with self.assertRaises(StopIteration):
                next(db_gen)
            mock_session.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
