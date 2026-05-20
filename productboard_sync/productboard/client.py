from __future__ import annotations

import logging
from collections.abc import Iterator

import requests

from ..utils.retry import retry_on_rate_limit
from .models import Entity, EntityConfiguration, Member, Note, Team
from .paginator import paginate

logger = logging.getLogger(__name__)

BASE_URL = "https://api.productboard.com/v2"


class ProductboardClient:
    def __init__(self, api_key: str, timeout: int = 30) -> None:
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    @retry_on_rate_limit()
    def _request(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json_body: dict | None = None,
    ):
        return self._session.request(method, url, params=params, json=json_body, timeout=self._timeout)

    def search_entities(self, types: list[str]) -> Iterator[Entity]:
        body = {"data": {"filter": {"type": types}}}
        for item in paginate(self._request, "POST", f"{BASE_URL}/entities/search", json_body=body):
            yield Entity.model_validate(item)

    def list_notes(self) -> Iterator[Note]:
        for item in paginate(self._request, "GET", f"{BASE_URL}/notes"):
            yield Note.model_validate(item)

    def list_members(self) -> Iterator[Member]:
        for item in paginate(self._request, "GET", f"{BASE_URL}/members"):
            yield Member.model_validate(item)

    def list_teams(self) -> Iterator[Team]:
        for item in paginate(self._request, "GET", f"{BASE_URL}/teams"):
            yield Team.model_validate(item)

    def get_entity_configuration(self, entity_type: str) -> EntityConfiguration:
        response = self._request("GET", f"{BASE_URL}/entities/configurations/{entity_type}")
        data = response.json()
        return EntityConfiguration.model_validate(data.get("data", data))
