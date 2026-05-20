from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ALL_ENTITY_TYPES = [
    "feature",
    "subfeature",
    "component",
    "product",
    "initiative",
    "objective",
    "keyResult",
    "release",
    "releaseGroup",
    "notes",
    "members",
    "teams",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    productboard_api_key: str
    storage_backend: str

    local_output_dir: Optional[Path] = None

    onedrive_tenant_id: Optional[str] = None
    onedrive_client_id: Optional[str] = None
    onedrive_client_secret: Optional[str] = None

    onedrive_drive_id: Optional[str] = None
    onedrive_folder_id: Optional[str] = None

    sharepoint_site_id: Optional[str] = None
    sharepoint_drive_id: Optional[str] = None
    sharepoint_folder_id: Optional[str] = None

    sync_entities: Annotated[list[str], NoDecode] = ALL_ENTITY_TYPES.copy()
    log_level: str = "INFO"
    request_timeout: int = 30

    @field_validator("storage_backend", mode="before")
    @classmethod
    def normalize_storage_backend(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("sync_entities", mode="before")
    @classmethod
    def parse_sync_entities(cls, v):
        if isinstance(v, str):
            if v.strip().lower() == "all":
                return ALL_ENTITY_TYPES.copy()
            return [e.strip() for e in v.split(",") if e.strip()]
        return v

    @field_validator("sync_entities", mode="after")
    @classmethod
    def validate_entity_types(cls, v: list[str]) -> list[str]:
        invalid = [e for e in v if e not in ALL_ENTITY_TYPES]
        if invalid:
            raise ValueError(f"Unknown entity types: {invalid}. Valid types: {ALL_ENTITY_TYPES}")
        return v

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @model_validator(mode="after")
    def validate_backend_config(self) -> "Settings":
        backend = self.storage_backend.lower()
        if backend == "local" and not self.local_output_dir:
            raise ValueError("LOCAL_OUTPUT_DIR is required when STORAGE_BACKEND=local")
        if backend == "onedrive":
            missing = [
                f
                for f in [
                    "onedrive_tenant_id",
                    "onedrive_client_id",
                    "onedrive_client_secret",
                    "onedrive_drive_id",
                    "onedrive_folder_id",
                ]
                if not getattr(self, f)
            ]
            if missing:
                raise ValueError(f"Missing OneDrive config: {missing}")
        if backend == "sharepoint":
            missing = [
                f
                for f in [
                    "onedrive_tenant_id",
                    "onedrive_client_id",
                    "onedrive_client_secret",
                    "sharepoint_site_id",
                    "sharepoint_drive_id",
                    "sharepoint_folder_id",
                ]
                if not getattr(self, f)
            ]
            if missing:
                raise ValueError(f"Missing SharePoint config: {missing}")
        if backend not in {"local", "onedrive", "sharepoint"}:
            raise ValueError(f"Unknown storage backend: {self.storage_backend}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_storage_backend(settings: Settings | None = None):
    if settings is None:
        settings = get_settings()

    backend = settings.storage_backend.lower()
    if backend == "local":
        from productboard_sync.storage.local import LocalStorageBackend

        return LocalStorageBackend(settings.local_output_dir)
    if backend == "onedrive":
        from productboard_sync.storage.onedrive import OneDriveStorageBackend

        return OneDriveStorageBackend(
            tenant_id=settings.onedrive_tenant_id,
            client_id=settings.onedrive_client_id,
            client_secret=settings.onedrive_client_secret,
            drive_id=settings.onedrive_drive_id,
            folder_id=settings.onedrive_folder_id,
            timeout=settings.request_timeout,
        )
    if backend == "sharepoint":
        from productboard_sync.storage.sharepoint import SharePointStorageBackend

        return SharePointStorageBackend(
            tenant_id=settings.onedrive_tenant_id,
            client_id=settings.onedrive_client_id,
            client_secret=settings.onedrive_client_secret,
            site_id=settings.sharepoint_site_id,
            drive_id=settings.sharepoint_drive_id,
            folder_id=settings.sharepoint_folder_id,
            timeout=settings.request_timeout,
        )
    raise ValueError(f"Unknown storage backend: {settings.storage_backend}")
