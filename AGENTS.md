# AGENTS.md — Guide for AI Agent Maintainers

This document is for AI agents (and humans acting in that capacity) who need to modify, extend, or debug this codebase. It covers the architecture, key invariants, conventions, and common failure modes that are not obvious from reading the code alone.

---

## Architecture overview

The system has four layers:

```
__main__.py              CLI entry point — parses args, wires everything together
config.py                Settings (pydantic-settings), validation, backend factory
productboard/            API client — HTTP, pagination, models, rate-limit retry
sync/                    Orchestration — field discovery, transform, write
storage/                 Storage backends — local filesystem, OneDrive, SharePoint
utils/                   Retry decorator, logging setup
```

Each run is a full rewrite of every requested entity type. There is no incremental state, no change detection, no delta tracking. Every CSV is overwritten on every run.

---

## Module responsibilities

### `productboard_sync/__main__.py`

- Parses CLI args (argparse)
- Defers all imports until after arg parsing — keeps `--help` fast
- Validates `--entity` values against `ALL_ENTITY_TYPES` before any API call
- `"all"` expands to `ALL_ENTITY_TYPES`; if no `--entity` flag, falls back to `settings.sync_entities`
- On any unhandled exception, logs it and calls `sys.exit(1)` — callers (cron, Docker) get a non-zero exit code

### `productboard_sync/config.py`

- `ALL_ENTITY_TYPES`: single source of truth for every valid entity type name. The runner derives its own `ENTITY_TYPES` from this list by filtering out non-entity types. The CLI validates against this list. Do not add entity types anywhere else.
- `Settings`: pydantic-settings model that reads from `.env` and env vars. Has two-stage validation: field-level validators (parse, normalize) then a model-level validator that checks backend completeness.
- `get_settings()`: `@lru_cache` — returns the same instance for the lifetime of the process. Tests must call `get_settings.cache_clear()` after each test (see `tests/conftest.py`).
- `get_storage_backend()`: factory that constructs the right backend from settings. Add new backends here.

### `productboard_sync/productboard/client.py`

- Thin wrapper around the Productboard REST API v2.
- `search_entities(types)` → `POST /v2/entities/search` — yields `Entity` objects
- `list_notes()` → `GET /v2/notes` — yields `Note` objects
- `list_members()` → `GET /v2/members` — yields `Member` objects
- `list_teams()` → `GET /v2/teams` — yields `Team` objects
- `get_entity_configuration(type)` → `GET /v2/entities/configurations/{type}` — returns `EntityConfiguration`
- All list methods are generators that page through the cursor-based API automatically.
- `timeout` is set on every `session.request()` call; it is not set on the session itself (no persistent default).

### `productboard_sync/productboard/paginator.py`

- Handles cursor-based pagination for both GET and POST endpoints.
- Reads `links.next` from the response envelope to determine whether another page exists.
- Yields raw dicts from `data[]`; callers parse them into models.

### `productboard_sync/productboard/models.py`

- Pydantic v2 models: `Entity`, `Note`, `Member`, `Team`, `EntityConfiguration`, `EntityField`, `Relationship`, `RelationshipTarget`.
- All models use `model_config = ConfigDict(extra="ignore")` — unknown fields from the API are silently dropped, not raised.
- `relationships` fields are `Optional[list[Relationship]]`, not `Optional[Any]`. Do not revert to `Any`.

### `productboard_sync/sync/fields.py`

- `FieldDiscovery.get_columns(entity_type)`: calls `get_entity_configuration()`, returns `list[tuple[field_id, display_name]]`.
- Columns always start with the four fixed fields: `id`, `type`, `createdAt`, `updatedAt`.

### `productboard_sync/sync/transformers.py`

- Four functions: `entities_to_csv`, `notes_to_csv`, `members_to_csv`, `teams_to_csv`.
- All accept `Iterable[...]` (not `list[...]`) — they stream records from the generator, writing to a `csv.writer` backed by `io.StringIO`.
- All return `(str, int)` — the CSV content and the record count. The runner uses the count for logging.
- Do not change these to accept or return lists — streaming keeps peak memory proportional to one record, not one page.

### `productboard_sync/sync/runner.py`

- `SyncRunner.run(entity_types, dry_run)`: iterates over entity types, calls `_sync_one` for each, collects failures, raises `RuntimeError` at the end if any failed.
- Continues past failures — if `feature` fails, `notes` still runs. The process exits non-zero because the exception propagates to `__main__.py`.
- Unknown entity types log a warning and return — they do not raise.
- `ENTITY_TYPES` is derived from `ALL_ENTITY_TYPES` by filtering out `_NON_ENTITY_TYPES = {"notes", "members", "teams"}`. It must not be a static list.

