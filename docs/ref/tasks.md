# Implementation Tasks — productboard-sync

Tasks are grouped by phase. Complete phases in order.

---

## Phase 1 — Project Scaffold

- [ ] Create full directory tree with all `__init__.py` files:
  `productboard_sync/`, `productboard_sync/productboard/`, `productboard_sync/storage/`,
  `productboard_sync/sync/`, `productboard_sync/utils/`, `tests/`, `tests/unit/`, `docs/`
- [ ] Create `pyproject.toml` with pytest config (`testpaths = ["tests"]`, `pythonpath = ["."]`)
- [ ] Create `requirements.txt`: `requests`, `pydantic>=2`, `pydantic-settings`, `python-dotenv`, `msal`
- [ ] Create `requirements-dev.txt`: `pytest`, `pytest-mock`, `responses`, `pytest-cov`
- [ ] Create `.env.example` documenting every variable from the configuration reference in `implementation-plan.md`
- [ ] Create `productboard_sync/config.py` using `pydantic-settings` `BaseSettings`:
  - Validate that backend-specific required vars are present (e.g., `LOCAL_OUTPUT_DIR` when `STORAGE_BACKEND=local`)
  - Expose a `get_settings()` cached singleton
  - `SYNC_ENTITIES` parses comma-separated string into `list[str]`; `"all"` expands to all known entity type names
- [ ] Create `productboard_sync/utils/logging.py`: configure root logger with format `%(asctime)s [%(levelname)s] %(name)s: %(message)s`; respect `LOG_LEVEL` from settings

---

## Phase 2 — Productboard API Client

- [ ] Create `productboard_sync/productboard/models.py`:
  - `OwnerRef` — `id: str | None`, `email: str | None`
  - `TagRef` — `name: str`
  - `StatusRef` — `id: str | None`, `name: str | None`
  - `EntityFields` — all optional: `name`, `owner: OwnerRef`, `tags: list[TagRef]`, `status: StatusRef`, `timeframe`, `archived: bool`; plus `extra_fields: dict[str, Any]` to capture custom/workspace-specific fields
  - `Entity` — `id`, `type`, `fields: EntityFields`, `relationships`, `links`, `createdAt`, `updatedAt`
  - `NoteContentMessage` — `externalId`, `content`, `authorName`, `authorType`, `timestamp` (for conversationNote)
  - `NoteFields` — `name`, `content: str | list[NoteContentMessage]`, `tags`, `owner`, `creator`, `processed: bool`, `archived: bool`
  - `Note` — `id`, `type`, `fields: NoteFields`, `relationships`, `createdAt`, `updatedAt`
  - `Member` — `id`, `name`, `email`, `role`, `disabled: bool`
  - `Team` — `id`, `name`, `handle`, `description`, `createdAt`, `updatedAt`
  - `EntityFieldConfig` — `id`, `name`, `type` (field type string)
  - `EntityConfiguration` — `type`, `fields: list[EntityFieldConfig]`
  - `PaginatedResponse[T]` — generic: `data: list[T]`, `links_next: str | None` (alias from `links.next`)

- [ ] Create `productboard_sync/utils/retry.py`:
  - `retry_on_rate_limit(max_retries=5)` decorator
  - On `HTTP 429`: sleep `2 ** attempt` seconds and retry
  - On other non-2xx: call `response.raise_for_status()` immediately
  - Logs each retry attempt at DEBUG level

- [ ] Create `productboard_sync/productboard/paginator.py`:
  - `paginate(session, method, url, params=None, json_body=None)` generator
  - Yields each item from `response["data"]` across all pages
  - Follows `response["links"]["next"]` — extracts `pageCursor` value from the URL
  - For POST: re-sends the same `json_body` on each subsequent page with `?pageCursor=` as a query param (not in body)
  - Stops when `links.next` is `null`

