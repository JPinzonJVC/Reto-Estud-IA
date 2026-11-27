"""Extractor incremental desacoplado para Zoho CRM vía OAuth2."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from app.env_vars import ZohoEnvs
from app.modules.eda.extractors.base import ExtractionResult

logger = logging.getLogger(__name__)

ZohoCRMConfig = ZohoEnvs


class ZohoCRMExtractor:
    """Extrae módulos de Zoho CRM de forma incremental usando If-Modified-Since."""

    def __init__(self, config: ZohoEnvs | None = None) -> None:
        """Inicializa el extractor con la configuración de Zoho CRM.

        Args:
            config: Configuración opcional; si es None, se carga desde entorno.

        Returns:
            None.

        Raises:
            None.

        """
        self.config = config or ZohoEnvs()

    def _refresh_access_token(self, client: httpx.Client) -> str:
        """Obtiene un access_token temporal usando el refresh_token OAuth2.

        Args:
            client: Cliente HTTPX reutilizable para peticiones a Zoho Accounts.

        Returns:
            Cadena con el access_token OAuth2 vigente.

        Raises:
            httpx.HTTPStatusError: Si el endpoint OAuth2 responde con error HTTP.
            RuntimeError: Si la respuesta JSON no incluye access_token.

        """
        response = client.post(
            f"{self.config.accounts_url}/oauth/v2/token",
            data={
                "refresh_token": self.config.refresh_token,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError(f"Respuesta OAuth2 de Zoho sin access_token: {payload}")
        return str(token)

    def _fetch_module_records(
        self,
        client: httpx.Client,
        *,
        access_token: str,
        module: str,
        modified_since: str | None,
    ) -> list[dict[str, Any]]:
        """Pagina registros de un módulo de Zoho CRM respetando If-Modified-Since.

        Args:
            client: Cliente HTTPX activo.
            access_token: Token OAuth2 vigente para autorizar las peticiones.
            module: Nombre del módulo de Zoho CRM (ej. 'Accounts', 'Contacts').
            modified_since: Timestamp ISO-8601 UTC para lectura incremental o None.

        Returns:
            Lista de diccionarios con los registros recuperados del módulo.

        Raises:
            httpx.HTTPStatusError: Si la API de Zoho CRM retorna un código de error HTTP.

        """
        headers: dict[str, str] = {"Authorization": f"Zoho-oauthtoken {access_token}"}
        if modified_since:
            headers["If-Modified-Since"] = modified_since

        records: list[dict[str, Any]] = []
        page = 1

        while True:
            response = client.get(
                f"{self.config.api_base_url}/crm/v6/{module}",
                headers=headers,
                params={"page": page, "per_page": 200},
            )
            if response.status_code in {204, 304}:
                break
            response.raise_for_status()
            payload = response.json()
            batch = payload.get("data") or []
            if not batch:
                break
            records.extend(batch)
            info = payload.get("info") or {}
            if not info.get("more_records", False):
                break
            page += 1

        return records

    def extract(
        self,
        *,
        last_sync_at: str | None = None,
        force: bool = False,
        http_client: httpx.Client | None = None,
    ) -> ExtractionResult:
        """Ejecuta la extracción incremental de módulos configurados en Zoho CRM.

        Args:
            last_sync_at: Timestamp ISO-8601 UTC de la última sincronización exitosa.
            force: Si es True, ignora last_sync_at y extrae todos los registros.
            http_client: Cliente HTTPX inyectado opcional para pruebas unitarias.

        Returns:
            Resultado estandarizado con archivos CSV escritos y conteo de registros.

        Raises:
            ValueError: Si ZOHO_ENABLED=true pero faltan credenciales OAuth2.
            httpx.HTTPStatusError: Si falla la autenticación o consulta a Zoho CRM.
            RuntimeError: Si Zoho OAuth2 no devuelve access_token.

        """
        if not self.config.enabled:
            return ExtractionResult(
                source_name=self.config.source_name,
                enabled=False,
                has_changes=False,
                skipped_reason="ZOHO_ENABLED=false",
            )

        if not (
            self.config.client_id
            and self.config.client_secret
            and self.config.refresh_token
        ):
            raise ValueError(
                "ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET y ZOHO_REFRESH_TOKEN "
                "son obligatorios cuando ZOHO_ENABLED=true."
            )

        sync_started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        modified_since = None if force else last_sync_at

        owns_client = http_client is None
        client = http_client or httpx.Client(timeout=self.config.timeout_seconds)
        written_files: list[Path] = []
        total_records = 0

        try:
            access_token = self._refresh_access_token(client)
            self.config.output_dir.mkdir(parents=True, exist_ok=True)

            for module in self.config.modules:
                records = self._fetch_module_records(
                    client,
                    access_token=access_token,
                    module=module,
                    modified_since=modified_since,
                )
                if not records:
                    logger.info("Zoho CRM módulo %s sin registros nuevos.", module)
                    continue

                df = pd.json_normalize(records)
                csv_path = self.config.output_dir / f"zoho_{module.lower()}.csv"
                df.to_csv(csv_path, index=False, encoding="utf-8")
                written_files.append(csv_path)
                total_records += len(df)
        finally:
            if owns_client:
                client.close()

        return ExtractionResult(
            source_name=self.config.source_name,
            enabled=True,
            has_changes=total_records > 0,
            files_written=written_files,
            records_extracted=total_records,
            new_cursor=sync_started_at,
            skipped_reason=None if total_records > 0 else "Sin cambios en Zoho CRM",
        )
