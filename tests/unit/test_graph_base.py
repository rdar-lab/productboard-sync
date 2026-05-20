import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from productboard_sync.storage._graph_base import GraphAuthMixin


class ConcreteGraphClient(GraphAuthMixin):
    def __init__(self, tenant_id="tenant", client_id="cid", client_secret="secret", timeout=30):
        self._init_auth(tenant_id, client_id, client_secret, timeout=timeout)


@pytest.fixture
def mock_msal_app():
    app = MagicMock()
    app.acquire_token_for_client.return_value = {
        "access_token": "test-token",
        "expires_in": 3600,
    }
    return app


@pytest.fixture
def client(mock_msal_app):
    with patch("msal.ConfidentialClientApplication", return_value=mock_msal_app):
        c = ConcreteGraphClient()
    return c, mock_msal_app


def make_mock_response(status_code, body=None, text=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {}
    resp.text = text or ""
    resp.json.return_value = body or {}
    if status_code >= 400:
        http_err = requests.exceptions.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_err
    else:
        resp.raise_for_status.return_value = None
    return resp


# --- token ---

def test_get_token_acquires_on_first_call(client):
    c, app = client
    assert c._get_token() == "test-token"
    app.acquire_token_for_client.assert_called_once()


def test_get_token_cached_within_expiry(client):
    c, app = client
    c._get_token()
    c._get_token()
    app.acquire_token_for_client.assert_called_once()


def test_get_token_refreshes_when_expired(client):
    c, app = client
    c._get_token()
    c._token_expiry = time.time()  # force expiry
    c._get_token()
    assert app.acquire_token_for_client.call_count == 2


def test_get_token_raises_on_msal_error(client):
    c, app = client
    app.acquire_token_for_client.return_value = {
        "error": "invalid_client",
        "error_description": "bad credentials",
    }
    with pytest.raises(RuntimeError, match="MSAL token acquisition failed"):
        c._get_token()


# --- _graph_put ---

def test_graph_put_sends_correct_content_type(client):
    c, _ = client
    c._session.request = MagicMock(return_value=make_mock_response(200))
    c._graph_put("https://example.com/file", "a,b\n1,2\n")
    _, kwargs = c._session.request.call_args
    assert kwargs["headers"].get("Content-Type") == "text/csv; charset=utf-8"


def test_graph_put_sends_encoded_body(client):
    c, _ = client
    c._session.request = MagicMock(return_value=make_mock_response(200))
    c._graph_put("https://example.com/file", "hello")
    _, kwargs = c._session.request.call_args
    assert kwargs["data"] == b"hello"


# --- _graph_get_text ---

def test_graph_get_text_returns_response_text(client):
    c, _ = client
    c._session.request = MagicMock(return_value=make_mock_response(200, text="csv data"))
    assert c._graph_get_text("https://example.com/file") == "csv data"


# --- _graph_list_children ---

def test_graph_list_children_single_page(client):
    c, _ = client
    resp = make_mock_response(200, body={"value": [{"name": "a.csv"}, {"name": "b.csv"}]})
    c._session.request = MagicMock(return_value=resp)
    items = c._graph_list_children("https://example.com/children")
    assert [i["name"] for i in items] == ["a.csv", "b.csv"]
    assert c._session.request.call_count == 1


def test_graph_list_children_follows_next_link(client):
    c, _ = client
    page1 = make_mock_response(200, body={
        "value": [{"name": "a.csv"}],
        "@odata.nextLink": "https://example.com/children?skip=1",
    })
    page2 = make_mock_response(200, body={"value": [{"name": "b.csv"}]})
    c._session.request = MagicMock(side_effect=[page1, page2])
    items = c._graph_list_children("https://example.com/children")
    assert [i["name"] for i in items] == ["a.csv", "b.csv"]
    assert c._session.request.call_count == 2


# --- _graph_delete ---

def test_graph_delete_succeeds_normally(client):
    c, _ = client
    c._session.request = MagicMock(return_value=make_mock_response(204))
    c._graph_delete("https://example.com/file")  # should not raise


def test_graph_delete_silent_on_404(client):
    c, _ = client
    c._session.request = MagicMock(return_value=make_mock_response(404))
    c._graph_delete("https://example.com/file")  # should not raise


def test_graph_delete_raises_on_403(client):
    c, _ = client
    c._session.request = MagicMock(return_value=make_mock_response(403))
    with pytest.raises(requests.exceptions.HTTPError):
        c._graph_delete("https://example.com/file")


# --- auth header injected ---

def test_auth_header_sent_with_request(client):
    c, _ = client
    c._session.request = MagicMock(return_value=make_mock_response(200))
    c._graph_get_text("https://example.com/file")
    _, kwargs = c._session.request.call_args
    assert kwargs["headers"].get("Authorization") == "Bearer test-token"


def test_request_passes_timeout_to_session(client):
    c, _ = client
    c._session.request = MagicMock(return_value=make_mock_response(200))
    c._graph_get_text("https://example.com/file")
    _, kwargs = c._session.request.call_args
    assert kwargs.get("timeout") == 30


def test_custom_timeout_used(mock_msal_app):
    with patch("msal.ConfidentialClientApplication", return_value=mock_msal_app):
        c = ConcreteGraphClient(timeout=60)
    assert c._timeout == 60
