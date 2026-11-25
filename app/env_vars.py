"""Modelos Pydantic centralizados para las variables de entorno utilizadas por Python."""

from enum import Enum
import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class IngestionSource(str, Enum):
    """Catálogo canónico de fuentes externas de ingesta."""

    GOOGLE_DRIVE = "google_drive"
    """Fuente de archivos Excel y CSV hospedados en Google Drive."""

    ZOHO_CRM = "zoho_crm"
    """Fuente incremental de módulos del CRM Zoho."""

DEFAULT_DRIVE_SCOPES = "https://www.googleapis.com/auth/drive.readonly"
DEFAULT_WEEKLY_CRON = "0 6 * * 1"
DEFAULT_TIMEZONE = "America/Bogota"


def _parse_bool_env(var_name: str, default: bool = False) -> bool:
    """Lee una variable de entorno booleana de forma segura.

    Args:
        var_name: Nombre de la variable de entorno.
        default: Valor por defecto si la variable no está definida.

    Returns:
        Valor booleano interpretado desde la variable de entorno.

    Raises:
        None.

    """
    raw = os.getenv(var_name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "si"}


def _parse_csv_list_env(var_name: str, default: str) -> list[str]:
    """Lee una variable de entorno separada por comas como lista de cadenas.

    Args:
        var_name: Nombre de la variable de entorno.
        default: Cadena por defecto separada por comas.

    Returns:
        Lista de elementos sin espacios vacíos.

    Raises:
        None.

    """
    raw = os.getenv(var_name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class AppEnvs(BaseModel):
    """Variables de entorno generales de la aplicación FastAPI."""

    app_name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "Reto-Estud-IA"))
    """Nombre descriptivo de la aplicación (APP_NAME)."""

    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    """Entorno de ejecución: development, staging o production (APP_ENV)."""

    app_host: str = Field(default_factory=lambda: os.getenv("APP_HOST", "0.0.0.0"))
    """Interfaz de red donde escucha uvicorn (APP_HOST)."""

    app_port: int = Field(default_factory=lambda: int(os.getenv("APP_PORT", "8000")))
    """Puerto HTTP de la aplicación FastAPI (APP_PORT)."""

    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    """Nivel de logging de Python: DEBUG, INFO, WARNING, ERROR (LOG_LEVEL)."""

    input_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("INPUT_DIR", "./input"))
    )
    """Directorio raíz de insumos y salidas locales del ETL (INPUT_DIR)."""


class DatabaseEnvs(BaseModel):
    """Variables de entorno de conexión a PostgreSQL."""

    postgres_host: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost")
    )
    """Host del servidor PostgreSQL (POSTGRES_HOST)."""

    postgres_port: int = Field(
        default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432"))
    )
    """Puerto TCP de PostgreSQL (POSTGRES_PORT)."""

    postgres_user: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_USER", "postgres")
    )
    """Usuario de autenticación en PostgreSQL (POSTGRES_USER)."""

    postgres_password: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "postgres123")
    )
    """Contraseña del usuario de PostgreSQL (POSTGRES_PASSWORD)."""

    postgres_db: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_DB", "estudia_db")
    )
    """Nombre de la base de datos principal del proyecto (POSTGRES_DB)."""

    database_url: str | None = Field(
        default_factory=lambda: os.getenv("DATABASE_URL") or None
    )
    """URL completa SQLAlchemy opcional; sobreescribe los campos POSTGRES_* (DATABASE_URL)."""

    def build_url(self) -> str:
        """Construye la URL SQLAlchemy de conexión a PostgreSQL.

        Args:
            None.

        Returns:
            Cadena de conexión PostgreSQL compatible con SQLAlchemy.

        Raises:
            None.

        """
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


