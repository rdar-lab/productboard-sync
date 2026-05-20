import pytest
from unittest.mock import MagicMock
from productboard_sync.sync.runner import SyncRunner
from productboard_sync.productboard.models import Entity, Note, Member, Team


def make_runner(entities=None, notes=None, members=None, teams=None):
    client = MagicMock()
    client.search_entities.return_value = iter(entities or [])
    client.list_notes.return_value = iter(notes or [])
    client.list_members.return_value = iter(members or [])
    client.list_teams.return_value = iter(teams or [])
    client.get_entity_configuration.return_value = MagicMock(type="feature", fields=[])
    backend = MagicMock()
    return SyncRunner(client, backend), client, backend


def test_feature_type_routes_to_search_entities_and_writes_csv():
    runner, client, backend = make_runner()
    runner.run(["feature"])
    client.search_entities.assert_called_once_with(["feature"])
    backend.write_file.assert_called_once()
    filename = backend.write_file.call_args[0][0]
    assert filename == "features.csv"


def test_notes_type_routes_to_list_notes():
    runner, client, backend = make_runner()
    runner.run(["notes"])
    client.list_notes.assert_called_once()
    backend.write_file.assert_called_once()
    assert backend.write_file.call_args[0][0] == "notes.csv"


def test_dry_run_does_not_write():
    runner, client, backend = make_runner()
    runner.run(["feature", "notes"], dry_run=True)
    backend.write_file.assert_not_called()


def test_failed_entity_type_does_not_stop_others():
    runner, client, backend = make_runner()
    client.search_entities.side_effect = Exception("API error")
    with pytest.raises(RuntimeError, match="Sync failed for entity type"):
        runner.run(["feature", "notes"])
    backend.write_file.assert_called_once()
    assert backend.write_file.call_args[0][0] == "notes.csv"


def test_all_failed_raises_runtime_error():
    runner, client, backend = make_runner()
    client.search_entities.side_effect = Exception("API error")
    client.list_notes.side_effect = Exception("API error")
    with pytest.raises(RuntimeError, match="Sync failed for entity type"):
        runner.run(["feature", "notes"])
    backend.write_file.assert_not_called()


def test_unknown_entity_type_skipped_gracefully():
    runner, client, backend = make_runner()
    runner.run(["unknown_type"])
    backend.write_file.assert_not_called()
