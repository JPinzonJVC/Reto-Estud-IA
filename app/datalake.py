"""Cliente y utilidades para la conexión y gestión del Data Lake en MinIO."""

import os
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config


class DataLakeClient:
    """Cliente para operaciones con el Data Lake S3 compatible (MinIO)."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Inicializa la conexión con el servidor MinIO.

        Args:
            endpoint_url: URL del endpoint de MinIO (ej. http://localhost:9000).
            access_key: Usuario o clave de acceso de MinIO.
            secret_key: Clave secreta o contraseña de MinIO.

        """
        self.endpoint_url = endpoint_url or os.getenv(
            "MINIO_ENDPOINT", "http://localhost:9000"
        )
        self.access_key = access_key or os.getenv(
            "MINIO_ROOT_USER", "minioadmin"
        )
        self.secret_key = secret_key or os.getenv(
            "MINIO_ROOT_PASSWORD", "minioadmin123"
        )

        self._s3_client: Any = None

    @property
    def client(self) -> Any:
        """Obtiene o instancia el cliente S3 de boto3 configurado para MinIO.

        Returns:
            Cliente boto3 inicializado con firma s3v4.

        """
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(signature_version="s3v4"),
                region_name="us-east-1",
            )
        return self._s3_client

    def upload_file(
        self,
        local_path: str | Path,
        bucket: str,
        s3_key: str,
    ) -> bool:
        """Sube un archivo local hacia una ruta y bucket del Data Lake.

        Args:
            local_path: Ruta del archivo en el sistema de archivos local.
            bucket: Nombre del bucket de destino.
            s3_key: Clave o ruta de destino dentro del bucket.

        Returns:
            True si el archivo se subió correctamente.

        Raises:
            FileNotFoundError: Si el archivo local no existe.

        """
        path_obj = Path(local_path)
        if not path_obj.exists():
            raise FileNotFoundError(
                f"No existe el archivo local a subir: {local_path}"
            )

        self.client.upload_file(str(path_obj), bucket, s3_key)
        return True

    def download_file(
        self,
        bucket: str,
        s3_key: str,
        local_path: str | Path,
    ) -> Path:
        """Descarga un objeto del Data Lake hacia el sistema local.

        Args:
            bucket: Nombre del bucket de origen.
            s3_key: Clave del objeto en MinIO.
            local_path: Ruta de destino en disco local.

        Returns:
            Ruta Path del archivo descargado.

        """
        dest_path = Path(local_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(bucket, s3_key, str(dest_path))
        return dest_path

    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
    ) -> list[str]:
        """Lista los nombres de los objetos almacenados bajo un prefijo.

        Args:
            bucket: Nombre del bucket a consultar.
            prefix: Prefijo o subcarpeta de búsqueda opcional.

        Returns:
            Lista con las claves (keys) de los objetos encontrados.

        """
        response = self.client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        contents = response.get("Contents", [])
        return [item["Key"] for item in contents if "Key" in item]

    def ping(self) -> bool:
        """Verifica la conectividad con el servicio MinIO.

        Returns:
            True si la conexión y autenticación responden exitosamente.

        """
        try:
            self.client.list_buckets()
            return True
        except Exception:
            return False
