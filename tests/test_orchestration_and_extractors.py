"""Pruebas unitarias para env_vars, extractores desacoplados, watermarks y flujo Prefect."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pandas as pd
import pytest
from sqlalchemy import create_engine

from app.env_vars import (
    DEFAULT_TIMEZONE,
    DEFAULT_WEEKLY_CRON,
    GoogleDriveEnvs,
    OrchestrationEnvs,
    ProjectEnvs,
    ZohoEnvs,
)
from app.modules.eda.extractors.google_drive import GoogleDriveExtractor
from app.modules.eda.extractors.watermarks import get_watermark, upsert_watermark
from app.modules.eda.extractors.zoho_crm import ZohoCRMExtractor
from app.modules.eda.orchestration.flows import eda_medallion_flow


def test_env_vars_models_load_dynamically(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida que los modelos Pydantic lean las variables al instanciarse.

    Args:
        monkeypatch: Fixture de pytest para inyectar variables de entorno.

    Returns:
        None.

    Raises:
        AssertionError: Si algún campo no refleja la variable de entorno configurada.

    """
    monkeypatch.setenv("ZOHO_ENABLED", "true")
    monkeypatch.setenv("ZOHO_MODULES", "Accounts, Deals")
    monkeypatch.setenv(
        "DRIVE_SCOPES",
        "https://www.googleapis.com/auth/drive.readonly, https://www.googleapis.com/auth/drive.metadata.readonly",
    )
    monkeypatch.setenv("EDA_SCHEDULE_CRON", "0 2 * * *")
    monkeypatch.setenv("EDA_SCHEDULE_TIMEZONE", "UTC")
    monkeypatch.setenv("EDA_FORCE_REPROCESS", "true")

    project_envs = ProjectEnvs()
    assert project_envs.zoho.enabled is True
    assert project_envs.zoho.modules == ["Accounts", "Deals"]
    assert project_envs.google_drive.drive_scopes == [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
    ]
    assert project_envs.orchestration.schedule_cron == "0 2 * * *"
    assert project_envs.orchestration.schedule_timezone == "UTC"
    assert project_envs.orchestration.force_reprocess is True


