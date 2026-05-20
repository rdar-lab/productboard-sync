# Implementation Plan — productboard-sync

## Problem Statement

Productboard API keys carry admin-level permissions, making it impractical to distribute them to all product managers. This tool solves that by running a centralized sync process that reads all Productboard data and writes it as **CSV files** to a shared storage location. PMs can open CSVs in Excel or feed them into any AI tool — without needing a Productboard account.

Data flow: **Productboard REST API → Python sync script → Storage backend (local folder / personal OneDrive / SharePoint)**

---

## Architecture

### Data Flow

```
Productboard REST API (v2)
        │
        ▼
ProductboardClient              ← auth, pagination, retry, field discovery
        │
        ▼
Pydantic Models                 ← typed, validated at the API boundary
        │
        ▼
SyncRunner                      ← orchestrates per-entity-type full sync
  └── Transformers              ← converts model lists → CSV strings
        │
        ▼
StorageBackend (abstract)
  ├── LocalStorageBackend       ← writes to a local folder
  ├── OneDriveStorageBackend    ← uploads via Graph API (/me/drive)
  └── SharePointStorageBackend  ← uploads via Graph API (/sites/{id}/drives/{id})
```

### Sync Strategy

**Full rewrite on every run.** Each execution fetches all records for every entity type, generates a fresh CSV, and overwrites the previous file. No incremental state tracking is needed. This maximises simplicity and correctness (no stale/deleted data in files).

### Module Structure

```
productboard_sync/
  __main__.py               # CLI entry point (argparse)
  config.py                 # Pydantic-settings: loads .env, validates, builds objects
  productboard/
    __init__.py
    client.py               # ProductboardClient: all API calls
    models.py               # Pydantic models for all entity types, notes, members
    paginator.py            # Cursor-based pagination generator
  storage/
    __init__.py
    base.py                 # Abstract StorageBackend (write_file, read_file, list_files, delete_file)
    local.py                # LocalStorageBackend
    onedrive.py             # OneDriveStorageBackend (personal /me/drive)
    sharepoint.py           # SharePointStorageBackend (/sites/{id}/drives/{id})
  sync/
    __init__.py
    runner.py               # SyncRunner: fetch → transform → write per entity type
    transformers.py         # Pure functions: list[Model] → CSV string
    fields.py               # Field discovery: fetches configurations and normalises column names
  utils/
    __init__.py
    retry.py                # retry_on_rate_limit decorator (exponential backoff)
    logging.py              # Structured logging setup
tests/
  conftest.py               # Shared fixtures
  unit/
    test_client.py
    test_models.py
    test_paginator.py
    test_retry.py
    test_local_storage.py
    test_transformers.py
    test_sync_runner.py
    test_fields.py
    test_config.py
docs/
  how-to-run.md
  how-to-deploy.md
.env.example
.dockerignore
Dockerfile
docker-compose.yml
pyproject.toml
requirements.txt
requirements-dev.txt
README.md
```

---

## Design Decisions

### StorageBackend abstraction
All sync logic writes through `StorageBackend.write_file(path: str, content: str)`. Three concrete backends: `local`, `onedrive` (personal `/me/drive`), `sharepoint` (organisation `/sites/{id}/drives/{id}`). Selected via `STORAGE_BACKEND` env var.

### CSV output format
One CSV file per entity type (e.g., `features.csv`, `notes.csv`, `initiatives.csv`). Columns are: standard fields first, then all custom/workspace-specific fields appended dynamically. The first row is always a header. Empty cells for fields not present on a given record.

### Dynamic field discovery
Entity fields in Productboard are workspace-specific. Before transforming, the runner calls `GET /v2/entities/configurations/{type}` to discover all available fields (standard + custom). These become the CSV column headers. This means the CSV schema automatically matches your workspace without code changes.

### All entity types
The following types are synced via `POST /v2/entities/search`:
`feature`, `subfeature`, `component`, `product`, `initiative`, `objective`, `keyResult`, `release`, `releaseGroup`

