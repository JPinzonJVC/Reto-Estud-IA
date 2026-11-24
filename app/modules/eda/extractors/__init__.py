"""Paquete de extractores desacoplados para Google Drive y Zoho CRM."""

from app.modules.eda.extractors.base import ExtractionResult, IngestionSource
from app.modules.eda.extractors.google_drive import (
    GoogleDriveConfig,
    GoogleDriveExtractor,
)
from app.modules.eda.extractors.watermarks import get_watermark, upsert_watermark
from app.modules.eda.extractors.zoho_crm import ZohoCRMConfig, ZohoCRMExtractor

__all__ = [
    "ExtractionResult",
    "GoogleDriveConfig",
    "GoogleDriveExtractor",
    "IngestionSource",
    "ZohoCRMConfig",
    "ZohoCRMExtractor",
    "get_watermark",
    "upsert_watermark",
]