class OrchestrationEnvs(BaseModel):
    """Variables de entorno para Prefect y programación del pipeline EDA."""

    prefect_api_url: str = Field(
        default_factory=lambda: os.getenv(
            "PREFECT_API_URL", "http://localhost:4200/api"
        ).rstrip("/")
    )
    """URL base de la API de Prefect Server (PREFECT_API_URL)."""

    schedule_cron: str = Field(
        default_factory=lambda: os.getenv("EDA_SCHEDULE_CRON", DEFAULT_WEEKLY_CRON),
        validate_default=True,
    )
    """Expresión cron de 5 campos para el scheduler semanal/periódico (EDA_SCHEDULE_CRON)."""

    schedule_timezone: str = Field(
        default_factory=lambda: os.getenv(
            "EDA_SCHEDULE_TIMEZONE", DEFAULT_TIMEZONE
        ).strip()
    )
    """Zona horaria IANA usada por Prefect para evaluar el cron (EDA_SCHEDULE_TIMEZONE)."""

    deployment_name: str = Field(
        default_factory=lambda: os.getenv(
            "EDA_DEPLOYMENT_NAME", "eda-medallion-weekly"
        ).strip()
    )
    """Nombre del deployment registrado en Prefect Server (EDA_DEPLOYMENT_NAME)."""

    force_reprocess: bool = Field(
        default_factory=lambda: _parse_bool_env("EDA_FORCE_REPROCESS", False)
    )
    """Fuerza la ejecución del Medallion ETL aunque no haya cambios en fuentes (EDA_FORCE_REPROCESS)."""

    cleanup_raw_after_load: bool = Field(
        default_factory=lambda: _parse_bool_env("EDA_CLEANUP_RAW_AFTER_LOAD", True)
    )
    """Elimina archivos temporales en raw_drive y raw_zoho tras carga exitosa (EDA_CLEANUP_RAW_AFTER_LOAD)."""

    @field_validator("schedule_cron")
    @classmethod
    def _validate_cron_expression(cls, value: str) -> str:
        """Valida que la expresión cron tenga exactamente 5 campos.

        Args:
            value: Expresión cron recibida desde entorno o argumento.

        Returns:
            Expresión cron normalizada con espacios simples.

        Raises:
            ValueError: Si la expresión no tiene exactamente 5 campos.

        """
        cleaned = " ".join(value.strip().split())
        if len(cleaned.split(" ")) != 5:
            raise ValueError(
                "EDA_SCHEDULE_CRON debe ser una expresión cron válida de 5 campos "
                f"(ej. '{DEFAULT_WEEKLY_CRON}'), recibido: '{value}'"
            )
        return cleaned


class GoogleDriveEnvs(BaseModel):
    """Variables de entorno para el extractor de Google Drive."""

    source_name: str = Field(
        default_factory=lambda: os.getenv(
            "GDRIVE_SOURCE_NAME", IngestionSource.GOOGLE_DRIVE.value
        ).strip()
    )
    """Identificador único de la fuente en audit_ingestion_watermarks (GDRIVE_SOURCE_NAME)."""

    enabled: bool = Field(
        default_factory=lambda: _parse_bool_env("GDRIVE_ENABLED", False)
    )
    """Habilita o deshabilita la extracción desde Google Drive (GDRIVE_ENABLED)."""

    folder_id: str = Field(
        default_factory=lambda: os.getenv("GDRIVE_FOLDER_ID", "").strip()
    )
    """ID de la carpeta raíz en Google Drive donde residen los Excel/CSV (GDRIVE_FOLDER_ID)."""

    credentials_file: Path | None = Field(
        default_factory=lambda: (
            Path(os.getenv("GDRIVE_CREDENTIALS_FILE", "").strip())
            if os.getenv("GDRIVE_CREDENTIALS_FILE", "").strip()
            else None
        )
    )
    """Ruta al JSON de Service Account de Google Cloud (GDRIVE_CREDENTIALS_FILE)."""

    download_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("GDRIVE_DOWNLOAD_DIR", "input/raw_drive"))
    )
    """Carpeta local destino para archivos descargados de Drive (GDRIVE_DOWNLOAD_DIR)."""

    export_excel_sheets_to_csv: bool = Field(
        default_factory=lambda: _parse_bool_env("GDRIVE_EXPORT_XLSX_TO_CSV", True)
    )
    """Exporta cada hoja de archivos .xlsx/.xls a .csv tras descargarlos (GDRIVE_EXPORT_XLSX_TO_CSV)."""

    drive_scopes: list[str] = Field(
        default_factory=lambda: _parse_csv_list_env("DRIVE_SCOPES", DEFAULT_DRIVE_SCOPES),
        validate_default=True,
    )
    """Lista de scopes OAuth2 separados por coma para Google Drive API (DRIVE_SCOPES)."""

    @field_validator("drive_scopes")
    @classmethod
    def _validate_drive_scopes(cls, value: list[str]) -> list[str]:
        """Valida que exista al menos un scope de Google Drive configurado.

        Args:
            value: Lista de scopes OAuth2 para Google Drive.

        Returns:
            Lista validada de scopes no vacíos.

        Raises:
            ValueError: Si la lista de scopes queda vacía.

        """
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("DRIVE_SCOPES debe contener al menos un scope válido.")
        return cleaned


