import pytest
import responses as resp_mock
from unittest.mock import MagicMock, patch
from productboard_sync.productboard.client import ProductboardClient, BASE_URL


@pytest.fixture
def client():
    return ProductboardClient("test-api-key")


@resp_mock.activate
def test_auth_header_is_set(client):
    resp_mock.add(resp_mock.GET, f"{BASE_URL}/members", json={"data": [], "links": {"next": None}})
    list(client.list_members())
    assert resp_mock.calls[0].request.headers["Authorization"] == "Bearer test-api-key"


@resp_mock.activate
def test_search_entities_posts_correct_body(client):
    resp_mock.add(resp_mock.POST, f"{BASE_URL}/entities/search", json={"data": [], "links": {"next": None}})
    list(client.search_entities(["feature"]))
    import json
    body = json.loads(resp_mock.calls[0].request.body)
    assert body["data"]["filter"]["type"] == ["feature"]


@resp_mock.activate
def test_list_notes_uses_get(client):
    resp_mock.add(resp_mock.GET, f"{BASE_URL}/notes", json={"data": [], "links": {"next": None}})
    list(client.list_notes())
    assert resp_mock.calls[0].request.method == "GET"


@resp_mock.activate
def test_list_members_uses_get(client):
    resp_mock.add(resp_mock.GET, f"{BASE_URL}/members", json={"data": [], "links": {"next": None}})
    list(client.list_members())
    assert resp_mock.calls[0].request.method == "GET"


@resp_mock.activate
def test_get_entity_configuration(client):
    resp_mock.add(
        resp_mock.GET,
        f"{BASE_URL}/entities/configurations/feature",
        json={"data": {"type": "feature", "fields": [{"id": "name", "name": "Name", "type": "text"}]}},
    )
    config = client.get_entity_configuration("feature")
    assert config.type == "feature"
    assert len(config.fields) == 1
    assert config.fields[0].id == "name"


def test_request_passes_timeout_to_session():
    client = ProductboardClient("key", timeout=42)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    with patch.object(client._session, "request", return_value=mock_resp) as mock_req:
        client._request("GET", "https://api.example.com")
    assert mock_req.call_args[1]["timeout"] == 42


def test_default_timeout_is_30():
    client = ProductboardClient("key")
    assert client._timeout == 30
