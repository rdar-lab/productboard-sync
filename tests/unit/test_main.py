import sys
from unittest.mock import MagicMock, patch

import pytest

from productboard_sync.__main__ import main
from productboard_sync.config import ALL_ENTITY_TYPES


@pytest.fixture
def local_env(tmp_path):
    return {
        "PRODUCTBOARD_API_KEY": "test-key",
        "STORAGE_BACKEND": "local",
        "LOCAL_OUTPUT_DIR": str(tmp_path),
    }


def test_entity_all_expands_to_all_entity_types(local_env):
    mock_runner = MagicMock()
    with patch("sys.argv", ["prog", "--entity", "all", "--dry-run"]), \
         patch.dict("os.environ", local_env, clear=True), \
         patch("productboard_sync.sync.runner.SyncRunner", return_value=mock_runner):
        main()
    mock_runner.run.assert_called_once_with(ALL_ENTITY_TYPES, dry_run=True)


def test_invalid_entity_type_exits_with_error(local_env):
    with patch("sys.argv", ["prog", "--entity", "bogus_type"]), \
         patch.dict("os.environ", local_env, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 2


def test_explicit_entity_types_passed_to_runner(local_env):
    mock_runner = MagicMock()
    with patch("sys.argv", ["prog", "--entity", "feature", "--entity", "notes", "--dry-run"]), \
         patch.dict("os.environ", local_env, clear=True), \
         patch("productboard_sync.sync.runner.SyncRunner", return_value=mock_runner):
        main()
    mock_runner.run.assert_called_once_with(["feature", "notes"], dry_run=True)