Plus separately:
- `notes` — via `GET /v2/notes` (includes textNote, conversationNote, opportunityNote)
- `members` — via `GET /v2/members`
- `teams` — via `GET /v2/teams`

Each entity type produces its own CSV file.

### Pydantic everywhere
Parse all API responses into Pydantic models at the client boundary. Never pass raw dicts into the sync/transform layer.

### Retry logic
`retry_on_rate_limit` decorator on all HTTP calls: on `HTTP 429`, sleep `2 ** attempt` seconds, retry up to 5 times. No `Retry-After` header from Productboard.

---

## Phase Breakdown

### Phase 1 — Project Scaffold
Set up directory structure, dependency files, configuration loading, `.env.example`.

Key outputs:
- All directories and `__init__.py` files
- `pyproject.toml` (pytest config: `testpaths`, `pythonpath`)
- `requirements.txt`: `requests`, `pydantic>=2`, `pydantic-settings`, `python-dotenv`, `msal`
- `requirements-dev.txt`: `pytest`, `pytest-mock`, `responses`, `pytest-cov`
- `.env.example` with all variables documented
- `config.py` using `pydantic-settings` `BaseSettings`; validates backend-specific required vars
- `utils/logging.py`: structured log format respecting `LOG_LEVEL`

### Phase 2 — Productboard API Client
Implement the HTTP client with full pagination, retry, and typed responses.

Key outputs:
- `productboard/models.py` — Pydantic models for `Entity`, `Note`, `Member`, `Team`, `Relationship`, `EntityConfiguration`, `PaginatedResponse[T]`
- `utils/retry.py` — `retry_on_rate_limit(max_retries=5)` decorator
- `productboard/paginator.py` — cursor-based pagination generator (supports both GET and POST endpoints)
- `productboard/client.py` — `ProductboardClient`:
  - `search_entities(types, page_cursor)` — `POST /v2/entities/search` (all entity types via this)
  - `list_notes(page_cursor)` — `GET /v2/notes`
  - `list_members(page_cursor)` — `GET /v2/members`
  - `list_teams(page_cursor)` — `GET /v2/teams`
  - `get_entity_configuration(entity_type)` — `GET /v2/entities/configurations/{type}`

### Phase 3 — Storage Backends
Implement the abstract interface and all three concrete backends.

Key outputs:
- `storage/base.py` — `StorageBackend` ABC: `write_file`, `read_file`, `list_files`, `delete_file`
- `storage/local.py` — `LocalStorageBackend`: writes UTF-8 files under `LOCAL_OUTPUT_DIR`
- `storage/onedrive.py` — `OneDriveStorageBackend`: MSAL client credentials, `PUT /me/drive/items/{folder_id}:/{name}:/content`
- `storage/sharepoint.py` — `SharePointStorageBackend`: MSAL client credentials, `PUT /sites/{site_id}/drives/{drive_id}/items/{folder_id}:/{name}:/content`; requires `SHAREPOINT_SITE_ID` and `SHAREPOINT_DRIVE_ID` in addition to folder ID

### Phase 4 — Sync Engine
Wire field discovery, transformation, and writing together.

Key outputs:
- `sync/fields.py` — `FieldDiscovery`: calls `get_entity_configuration` per type, caches results, returns ordered list of `(field_id, display_name)` tuples for use as CSV columns
- `sync/transformers.py` — pure functions (no I/O):
  - `entities_to_csv(entities: list[Entity], columns: list[tuple[str, str]]) -> str`
  - `notes_to_csv(notes: list[Note]) -> str`
  - `members_to_csv(members: list[Member]) -> str`
  - `teams_to_csv(teams: list[Team]) -> str`
  - Uses Python `csv.DictWriter` with `extrasaction='ignore'`
- `sync/runner.py` — `SyncRunner`:
  - Constructor takes `client`, `backend`
  - `run(entities: list[str], dry_run: bool)` — for each entity type: discover fields → fetch all pages → transform → write CSV
  - Log record count per type
  - If one type fails, log error and continue with the rest