### `productboard_sync/storage/base.py`

- `StorageBackend` ABC with four methods: `write_file`, `read_file`, `list_files`, `delete_file`.
- All paths are relative filenames (e.g. `"features.csv"`). Backends are responsible for resolving them to their target location.

### `productboard_sync/storage/local.py`

- Writes to `LOCAL_OUTPUT_DIR`. Creates the directory if it does not exist.
- `_safe_path()` resolves paths and rejects anything that escapes the root via `Path.resolve().is_relative_to()`. This is a security control — do not remove it.

### `productboard_sync/storage/_graph_base.py`

- `GraphAuthMixin`: shared MSAL client credentials auth and Graph API request helpers.
- `_init_auth(tenant_id, client_id, client_secret, timeout)`: sets up the MSAL app and a `requests.Session`.
- `_get_token()`: acquires a token, caches it, refreshes 60 seconds before expiry.
- `_graph_request(method, url, **kwargs)`: sends a request with auth header and timeout; decorated with `@retry_on_rate_limit()`.
- `_graph_put(url, content)`: PUT with `text/csv; charset=utf-8` content-type.
- `_graph_get_text(url)`: GET, returns `response.text`.
- `_graph_list_children(url)`: GET with automatic `@odata.nextLink` pagination.
- `_graph_delete(url)`: DELETE; silently ignores 404, raises on everything else.

### `productboard_sync/storage/onedrive.py`

- URL pattern: `/drives/{drive_id}/items/{folder_id}:/{filename}:/content`
- Uses `drive_id` — **not** `/me/drive/`. `/me/drive/` is a delegated-auth path and fails with app-only client credentials. Do not revert this.

### `productboard_sync/storage/sharepoint.py`

- URL pattern: `/drives/{drive_id}/items/{folder_id}:/{filename}:/content`
- Same `drive_id` pattern as OneDrive — app-only auth.

### `productboard_sync/utils/retry.py`

- `@retry_on_rate_limit(max_retries=5)`: wraps functions that return a `requests.Response`.
- On 429, reads `Retry-After` header (int seconds); falls back to `2 ** attempt`.
- `Retry-After` parsing is wrapped in `try/except (ValueError, TypeError)` — non-integer header values fall back to exponential backoff silently.
- Does **not** sleep on the last attempt (attempt `max_retries - 1`); just continues and raises `RuntimeError` on exhaustion.

---

## Key invariants — do not break these

1. **`ALL_ENTITY_TYPES` is the single source of truth.** The CLI validates against it; the config validates against it; the runner derives its entity set from it. Adding a new entity type means adding it here and nowhere else to get validation coverage.

2. **Transformers accept iterables and return `(str, int)`.** They must not materialize the full list. The runner passes an API generator directly to the transformer; the transformer streams it.

3. **`ENTITY_TYPES` in `runner.py` is derived, not static.** `[t for t in ALL_ENTITY_TYPES if t not in _NON_ENTITY_TYPES]`. A static list would silently get out of sync with `ALL_ENTITY_TYPES`.

4. **OneDrive and SharePoint backends use `/drives/{drive_id}/...`**, not `/me/drive/...`. The `/me/drive/` path is for delegated (user) auth and will return 403 with client credentials. This was a deliberate fix.

5. **Container name `productboard-sync` must match across `docker-compose.yml` and `ofelia.ini`.** `docker-compose.yml` sets `container_name: productboard-sync`; `ofelia.ini` references it. Renaming one without the other silently breaks the schedule.

6. **`get_settings()` is `@lru_cache`.** In tests, always call `get_settings.cache_clear()` in teardown (the `clear_settings_cache` autouse fixture in `tests/conftest.py` does this). Not clearing it causes test pollution — a test that sets env vars will leak its settings into the next test.

7. **`sys.exit(1)` on any sync failure.** `__main__.py` catches all exceptions and calls `sys.exit(1)`. The cron scheduler and Docker healthchecks depend on a non-zero exit code to detect failure.

---

## Code conventions

- **No comments.** Only add a comment when the why is non-obvious (a hidden constraint, a workaround, a subtle invariant). "What" comments and task-reference comments are never written.
- **No docstrings.** Module and class docstrings are not written. Function signatures and names are self-documenting.
- **No premature abstraction.** Three similar lines is better than a helper. Don't design for hypothetical future use cases.
- **No error handling for impossible scenarios.** Only validate at system boundaries (user input, external APIs). Don't add fallbacks for internal code that can't fail.
- **Pydantic v2 syntax.** `model_config = ConfigDict(...)`, not `class Config`. `@field_validator(..., mode="before")`, not `@validator`.