- [ ] Create `productboard_sync/productboard/client.py` — `ProductboardClient`:
  - `__init__(api_key: str)`: create `requests.Session` with `Authorization: Bearer {api_key}` and `Content-Type: application/json`
  - `search_entities(types: list[str]) -> Iterator[Entity]`: paginates `POST /v2/entities/search` with `{"data": {"filter": {"type": types}}}`
  - `list_notes() -> Iterator[Note]`: paginates `GET /v2/notes`
  - `list_members() -> Iterator[Member]`: paginates `GET /v2/members`
  - `list_teams() -> Iterator[Team]`: paginates `GET /v2/teams`
  - `get_entity_configuration(entity_type: str) -> EntityConfiguration`: `GET /v2/entities/configurations/{type}`
  - All HTTP calls wrapped with `@retry_on_rate_limit`

---

## Phase 3 — Storage Backends

- [ ] Create `productboard_sync/storage/base.py` — `StorageBackend` ABC:
  - `write_file(path: str, content: str) -> None`
  - `read_file(path: str) -> str`
  - `list_files(prefix: str = "") -> list[str]`
  - `delete_file(path: str) -> None`

- [ ] Create `productboard_sync/storage/local.py` — `LocalStorageBackend(StorageBackend)`:
  - Constructor: `output_dir: Path`
  - `write_file`: creates parent dirs via `mkdir(parents=True, exist_ok=True)`, writes UTF-8
  - `read_file`: reads UTF-8; raises `FileNotFoundError` if missing
  - `list_files(prefix)`: returns relative path strings under `output_dir` matching prefix
  - `delete_file`: removes file; silent if already missing

- [ ] Create `productboard_sync/storage/onedrive.py` — `OneDriveStorageBackend(StorageBackend)`:
  - Constructor: `tenant_id`, `client_id`, `client_secret`, `folder_id`
  - Auth: MSAL `ConfidentialClientApplication`, scope `https://graph.microsoft.com/.default`, client credentials flow; cache token and refresh when within 5 minutes of expiry
  - `write_file(path, content)`: `PUT https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}:/{path}:/content` with `Content-Type: text/csv; charset=utf-8`
  - `read_file(path)`: `GET` same URL pattern
  - `list_files(prefix)`: `GET /v1.0/me/drive/items/{folder_id}/children`, filter by name prefix
  - `delete_file(path)`: resolve item ID via list then `DELETE /v1.0/me/drive/items/{item_id}`

- [ ] Create `productboard_sync/storage/sharepoint.py` — `SharePointStorageBackend(StorageBackend)`:
  - Constructor: `tenant_id`, `client_id`, `client_secret`, `site_id`, `drive_id`, `folder_id`
  - Same MSAL auth pattern as OneDrive backend
  - All Graph API paths use `/sites/{site_id}/drives/{drive_id}/items/{folder_id}:/{path}:/content` instead of `/me/drive/...`
  - Consider extracting a shared `_GraphStorageBase` mixin to avoid duplicating auth + token refresh logic

- [ ] Update `config.py` to instantiate the correct backend from `STORAGE_BACKEND` and inject all required params

---

## Phase 4 — Sync Engine

- [ ] Create `productboard_sync/sync/fields.py` — `FieldDiscovery`:
  - `get_columns(entity_type: str) -> list[tuple[str, str]]`: returns ordered `(field_id, display_name)` list
  - Calls `client.get_entity_configuration(entity_type)` once per type and caches result
  - Standard fields come first in a fixed order (`name`, `status`, `owner`, `tags`, `timeframe`, `archived`)
  - Custom fields appended after, sorted by display name for stable column ordering

- [ ] Create `productboard_sync/sync/transformers.py` — pure functions (no I/O, deterministic):
  - `entities_to_csv(entities: list[Entity], columns: list[tuple[str, str]]) -> str`:
    - Uses `csv.DictWriter` with `extrasaction='ignore'`
    - Column headers = display names from `columns`
    - Maps each entity's standard fields + `extra_fields` dict to the column IDs
    - Multi-value fields (tags, teams): join with ` | ` separator
    - Returns empty-row CSV (header only) if `entities` is empty
  - `notes_to_csv(notes: list[Note]) -> str`:
    - Fixed columns: `id`, `type`, `name`, `content`, `owner`, `creator`, `tags`, `processed`, `archived`, `linked_features`, `createdAt`, `updatedAt`
    - `content`: for conversationNote, join messages as `{authorName}: {content}` separated by ` | `
    - `linked_features`: IDs of linked feature relationships, joined with ` | `
  - `members_to_csv(members: list[Member]) -> str`: fixed columns `id`, `name`, `email`, `role`, `disabled`
  - `teams_to_csv(teams: list[Team]) -> str`: fixed columns `id`, `name`, `handle`, `description`, `createdAt`, `updatedAt`