### Phase 5 — CLI Entry Point
Key outputs:
- `__main__.py` with `argparse`:
  - `--entity` (repeatable, or `all`; default: `all`)
  - `--dry-run` flag
  - `--log-level` (default: `INFO`)
- Wires config → client → runner → storage

### Phase 6 — Unit Tests
Key outputs: full test suite for every module (see tasks.md for per-file test cases)

### Phase 7 — Documentation
Key outputs:
- `README.md` — overview, quickstart, env var reference, CSV format description
- `docs/how-to-run.md` — venv setup, each backend config, cron scheduling, how to find SharePoint site/drive IDs
- `docs/how-to-deploy.md` — Docker build, run, volume mounts, daily scheduling with `docker-compose`

### Phase 8 — Docker
Key outputs:
- `Dockerfile` — `python:3.12-slim`, install `uv`, non-root user, `ENTRYPOINT ["python", "-m", "productboard_sync"]`
- `docker-compose.yml` — `sync` service with `env_file`, volume for output dir; optional `scheduler` service running daily via `crond` or `ofelia`
- `.dockerignore`

---

## Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `PRODUCTBOARD_API_KEY` | ✅ | — | Productboard API token |
| `STORAGE_BACKEND` | ✅ | — | `local`, `onedrive`, or `sharepoint` |
| `LOCAL_OUTPUT_DIR` | local only | — | Absolute path to output folder |
| `ONEDRIVE_TENANT_ID` | onedrive/sharepoint | — | Azure AD tenant ID |
| `ONEDRIVE_CLIENT_ID` | onedrive/sharepoint | — | Azure app (service principal) client ID |
| `ONEDRIVE_CLIENT_SECRET` | onedrive/sharepoint | — | Azure app client secret |
| `ONEDRIVE_FOLDER_ID` | onedrive only | — | OneDrive folder item ID |
| `SHAREPOINT_SITE_ID` | sharepoint only | — | SharePoint site ID |
| `SHAREPOINT_DRIVE_ID` | sharepoint only | — | SharePoint document library drive ID |
| `SHAREPOINT_FOLDER_ID` | sharepoint only | — | Folder item ID within the drive |
| `SYNC_ENTITIES` | ❌ | `all` | Comma-separated entity types, or `all` |
| `LOG_LEVEL` | ❌ | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Entity Types and Output Files

| Entity type | API method | Output file |
|---|---|---|
| `feature` | `POST /v2/entities/search` | `features.csv` |
| `subfeature` | `POST /v2/entities/search` | `subfeatures.csv` |
| `component` | `POST /v2/entities/search` | `components.csv` |
| `product` | `POST /v2/entities/search` | `products.csv` |
| `initiative` | `POST /v2/entities/search` | `initiatives.csv` |
| `objective` | `POST /v2/entities/search` | `objectives.csv` |
| `keyResult` | `POST /v2/entities/search` | `key_results.csv` |
| `release` | `POST /v2/entities/search` | `releases.csv` |
| `releaseGroup` | `POST /v2/entities/search` | `release_groups.csv` |
| `notes` | `GET /v2/notes` | `notes.csv` |
| `members` | `GET /v2/members` | `members.csv` |
| `teams` | `GET /v2/teams` | `teams.csv` |

---

## Dependencies

### Runtime (`requirements.txt`)
| Package | Purpose |
|---|---|
| `requests` | HTTP client |
| `pydantic>=2` | Data validation and models |
| `pydantic-settings` | Config loading from env vars |
| `python-dotenv` | Load `.env` file |
| `msal` | Microsoft Graph auth (client credentials flow) |

### Dev (`requirements-dev.txt`)
| Package | Purpose |
|---|---|
| `pytest` | Test runner |
| `pytest-mock` | Mock fixtures |
| `responses` | Mock `requests` HTTP calls |
| `pytest-cov` | Coverage reporting |