def test_orchestration_settings_defaults_and_invalid_cron(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valida el schedule semanal por defecto y rechazo de cron inválido.

    Args:
        monkeypatch: Fixture de pytest para manipular variables de entorno.

    Returns:
        None.

    Raises:
        AssertionError: Si los valores por defecto o la validación fallan.

    """
    monkeypatch.delenv("EDA_SCHEDULE_CRON", raising=False)
    monkeypatch.delenv("EDA_SCHEDULE_TIMEZONE", raising=False)
    monkeypatch.delenv("EDA_FORCE_REPROCESS", raising=False)

    defaults = OrchestrationEnvs()
    assert defaults.schedule_cron == DEFAULT_WEEKLY_CRON
    assert defaults.schedule_timezone == DEFAULT_TIMEZONE
    assert defaults.force_reprocess is False

    monkeypatch.setenv("EDA_SCHEDULE_CRON", "0 6 * *")
    with pytest.raises(ValueError, match="5 campos"):
        OrchestrationEnvs()


def test_watermarks_upsert_and_get() -> None:
    """Verifica creación y actualización de watermarks en SQLAlchemy.

    Args:
        None.

    Returns:
        None.

    Raises:
        AssertionError: Si el registro persistido no coincide con lo esperado.

    """
    engine = create_engine("sqlite:///:memory:")
    assert get_watermark(engine, "zoho_crm") is None

    created = upsert_watermark(
        engine,
        source_name="zoho_crm",
        last_status="SUCCESS",
        last_sync_at="2026-11-21T06:00:00Z",
        last_cursor="2026-11-21T06:00:00Z",
        records_extracted=42,
    )
    assert created.source_name == "zoho_crm"
    assert created.records_extracted == 42

    updated = upsert_watermark(
        engine,
        source_name="zoho_crm",
        last_status="SKIPPED",
        records_extracted=0,
        details="Sin cambios",
    )
    assert updated.last_sync_at == "2026-11-21T06:00:00Z"
    assert updated.last_status == "SKIPPED"


def test_google_drive_extractor_skips_when_disabled_or_unchanged(tmp_path: Path) -> None:
    """Verifica omisión cuando GDRIVE_ENABLED=false o el fingerprint no cambia.

    Args:
        tmp_path: Directorio temporal provisto por pytest.

    Returns:
        None.

    Raises:
        AssertionError: Si el comportamiento incremental no coincide.

    """
    disabled = GoogleDriveExtractor(GoogleDriveEnvs(enabled=False))
    res_disabled = disabled.extract()
    assert res_disabled.enabled is False
    assert res_disabled.has_changes is False

    mock_service = MagicMock()
    mock_service.files.return_value.list.return_value.execute.return_value = {
        "files": [
            {
                "id": "file-1",
                "name": "eventos.csv",
                "md5Checksum": "abc123",
                "modifiedTime": "2026-11-20T10:00:00Z",
            }
        ]
    }
    extractor = GoogleDriveExtractor(
        GoogleDriveEnvs(
            enabled=True,
            folder_id="folder-xyz",
            download_dir=tmp_path / "drive",
        )
    )
    with patch.object(extractor, "_download_file", return_value=b"col1,col2\n1,2\n"):
        first = extractor.extract(drive_service=mock_service)
    assert first.has_changes is True
    assert first.records_extracted == 2
    assert (tmp_path / "drive" / "eventos.csv").exists()

    second = extractor.extract(last_cursor=first.new_cursor, drive_service=mock_service)
    assert second.has_changes is False
    assert second.skipped_reason == "Sin cambios en carpeta de Google Drive"


def test_google_drive_extractor_exports_excel_sheets(tmp_path: Path) -> None:
    """Verifica descarga de .xlsx y exportación automática de sus hojas a .csv.

    Args:
        tmp_path: Directorio temporal provisto por pytest.

    Returns:
        None.

    Raises:
        AssertionError: Si no se exportan los archivos esperados.

    """
    mock_service = MagicMock()
    mock_service.files.return_value.list.return_value.execute.return_value = {
        "files": [
            {
                "id": "xlsx-1",
                "name": "evento_semanal.xlsx",
                "md5Checksum": "xyz999",
                "modifiedTime": "2026-11-21T05:00:00Z",
            }
        ]
    }

    extractor = GoogleDriveExtractor(
        GoogleDriveEnvs(
            enabled=True,
            folder_id="folder-xyz",
            download_dir=tmp_path / "drive",
            export_excel_sheets_to_csv=True,
        )
    )
    fake_sheets = {
        "Asistencia": pd.DataFrame([["empresa", "asistentes"], ["ACTHO", "12"]]),
        "Vacia": pd.DataFrame(),
    }
    with (
        patch.object(extractor, "_download_file", return_value=b"fake-xlsx-bytes"),
        patch(
            "app.modules.eda.extractors.google_drive.pd.read_excel",
            return_value=fake_sheets,
        ),
    ):
        result = extractor.extract(drive_service=mock_service)

    assert result.has_changes is True
    assert result.records_extracted == 2
    assert (tmp_path / "drive" / "evento_semanal.xlsx").exists()
    assert (tmp_path / "drive" / "evento_semanal__Asistencia.csv").exists()
    assert not (tmp_path / "drive" / "evento_semanal__Vacia.csv").exists()


def test_google_drive_extractor_recursive_subfolders(tmp_path: Path) -> None:
    """Verifica recorrido recursivo de subcarpetas sin sobreescribir Excels homónimos.

    Args:
        tmp_path: Directorio temporal provisto por pytest.

    Returns:
        None.

    Raises:
        AssertionError: Si no se preservan las rutas relativas por subcarpeta.

    """
    mock_service = MagicMock()
    mock_service.files.return_value.list.return_value.execute.side_effect = [
        {
            "files": [
                {
                    "id": "sub-1",
                    "name": "Semana_01",
                    "mimeType": "application/vnd.google-apps.folder",
                },
                {
                    "id": "sub-2",
                    "name": "Semana_02",
                    "mimeType": "application/vnd.google-apps.folder",
                },
            ]
        },
        {
            "files": [
                {
                    "id": "xlsx-s1",
                    "name": "datos.xlsx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "md5Checksum": "hash1",
                    "modifiedTime": "2026-11-10T10:00:00Z",
                }
            ]
        },
        {
            "files": [
                {
                    "id": "xlsx-s2",
                    "name": "datos.xlsx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "md5Checksum": "hash2",
                    "modifiedTime": "2026-11-17T10:00:00Z",
                }
            ]
        },
    ]

    extractor = GoogleDriveExtractor(
        GoogleDriveEnvs(
            enabled=True,
            folder_id="root-folder",
            download_dir=tmp_path / "drive",
            export_excel_sheets_to_csv=True,
        )
    )
    fake_sheets = {"Hoja1": pd.DataFrame({"a": [1, 2]})}
    with (
        patch.object(extractor, "_download_file", return_value=b"fake-xlsx"),
        patch(
            "app.modules.eda.extractors.google_drive.pd.read_excel",
            return_value=fake_sheets,
        ),
    ):
        result = extractor.extract(drive_service=mock_service)

    assert result.has_changes is True
    assert result.records_extracted == 4
    assert (tmp_path / "drive" / "Semana_01" / "datos.xlsx").exists()
    assert (tmp_path / "drive" / "Semana_01" / "datos__Hoja1.csv").exists()
    assert (tmp_path / "drive" / "Semana_02" / "datos.xlsx").exists()
    assert (tmp_path / "drive" / "Semana_02" / "datos__Hoja1.csv").exists()


def test_zoho_crm_extractor_incremental(tmp_path: Path) -> None:
    """Verifica autenticación OAuth2 y descarga incremental con If-Modified-Since.

    Args:
        tmp_path: Directorio temporal provisto por pytest.

    Returns:
        None.

    Raises:
        AssertionError: Si los encabezados o CSV generados no coinciden.

    """
    captured_headers: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Simula respuestas HTTP de Zoho OAuth2 y CRM API v6.

        Args:
            request: Petición HTTPX interceptada por MockTransport.

        Returns:
            Respuesta HTTP simulada.

        Raises:
            None.

        """
        if request.url.path.endswith("/oauth/v2/token"):
            return httpx.Response(200, json={"access_token": "tok-123"})
        if request.url.path.endswith("/crm/v6/Accounts"):
            captured_headers.append(request.headers.get("If-Modified-Since", ""))
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "1", "Account_Name": "Empresa Demo"}],
                    "info": {"more_records": False},
                },
            )
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    config = ZohoEnvs(
        enabled=True,
        client_id="cid",
        client_secret="csec",
        refresh_token="rtok",
        modules=["Accounts", "Contacts"],
        output_dir=tmp_path / "zoho",
    )
    extractor = ZohoCRMExtractor(config)

    with httpx.Client(transport=transport) as client:
        result = extractor.extract(
            last_sync_at="2026-11-14T06:00:00Z",
            http_client=client,
        )

    assert result.has_changes is True
    assert result.records_extracted == 1
    assert captured_headers == ["2026-11-14T06:00:00Z"]
    assert (tmp_path / "zoho" / "zoho_accounts.csv").exists()
    assert not (tmp_path / "zoho" / "zoho_contacts.csv").exists()