- [ ] Create `productboard_sync/sync/runner.py` — `SyncRunner`:
  - Constructor: `client: ProductboardClient`, `backend: StorageBackend`
  - `run(entity_types: list[str], dry_run: bool) -> None`
  - Entity type routing:
    - Entity types (`feature`, `subfeature`, etc.): call `search_entities([type])`, discover columns, call `entities_to_csv`; output filename = `{type_snake_case}.csv`
    - `notes`: call `list_notes()`, call `notes_to_csv`; output = `notes.csv`
    - `members`: call `list_members()`, call `members_to_csv`; output = `members.csv`
    - `teams`: call `list_teams()`, call `teams_to_csv`; output = `teams.csv`
  - If not `dry_run`: call `backend.write_file(filename, csv_content)`
  - Log: `Synced {count} {entity_type} records → {filename}` at INFO level
  - If a single entity type fails: log error with traceback at ERROR level, continue with remaining types

---

## Phase 5 — CLI Entry Point

- [ ] Create `productboard_sync/__main__.py`:
  - `argparse` arguments:
    - `--entity` (repeatable flag; e.g. `--entity features --entity notes`; default uses `SYNC_ENTITIES` config)
    - `--dry-run` flag
    - `--log-level {DEBUG,INFO,WARNING,ERROR}` (default: `INFO`)
  - Load `get_settings()`
  - Call `setup_logging(log_level)`
  - Instantiate `ProductboardClient(settings.productboard_api_key)`
  - Instantiate the correct `StorageBackend` from settings
  - Instantiate and call `SyncRunner(client, backend).run(entity_types, dry_run)`
  - On unhandled exception: log it and `sys.exit(1)`

---

## Phase 6 — Unit Tests

- [ ] Create `tests/conftest.py`:
  - `sample_entity_payload()` — returns a valid `Entity`-shaped dict (feature type, with standard fields)
  - `sample_note_payload(note_type="textNote")` — returns valid dict; supports `conversationNote` variant
  - `sample_member_payload()` — valid Member dict
  - `sample_team_payload()` — valid Team dict
  - `mock_responses` fixture — activates `responses` library mock for the test
  - `tmp_local_backend(tmp_path)` — `LocalStorageBackend` on a temp directory

- [ ] Create `tests/unit/test_models.py`:
  - Valid entity payload parses without error
  - Missing optional fields in `EntityFields` default to `None`
  - `conversationNote` content parses as `list[NoteContentMessage]`
  - `textNote` content parses as `str`
  - `PaginatedResponse[Entity]` correctly parses `data` list and `links.next`

- [ ] Create `tests/unit/test_retry.py`:
  - Decorated function succeeds on first call — no sleep
  - Function gets 429 twice then 200 — retried, sleep called with `1` then `2` seconds
  - Function gets 429 `max_retries` times — raises after exhausting retries
  - Non-429 4xx error is raised immediately without retry

- [ ] Create `tests/unit/test_paginator.py`:
  - Single page (`links.next = null`) yields all items and stops
  - Two-page response: second request includes correct `pageCursor` query param
  - Empty `data[]` on first page yields nothing
  - POST endpoint: body is re-sent on page 2; cursor is a query param not a body field

- [ ] Create `tests/unit/test_client.py`:
  - Every request has `Authorization: Bearer <key>` header
  - `search_entities(["feature"])` sends correct POST body with `type: ["feature"]`
  - `list_notes()` calls `GET /v2/notes`
  - `list_members()` calls `GET /v2/members`
  - `get_entity_configuration("feature")` calls correct URL and returns parsed model

- [ ] Create `tests/unit/test_local_storage.py`:
  - `write_file` creates nested directories if they don't exist
  - `write_file` overwrites an existing file
  - `read_file` returns correct UTF-8 content
  - `read_file` raises `FileNotFoundError` for missing path
  - `list_files("")` returns all relative paths
  - `delete_file` removes a file; calling again on missing path does not raise

