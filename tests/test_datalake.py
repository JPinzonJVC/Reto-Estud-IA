"""Pruebas unitarias para el cliente de Data Lake (MinIO)."""

import unittest
from unittest.mock import MagicMock, patch

from app.datalake import DataLakeClient


class TestDataLakeClient(unittest.TestCase):
    """Casos de prueba para el cliente de MinIO y Data Lake."""

    def setUp(self) -> None:
        """Inicializa una instancia del cliente de pruebas."""
        self.dl_client = DataLakeClient(
            endpoint_url="http://mock-minio:9000",
            access_key="test_user",
            secret_key="test_pass",
        )

    def test_client_initialization(self) -> None:
        """Verifica que los atributos de configuración se asignen correctamente."""
        self.assertEqual(self.dl_client.endpoint_url, "http://mock-minio:9000")
        self.assertEqual(self.dl_client.access_key, "test_user")
        self.assertEqual(self.dl_client.secret_key, "test_pass")

    def test_upload_file_non_existent_raises(self) -> None:
        """Verifica que se lance FileNotFoundError al subir un archivo inexistente."""
        with self.assertRaises(FileNotFoundError):
            self.dl_client.upload_file(
                local_path="archivo_que_no_existe.parquet",
                bucket="datalake-raw",
                s3_key="raw/data.parquet",
            )

    @patch("boto3.client")
    def test_list_objects_mocked(self, mock_boto_client: MagicMock) -> None:
        """Verifica el listado de objetos usando cliente simulado."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "data/churn.parquet"}, {"Key": "data/clients.csv"}]
        }
        mock_boto_client.return_value = mock_s3

        client = DataLakeClient()
        objects = client.list_objects("datalake-raw", prefix="data/")
        self.assertEqual(len(objects), 2)
        self.assertIn("data/churn.parquet", objects)

    @patch("boto3.client")
    def test_ping_success(self, mock_boto_client: MagicMock) -> None:
        """Verifica que ping devuelva True cuando list_buckets responde exitosamente."""
        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {"Buckets": []}
        mock_boto_client.return_value = mock_s3

        client = DataLakeClient()
        self.assertTrue(client.ping())

    @patch("boto3.client")
    def test_ping_failure(self, mock_boto_client: MagicMock) -> None:
        """Verifica que ping capture excepciones y devuelva False si hay error."""
        mock_s3 = MagicMock()
        mock_s3.list_buckets.side_effect = RuntimeError("Conexión rechazada")
        mock_boto_client.return_value = mock_s3

        client = DataLakeClient()
        self.assertFalse(client.ping())


if __name__ == "__main__":
    unittest.main()
