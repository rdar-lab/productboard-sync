import pytest
from pydantic import ValidationError


def make_settings(**kwargs):
    import os
    from unittest.mock import patch
    env = {"PRODUCTBOARD_API_KEY": "key", "STORAGE_BACKEND": "local", "LOCAL_OUTPUT_DIR": "/tmp", **kwargs}
    with patch.dict(os.environ, env, clear=True):
        from productboard_sync.config import Settings
        return Settings(_env_file=None)


def test_missing_api_key_raises():
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {"STORAGE_BACKEND": "local", "LOCAL_OUTPUT_DIR": "/tmp"}, clear=True):
        from productboard_sync.config import Settings
        with pytest.raises(ValidationError):
            Settings(_env_file=None)


def test_missing_storage_backend_raises():
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {"PRODUCTBOARD_API_KEY": "key", "LOCAL_OUTPUT_DIR": "/tmp"}, clear=True):
        from productboard_sync.config import Settings
        with pytest.raises(ValidationError):
            Settings(_env_file=None)


def test_local_backend_without_output_dir_raises():
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {"PRODUCTBOARD_API_KEY": "key", "STORAGE_BACKEND": "local"}, clear=True):
        from productboard_sync.config import Settings
        with pytest.raises((ValidationError, ValueError)):
            Settings(_env_file=None)


def test_onedrive_backend_without_folder_id_raises():
    import os
    from unittest.mock import patch
    env = {
        "PRODUCTBOARD_API_KEY": "key",
        "STORAGE_BACKEND": "onedrive",
        "ONEDRIVE_TENANT_ID": "t",
        "ONEDRIVE_CLIENT_ID": "c",
        "ONEDRIVE_CLIENT_SECRET": "s",
        "ONEDRIVE_DRIVE_ID": "d",
        # missing ONEDRIVE_FOLDER_ID
    }
    with patch.dict(os.environ, env, clear=True):
        from productboard_sync.config import Settings
        with pytest.raises((ValidationError, ValueError)):
            Settings(_env_file=None)


def test_sharepoint_backend_without_site_id_raises():
    import os
    from unittest.mock import patch
    env = {
        "PRODUCTBOARD_API_KEY": "key",
        "STORAGE_BACKEND": "sharepoint",
        "ONEDRIVE_TENANT_ID": "t",
        "ONEDRIVE_CLIENT_ID": "c",
        "ONEDRIVE_CLIENT_SECRET": "s",
        "SHAREPOINT_DRIVE_ID": "d",
        "SHAREPOINT_FOLDER_ID": "f",
        # missing SHAREPOINT_SITE_ID
    }
    with patch.dict(os.environ, env, clear=True):
        from productboard_sync.config import Settings
        with pytest.raises((ValidationError, ValueError)):
            Settings(_env_file=None)


def test_sync_entities_all_expands():
    settings = make_settings(SYNC_ENTITIES="all")
    from productboard_sync.config import ALL_ENTITY_TYPES
    assert settings.sync_entities == ALL_ENTITY_TYPES


def test_sync_entities_comma_list_parsed():
    settings = make_settings(SYNC_ENTITIES="feature,notes")
    assert settings.sync_entities == ["feature", "notes"]


def test_invalid_entity_type_raises():
    with pytest.raises((ValidationError, ValueError)):
        make_settings(SYNC_ENTITIES="invalid_type")