- [ ] Create `tests/unit/test_fields.py`:
  - Returns standard fields first in correct fixed order
  - Custom fields appended after, sorted by display name
  - Result is cached — `get_entity_configuration` called only once for the same type
  - Unknown/empty configuration returns standard fields only

- [ ] Create `tests/unit/test_transformers.py`:
  - `entities_to_csv` first row equals the display names from `columns`
  - `entities_to_csv` includes all entity names in output
  - Multi-value tags joined with ` | `
  - Empty entities list returns header row only (no data rows)
  - `notes_to_csv` has a row for each note
  - conversationNote messages joined with ` | ` in the `content` column
  - Redacted owner (`"[redacted]"`) written as-is without error
  - `members_to_csv` and `teams_to_csv` have correct headers and row counts

- [ ] Create `tests/unit/test_sync_runner.py`:
  - Feature type routes to `search_entities` and writes `features.csv`
  - Notes type routes to `list_notes` and writes `notes.csv`
  - `dry_run=True` does not call `backend.write_file`
  - Failed fetch for one entity type logs error but other types still complete
  - Row count is logged at INFO level for each type

- [ ] Create `tests/unit/test_config.py`:
  - Missing `PRODUCTBOARD_API_KEY` raises `ValidationError`
  - Missing `STORAGE_BACKEND` raises `ValidationError`
  - `STORAGE_BACKEND=local` without `LOCAL_OUTPUT_DIR` raises `ValidationError`
  - `STORAGE_BACKEND=onedrive` without `ONEDRIVE_FOLDER_ID` raises `ValidationError`
  - `STORAGE_BACKEND=sharepoint` without `SHAREPOINT_SITE_ID` raises `ValidationError`
  - `SYNC_ENTITIES=all` expands to all known entity types

---

## Phase 7 — Documentation

- [ ] Create `README.md`:
  - One-paragraph purpose summary
  - Prerequisites: Python 3.11+; Azure app registration for OneDrive/SharePoint backend
  - Quickstart: 5 commands to get running with the local backend
  - Full environment variable reference table
  - Output files section: list all CSV filenames and key columns
  - Link to `docs/how-to-run.md` and `docs/how-to-deploy.md`

- [ ] Create `docs/how-to-run.md`:
  - Setting up venv with `uv`
  - Configuring `.env` for local backend
  - Configuring `.env` for OneDrive backend (step-by-step Azure app registration)
  - Configuring `.env` for SharePoint backend (how to find site ID, drive ID, folder ID using Graph Explorer)
  - Running a full sync: `python -m productboard_sync`
  - Running a subset: `--entity features --entity notes`
  - Dry run: `--dry-run`
  - Scheduling with cron (example crontab for daily 2am run)

- [ ] Create `docs/how-to-deploy.md`:
  - Prerequisites: Docker, Docker Compose
  - Building the image: `docker build -t productboard-sync .`
  - Running once with local backend (volume mount for output dir)
  - Running with OneDrive/SharePoint backend (env file)
  - Setting up daily scheduled sync with `docker-compose` (cron service config)
  - Viewing logs: `docker compose logs sync`
  - Updating: pull, rebuild, restart steps

---

## Phase 8 — Docker

- [ ] Create `.dockerignore`:
  `.venv/`, `__pycache__/`, `*.pyc`, `.env`, `.git/`, `tests/`, `*.md`, `*.csv`

- [ ] Create `Dockerfile`:
  - Stage 1 (builder): `python:3.12-slim`, install `uv`, copy `requirements.txt`, run `uv pip install --system -r requirements.txt`
  - Stage 2 (runtime): `python:3.12-slim`, copy installed packages from builder, copy `productboard_sync/` source
  - Create non-root user `appuser`; `USER appuser`
  - `ENTRYPOINT ["python", "-m", "productboard_sync"]`
  - `CMD ["--entity", "all"]`

- [ ] Create `docker-compose.yml`:
  - `sync` service: image built from `Dockerfile`, `env_file: .env`, volume mounts: one for output dir (local backend), one for any persistent state
  - `scheduler` service: lightweight cron container (e.g., `mcuadros/ofelia`) configured to run the `sync` service daily at 02:00
  - OR: single service with an entrypoint loop (`while true; do python -m productboard_sync; sleep 86400; done`) if a separate scheduler image is not desired
