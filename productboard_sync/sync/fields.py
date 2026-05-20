from __future__ import annotations

import logging

from productboard_sync.productboard.client import ProductboardClient
from productboard_sync.productboard.models import EntityFieldConfig

logger = logging.getLogger(__name__)

STANDARD_FIELD_IDS = ["name", "status", "owner", "tags", "timeframe", "archived"]


class FieldDiscovery:
    def __init__(self, client: ProductboardClient) -> None:
        self._client = client
        self._cache: dict[str, list[tuple[str, str]]] = {}

    def get_columns(self, entity_type: str) -> list[tuple[str, str]]:
        if entity_type in self._cache:
            return self._cache[entity_type]

        try:
            config = self._client.get_entity_configuration(entity_type)
            all_fields: list[EntityFieldConfig] = config.fields
        except Exception:
            logger.warning("Could not fetch configuration for %s, using standard fields only", entity_type)
            all_fields = []

        standard = [(field_id, field_id) for field_id in STANDARD_FIELD_IDS]
        custom = sorted(
            [(field.id, field.name or field.id) for field in all_fields if field.id not in STANDARD_FIELD_IDS],
            key=lambda item: item[1].lower(),
        )

        columns = standard + custom
        self._cache[entity_type] = columns
        return columns