def test_eda_medallion_flow_skips_and_runs_conditionally() -> None:
    """Verifica que el flow solo ejecute Medallion si hay cambios o force=True.

    Args:
        None.

    Returns:
        None.

    Raises:
        AssertionError: Si la ejecución condicional del flujo falla.

    """
    engine = create_engine("sqlite:///:memory:")
    drive_disabled = GoogleDriveExtractor(GoogleDriveEnvs(enabled=False))
    zoho_disabled = ZohoCRMExtractor(ZohoEnvs(enabled=False))

    with patch(
        "app.modules.eda.orchestration.flows.ejecutar_pipeline_completo"
    ) as mock_etl:
        skipped = eda_medallion_flow(
            force_reprocess=False,
            engine=engine,
            drive_extractor=drive_disabled,
            zoho_extractor=zoho_disabled,
        )
        assert skipped["status"] == "SKIPPED_NO_CHANGES"
        mock_etl.assert_not_called()

        mock_etl.return_value = {"run_id": "run-test-001", "errores": []}
        forced = eda_medallion_flow(
            force_reprocess=True,
            engine=engine,
            drive_extractor=drive_disabled,
            zoho_extractor=zoho_disabled,
        )
        assert forced["status"] == "COMPLETED"
        assert forced["pipeline_run_id"] == "run-test-001"
        mock_etl.assert_called_once()


def test_eda_medallion_flow_cleans_staging_files_after_success(tmp_path: Path) -> None:
    """Verifica que los archivos temporales en raw_drive/raw_zoho se eliminen tras éxito.

    Args:
        tmp_path: Directorio temporal provisto por pytest.

    Returns:
        None.

    Raises:
        AssertionError: Si los archivos temporales no se eliminan correctamente.

    """
    from app.modules.eda.extractors.base import ExtractionResult

    engine = create_engine("sqlite:///:memory:")
    drive_file = tmp_path / "raw_drive" / "dim_kams.xlsx"
    zoho_file = tmp_path / "raw_zoho" / "zoho_accounts.csv"
    drive_file.parent.mkdir(parents=True)
    zoho_file.parent.mkdir(parents=True)
    drive_file.write_text("dummy", encoding="utf-8")
    zoho_file.write_text("id\n1\n", encoding="utf-8")

    mock_drive = MagicMock(spec=GoogleDriveExtractor)
    mock_drive.config = GoogleDriveEnvs(enabled=True)
    mock_drive.extract.return_value = ExtractionResult(
        source_name="google_drive",
        enabled=True,
        has_changes=True,
        records_extracted=1,
        files_written=[drive_file],
        new_cursor="cur-1",
    )

    mock_zoho = MagicMock(spec=ZohoCRMExtractor)
    mock_zoho.config = ZohoEnvs(enabled=True)
    mock_zoho.extract.return_value = ExtractionResult(
        source_name="zoho_crm",
        enabled=True,
        has_changes=True,
        records_extracted=1,
        files_written=[zoho_file],
        new_cursor="2026-11-25T00:00:00Z",
    )

    with patch(
        "app.modules.eda.orchestration.flows.ejecutar_pipeline_completo",
        return_value={"run_id": "run-clean-001", "errores": []},
    ):
        res = eda_medallion_flow(
            force_reprocess=False,
            cleanup_raw_after_load=True,
            engine=engine,
            drive_extractor=mock_drive,
            zoho_extractor=mock_zoho,
        )

    assert res["status"] == "COMPLETED"
    assert res["staging_cleaned_files"] == 2
    assert not drive_file.exists()
    assert not zoho_file.exists()