---

## Adding a new entity type

Entity types that go through `POST /v2/entities/search` (the "search entities" path):

1. Add the type name to `ALL_ENTITY_TYPES` in `config.py`.
2. Add it to `ENTITY_FILENAME_MAP` in `runner.py`.
3. The runner will automatically pick it up via `ENTITY_TYPES = [t for t in ALL_ENTITY_TYPES if t not in _NON_ENTITY_TYPES]`.
4. Field discovery runs automatically via `FieldDiscovery.get_columns()`.
5. Add the new CSV to the output table in `README.md`.

Entity types that use a dedicated endpoint (like `notes`, `members`, `teams`):

1. Add the type name to `ALL_ENTITY_TYPES` in `config.py`.
2. Add it to `_NON_ENTITY_TYPES` in `runner.py`.
3. Add a new client method in `client.py` that yields the appropriate model.
4. Add a new transformer function in `transformers.py` that returns `(str, int)`.
5. Add a new `elif entity_type == "..."` branch in `SyncRunner._sync_one()`.
6. Add the new Pydantic model to `models.py` if needed.
7. Add tests for the transformer and the runner branch.

---

## Adding a new storage backend

1. Add a new file in `productboard_sync/storage/` that subclasses `StorageBackend`.
2. Implement all four abstract methods: `write_file`, `read_file`, `list_files`, `delete_file`.
3. Add any required env vars to `Settings` in `config.py` (optional fields, validated in `validate_backend_config`).
4. Add the backend name to the `validate_backend_config` model validator.
5. Add an `if backend == "..."` branch in `get_storage_backend()`.
6. Add the new variables to `.env.example` and the README configuration table.

---

## Running tests

```bash
# Install dev dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run all tests
pytest

# With coverage
pytest --cov=productboard_sync --cov-report=term-missing

# Run a specific test file
pytest tests/unit/test_sync_runner.py -v
```

All tests are unit tests under `tests/unit/`. There are no integration tests. HTTP is mocked via the `responses` library (for Productboard API tests) and via `unittest.mock.MagicMock` patching `session.request` (for Graph API tests).

The `autouse` fixture `clear_settings_cache` in `tests/conftest.py` calls `get_settings.cache_clear()` after every test. Do not remove it.

---

## Deployment architecture

The Docker setup has two services:

- **`productboard-sync`** (`container_name: productboard-sync`): runs `python -m productboard_sync` and exits. It is not long-running.
- **`scheduler`**: runs `mcuadros/ofelia:v0.3.22`, reads `ofelia.ini`, and executes the sync container on a cron schedule.

Ofelia triggers a job by running a command inside the named container. The container name is hardcoded in both `docker-compose.yml` (`container_name: productboard-sync`) and `ofelia.ini` (`container = productboard-sync`). They must match.

The sync container is not a daemon — it runs, writes files, and exits. Ofelia starts it on schedule.

Do not upgrade `mcuadros/ofelia` beyond `v0.3.22` without verifying the job configuration format is unchanged.

---

## Known historical gotchas

These are bugs that were fixed. Do not reintroduce them.

**`/me/drive/` in OneDrive backend**: The original code used `/me/drive/items/{folder_id}:/` which works for delegated auth but returns 403 with app-only (client credentials) auth. Fixed to `/drives/{drive_id}/items/{folder_id}:/`. The `ONEDRIVE_DRIVE_ID` env var is now required.

**`Retry-After` header crash**: The original retry decorator did `wait = int(response.headers.get("Retry-After", 2 ** attempt))` — if the header contained a non-integer string (e.g. an HTTP date), `int()` would raise. Fixed with `try/except (ValueError, TypeError)`.

**`get_settings()` test pollution**: The original test suite did not clear the `@lru_cache` between tests. Tests that patched env vars leaked their `Settings` instance into subsequent tests. Fixed with the `clear_settings_cache` autouse fixture.

**Runner swallowing failures silently**: The original `runner.run()` caught exceptions and logged them but did not raise and did not cause a non-zero exit. Cron would report success even after a complete failure. Fixed: all failures are collected, and a `RuntimeError` is raised after all entity types are attempted.

**`Relationships` typed as `Any`**: The original `Entity.relationships` and `Note.relationships` were `Optional[Any]`. This silently accepted arbitrary data structures and made the field unusable for callers. Fixed to `Optional[list[Relationship]]`.

**No sleep on last retry attempt**: The original retry loop slept before the last attempt, then raised — wasting one sleep interval on an attempt that would never succeed. Fixed by gating the sleep on `attempt < max_retries - 1`.
