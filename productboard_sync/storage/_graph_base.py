from __future__ import annotations

import logging
import time

import requests

from ..utils.retry import retry_on_rate_limit

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphAuthMixin:
    def _init_auth(self, tenant_id: str, client_id: str, client_secret: str, timeout: int = 30) -> None:
        import msal

        self._app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        self._timeout = timeout
        self._session = requests.Session()
        self._token: dict | None = None
        self._token_expiry: float = 0.0

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 300:
            return self._token["access_token"]
        result = self._app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in result:
            raise RuntimeError(f"MSAL token acquisition failed: {result.get('error_description')}")
        self._token = result
        self._token_expiry = time.time() + result.get("expires_in", 3600)
        return result["access_token"]

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    @retry_on_rate_limit()
    def _graph_request(self, method: str, url: str, **kwargs) -> requests.Response:
        headers = {**self._auth_headers(), **kwargs.pop("headers", {})}
        return self._session.request(method, url, headers=headers, timeout=self._timeout, **kwargs)

    def _graph_put(self, url: str, content: str) -> None:
        self._graph_request(
            "PUT", url,
            headers={"Content-Type": "text/csv; charset=utf-8"},
            data=content.encode("utf-8"),
        )

    def _graph_get_text(self, url: str) -> str:
        return self._graph_request("GET", url).text

    def _graph_list_children(self, url: str) -> list[dict]:
        items = []
        next_url: str | None = url
        while next_url:
            data = self._graph_request("GET", next_url).json()
            items.extend(data.get("value", []))
            next_url = data.get("@odata.nextLink")
        return items

    def _graph_delete(self, url: str) -> None:
        try:
            self._graph_request("DELETE", url)
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                return
            raise
