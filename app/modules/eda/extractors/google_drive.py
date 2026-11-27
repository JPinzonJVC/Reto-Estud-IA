"""Extractor desacoplado de archivos Excel/CSV desde Google Drive."""

import hashlib
import io
import logging
from collections import deque
from pathlib import Path, PurePosixPath
from typing import Any

import pandas as pd

from app.env_vars import GoogleDriveEnvs
from app.modules.eda.extractors.base import ExtractionResult

logger = logging.getLogger(__name__)

GoogleDriveConfig = GoogleDriveEnvs
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
SUPPORTED_EXTENSIONS = (".xlsx", ".xls", ".csv")


def _build_drive_service(credentials_file: Path, scopes: list[str]) -> Any:
    """Construye el cliente oficial de Google Drive v3 con Service Account.

    Args:
        credentials_file: Ruta al archivo JSON de la cuenta de servicio.
        scopes: Lista de scopes OAuth2 configurados para Google Drive.

    Returns:
        Recurso cliente de Google Drive API v3.

    Raises:
        FileNotFoundError: Si el archivo de credenciales no existe.
        ImportError: Si faltan las librerías de Google API en el entorno.

    """
    # pylint: disable=import-outside-toplevel
    from google.oauth2 import service_account  # type: ignore[import-untyped]
    from googleapiclient.discovery import build  # type: ignore[import-untyped]

    creds = service_account.Credentials.from_service_account_file(
        str(credentials_file),
        scopes=scopes,
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _compute_folder_fingerprint(files: list[dict[str, Any]]) -> str:
    """Genera un hash determinístico del estado de archivos en el árbol de carpetas.

    Args:
        files: Lista de metadatos de archivos retornada por Google Drive API.

    Returns:
        Digest SHA-256 hexadecimal representativo del estado de la carpeta y subcarpetas.

    Raises:
        None.

    """
    entries = sorted(
        f"{f.get('relative_path', f.get('name', ''))}:"
        f"{f.get('id', '')}:{f.get('md5Checksum', '')}:{f.get('modifiedTime', '')}"
        for f in files
    )
    payload = "|".join(entries).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class GoogleDriveExtractor:
    """Descarga incremental y recursivamente archivos Excel y CSV desde Drive."""

    def __init__(self, config: GoogleDriveEnvs | None = None) -> None:
        """Inicializa el extractor con la configuración de Google Drive.

        Args:
            config: Configuración opcional; si es None, se carga desde entorno.

        Returns:
            None.

        Raises:
            None.

        """
        self.config = config or GoogleDriveEnvs()

    def _list_folder_files(self, service: Any) -> list[dict[str, Any]]:
        """Lista recursivamente archivos Excel y CSV dentro de la carpeta y subcarpetas.

        Args:
            service: Cliente activo de Google Drive API v3.

        Returns:
            Lista de metadatos enriquecidos con 'relative_path' para .xlsx, .xls y .csv.

        Raises:
            Exception: Si ocurre un error en la llamada a la API de Google Drive.

        """
        fields = "nextPageToken, files(id, name, mimeType, md5Checksum, modifiedTime)"
        discovered_files: list[dict[str, Any]] = []
        queue: deque[tuple[str, PurePosixPath]] = deque(
            [(self.config.folder_id, PurePosixPath("."))]
        )
        visited_folders: set[str] = set()

        while queue:
            current_folder_id, current_rel_dir = queue.popleft()
            if current_folder_id in visited_folders:
                continue
            visited_folders.add(current_folder_id)

            query = f"'{current_folder_id}' in parents and trashed = false"
            page_token: str | None = None

            while True:
                response = (
                    service.files()
                    .list(
                        q=query,
                        fields=fields,
                        pageSize=100,
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                for item in response.get("files", []):
                    name = str(item.get("name", ""))
                    mime_type = str(item.get("mimeType", ""))
                    rel_path = (
                        PurePosixPath(name)
                        if current_rel_dir == PurePosixPath(".")
                        else current_rel_dir / name
                    )

                    if mime_type == FOLDER_MIME_TYPE:
                        folder_child_id = str(item.get("id", ""))
                        if folder_child_id and folder_child_id not in visited_folders:
                            queue.append((folder_child_id, rel_path))
                    elif name.lower().endswith(SUPPORTED_EXTENSIONS):
                        enriched = dict(item)
                        enriched["relative_path"] = rel_path.as_posix()
                        discovered_files.append(enriched)

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        return discovered_files

    def _download_file(self, service: Any, file_id: str) -> bytes:
        """Descarga el contenido binario de un archivo desde Google Drive.

        Args:
            service: Cliente activo de Google Drive API v3.
            file_id: Identificador único del archivo en Google Drive.

        Returns:
            Contenido binario completo del archivo descargado.

        Raises:
            Exception: Si falla la descarga por fragmentos desde Google Drive.

        """
        # pylint: disable=import-outside-toplevel
        from googleapiclient.http import (
            MediaIoBaseDownload,  # type: ignore[import-untyped]
        )

        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()

    def extract(  # pylint: disable=too-many-locals
        self,
        *,
        last_cursor: str | None = None,
        force: bool = False,
        drive_service: Any | None = None,
    ) -> ExtractionResult:
        """Ejecuta la verificación y descarga incremental desde Google Drive.

        Args:
            last_cursor: Huella SHA-256 de la última sincronización exitosa.
            force: Si es True, descarga los archivos aunque no haya cambios detectados.
            drive_service: Cliente mock o inyectado opcional para pruebas unitarias.

        Returns:
            Resultado estandarizado con archivos escritos, filas y nuevo cursor.

        Raises:
            ValueError: Si GDRIVE_ENABLED=true pero GDRIVE_FOLDER_ID está vacío.
            FileNotFoundError: Si el archivo de credenciales Service Account no existe.

        """
        if not self.config.enabled:
            return ExtractionResult(
                source_name=self.config.source_name,
                enabled=False,
                has_changes=False,
                skipped_reason="GDRIVE_ENABLED=false",
            )

        if not self.config.folder_id:
            raise ValueError(
                "GDRIVE_FOLDER_ID es obligatorio cuando GDRIVE_ENABLED=true."
            )

        service = drive_service
        if service is None:
            if (
                self.config.credentials_file is None
                or not self.config.credentials_file.exists()
            ):
                raise FileNotFoundError(
                    "Archivo de credenciales Service Account no encontrado: "
                    f"{self.config.credentials_file}"
                )
            service = _build_drive_service(
                self.config.credentials_file,
                self.config.drive_scopes,
            )

        files = self._list_folder_files(service)
        fingerprint = _compute_folder_fingerprint(files)

        if not force and last_cursor and fingerprint == last_cursor:
            logger.info(
                "Google Drive sin cambios detectados (cursor=%s).", fingerprint[:12]
            )
            return ExtractionResult(
                source_name=self.config.source_name,
                enabled=True,
                has_changes=False,
                new_cursor=fingerprint,
                skipped_reason="Sin cambios en carpeta de Google Drive",
            )

        self.config.download_dir.mkdir(parents=True, exist_ok=True)
        written_files: list[Path] = []
        total_rows = 0

        for item in files:
            name = str(item["name"])
            rel_path = Path(str(item.get("relative_path", name)))
            raw_bytes = self._download_file(service, str(item["id"]))

            target_path = self.config.download_dir / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(raw_bytes)
            written_files.append(target_path)

            lower_name = name.lower()
            if lower_name.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(raw_bytes), header=None, dtype=str)
                total_rows += int(len(df.dropna(how="all")))
            elif (
                lower_name.endswith((".xlsx", ".xls"))
                and self.config.export_excel_sheets_to_csv
            ):
                sheets = pd.read_excel(
                    io.BytesIO(raw_bytes),
                    sheet_name=None,
                    header=None,
                    dtype=str,
                )
                stem = target_path.stem
                for sheet_name, sheet_df in sheets.items():
                    non_empty_df = sheet_df.dropna(how="all")
                    if non_empty_df.empty:
                        continue
                    safe_sheet = "".join(
                        ch if ch.isalnum() or ch in {"_", "-"} else "_"
                        for ch in str(sheet_name)
                    ).strip("_")
                    csv_path = target_path.parent / f"{stem}__{safe_sheet}.csv"
                    non_empty_df.to_csv(
                        csv_path,
                        index=False,
                        header=False,
                        encoding="utf-8",
                    )
                    written_files.append(csv_path)
                    total_rows += int(len(non_empty_df))

        return ExtractionResult(
            source_name=self.config.source_name,
            enabled=True,
            has_changes=bool(written_files),
            files_written=written_files,
            records_extracted=total_rows,
            new_cursor=fingerprint,
        )
