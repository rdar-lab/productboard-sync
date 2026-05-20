from __future__ import annotations

import logging

import requests

from productboard_sync.config import ALL_ENTITY_TYPES
from productboard_sync.productboard.client import ProductboardClient
from productboard_sync.storage.base import StorageBackend

from . import transformers
from .fields import FieldDiscovery

logger = logging.getLogger(__name__)

_NON_ENTITY_TYPES = {"notes", "members", "teams"}
ENTITY_TYPES = [t for t in ALL_ENTITY_TYPES if t not in _NON_ENTITY_TYPES]

ENTITY_FILENAME_MAP = {
    "feature": "features.csv",
    "subfeature": "subfeatures.csv",
    "component": "components.csv",
    "product": "products.csv",
    "initiative": "initiatives.csv",
    "objective": "objectives.csv",
    "keyResult": "key_results.csv",
    "release": "releases.csv",
    "releaseGroup": "release_groups.csv",
}


class SyncRunner:
    def __init__(self, client: ProductboardClient, backend: StorageBackend) -> None:
        self._client = client
        self._backend = backend
        self._fields = FieldDiscovery(client)

    def run(self, entity_types: list[str], dry_run: bool = False) -> None:
        failed = []
        for entity_type in entity_types:
            try:
                self._sync_one(entity_type, dry_run)
            except requests.exceptions.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 400:
                    logger.warning("Entity type %s is not supported in this workspace — skipping", entity_type)
                else:
                    logger.error("Failed to sync %s", entity_type, exc_info=True)
                    failed.append(entity_type)
            except Exception:
                logger.error("Failed to sync %s", entity_type, exc_info=True)
                failed.append(entity_type)
        if failed:
            raise RuntimeError(f"Sync failed for entity type(s): {failed}")

    def _sync_one(self, entity_type: str, dry_run: bool) -> None:
        if entity_type in ENTITY_TYPES:
            columns = self._fields.get_columns(entity_type)
            csv_content, count = transformers.entities_to_csv(
                self._client.search_entities([entity_type]), columns
            )
            filename = ENTITY_FILENAME_MAP[entity_type]
        elif entity_type == "notes":
            csv_content, count = transformers.notes_to_csv(self._client.list_notes())
            filename = "notes.csv"
        elif entity_type == "members":
            csv_content, count = transformers.members_to_csv(self._client.list_members())
            filename = "members.csv"
        elif entity_type == "teams":
            csv_content, count = transformers.teams_to_csv(self._client.list_teams())
            filename = "teams.csv"
        else:
            logger.warning("Unknown entity type: %s — skipping", entity_type)
            return

        if dry_run:
            logger.info("[dry-run] Would write %d %s records -> %s", count, entity_type, filename)
            return

        self._backend.write_file(filename, csv_content)
        logger.info("Synced %d %s records -> %s", count, entity_type, filename)
