from unittest.mock import MagicMock
from productboard_sync.productboard.models import EntityConfiguration, EntityFieldConfig
from productboard_sync.sync.fields import FieldDiscovery, STANDARD_FIELD_IDS


def make_client_with_config(fields):
    client = MagicMock()
    config = EntityConfiguration(type="feature", fields=fields)
    client.get_entity_configuration.return_value = config
    return client


def test_standard_fields_come_first():
    client = make_client_with_config([
        EntityFieldConfig(id="name", name="Name", type="text"),
        EntityFieldConfig(id="custom-xyz", name="Priority", type="single_select"),
    ])
    discovery = FieldDiscovery(client)
    columns = discovery.get_columns("feature")
    column_ids = [cid for cid, _ in columns]
    for i, std in enumerate(STANDARD_FIELD_IDS):
        assert column_ids[i] == std


def test_custom_fields_appended_sorted_by_name():
    client = make_client_with_config([
        EntityFieldConfig(id="c2", name="Zebra", type="text"),
        EntityFieldConfig(id="c1", name="Alpha", type="text"),
    ])
    discovery = FieldDiscovery(client)
    columns = discovery.get_columns("feature")
    custom_names = [name for cid, name in columns if cid not in STANDARD_FIELD_IDS]
    assert custom_names == ["Alpha", "Zebra"]


def test_result_is_cached():
    client = make_client_with_config([])
    discovery = FieldDiscovery(client)
    discovery.get_columns("feature")
    discovery.get_columns("feature")
    assert client.get_entity_configuration.call_count == 1


def test_fallback_to_standard_on_error():
    client = MagicMock()
    client.get_entity_configuration.side_effect = Exception("API error")
    discovery = FieldDiscovery(client)
    columns = discovery.get_columns("feature")
    assert [cid for cid, _ in columns] == STANDARD_FIELD_IDS