class ZohoEnvs(BaseModel):
    """Variables de entorno para el extractor incremental de Zoho CRM."""

    source_name: str = Field(
        default_factory=lambda: os.getenv(
            "ZOHO_SOURCE_NAME", IngestionSource.ZOHO_CRM.value
        ).strip()
    )
    """Identificador único de la fuente en audit_ingestion_watermarks (ZOHO_SOURCE_NAME)."""

    enabled: bool = Field(
        default_factory=lambda: _parse_bool_env("ZOHO_ENABLED", False)
    )
    """Habilita o deshabilita la extracción incremental desde Zoho CRM (ZOHO_ENABLED)."""

    client_id: str = Field(
        default_factory=lambda: os.getenv("ZOHO_CLIENT_ID", "").strip()
    )
    """Client ID de la aplicación OAuth2 registrada en Zoho (ZOHO_CLIENT_ID)."""

    client_secret: str = Field(
        default_factory=lambda: os.getenv("ZOHO_CLIENT_SECRET", "").strip()
    )
    """Client Secret de la aplicación OAuth2 en Zoho (ZOHO_CLIENT_SECRET)."""

    refresh_token: str = Field(
        default_factory=lambda: os.getenv("ZOHO_REFRESH_TOKEN", "").strip()
    )
    """Refresh Token OAuth2 persistente para renovar access tokens de Zoho (ZOHO_REFRESH_TOKEN)."""

    accounts_url: str = Field(
        default_factory=lambda: os.getenv(
            "ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com"
        ).rstrip("/")
    )
    """URL base del servidor de autenticación OAuth2 de Zoho según región (ZOHO_ACCOUNTS_URL)."""

    api_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "ZOHO_API_BASE_URL", "https://www.zohoapis.com"
        ).rstrip("/")
    )
    """URL base de la API REST de Zoho CRM según región (ZOHO_API_BASE_URL)."""

    modules: list[str] = Field(
        default_factory=lambda: _parse_csv_list_env(
            "ZOHO_MODULES", "Accounts,Contacts,Deals"
        )
    )
    """Módulos de Zoho CRM a consultar separados por coma (ZOHO_MODULES)."""

    output_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("ZOHO_OUTPUT_DIR", "input/raw_zoho"))
    )
    """Carpeta local destino para los CSV extraídos desde Zoho CRM (ZOHO_OUTPUT_DIR)."""

    timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("ZOHO_TIMEOUT_SECONDS", "30.0"))
    )
    """Tiempo máximo de espera en segundos por petición HTTP a Zoho (ZOHO_TIMEOUT_SECONDS)."""


class ProjectEnvs(BaseModel):
    """Contenedor unificado de todas las variables de entorno del proyecto."""

    app: AppEnvs = Field(default_factory=AppEnvs)
    """Configuración general de la aplicación FastAPI."""

    database: DatabaseEnvs = Field(default_factory=DatabaseEnvs)
    """Configuración de conexión a PostgreSQL."""

    orchestration: OrchestrationEnvs = Field(default_factory=OrchestrationEnvs)
    """Configuración de Prefect y programación cron."""

    google_drive: GoogleDriveEnvs = Field(default_factory=GoogleDriveEnvs)
    """Configuración del extractor de Google Drive."""

    zoho: ZohoEnvs = Field(default_factory=ZohoEnvs)
    """Configuración del extractor incremental de Zoho CRM."""
