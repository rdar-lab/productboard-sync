# Copilot Instructions — productboard-sync

## Project Purpose

This tool syncs data from Productboard (notes/insights, features, etc.) into files on a configurable storage backend. The goal is to give product managers read-only access to Productboard data via shared files, so they can feed that data into any AI tool of their choice — without needing personal Productboard API keys (which carry admin-level permissions).

Data flow: **Productboard REST API → Python sync script → Storage backend (local folder or OneDrive)**

## Environment Setup

This project uses `venv` for virtual environments and `uv` for fast package installation.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

To add a new dependency:
```bash
uv pip install <package>
uv pip freeze > requirements.txt
```

## Running

```bash
# Run the full sync
python -m productboard_sync

# Run a specific sync target (once implemented)
python -m productboard_sync --entity features
python -m productboard_sync --entity notes
```

## Tests

```bash
# Full suite
pytest

# Single test file
pytest tests/test_productboard_client.py

# Single test by name
pytest -k "test_fetch_features"
```

## Architecture

```
productboard_sync/
  __main__.py          # Entry point; orchestrates sync runs
  config.py            # Loads env vars / config (API key, storage backend choice, paths)
  productboard/
    client.py          # Thin wrapper around the Productboard REST API
    models.py          # Pydantic models for Productboard entities
  storage/
    base.py            # Abstract StorageBackend interface
    local.py           # Writes files to a local folder
    onedrive.py        # Microsoft Graph API client for OneDrive/SharePoint uploads
  sync/
    runner.py          # Orchestrates fetch → transform → upload per entity type
    transformers.py    # Converts Productboard models into output file formats (Markdown/JSON)
tests/
```

> As the project grows, update this section to reflect the actual structure.

## Key Conventions

### Storage backends
The `StorageBackend` abstraction in `storage/base.py` is the extension point. All sync logic writes through this interface — never directly to a storage implementation. To add a new backend, subclass `StorageBackend` and register it in `config.py`. Select the backend via the `STORAGE_BACKEND` env var (`local` or `onedrive`).

### Credentials
Never hardcode API keys or tokens. Use a `.env` file locally (gitignored). Document all required variables in `.env.example`.

- **Always required**: `PRODUCTBOARD_API_KEY`, `STORAGE_BACKEND`
- **Local backend**: `LOCAL_OUTPUT_DIR` (path to the target folder)
- **OneDrive backend**: `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `GRAPH_TENANT_ID`, `ONEDRIVE_TARGET_FOLDER_ID`

### Models
Use Pydantic models for all external API responses — parse at the API boundary, pass typed models everywhere inside the codebase.

### Output format
Default to Markdown (`.md`) files for human + AI readability. Lists of entities (features, notes) use Markdown tables or YAML front matter + body.

### Productboard API

- **Base URL:** `https://api.productboard.com/v2` — versioning is in the URL path, **no `X-Version` header** (that was v1, now deprecated)
- **Auth:** `Authorization: Bearer <PRODUCTBOARD_API_KEY>` on every request
- **Key entity types:** `feature`, `subfeature`, `component`, `product`, `initiative`, `objective`, `keyResult`, `release` — all served by the unified `/v2/entities` endpoint
- **Notes types:** `textNote`, `conversationNote`, `opportunityNote`
- **Pagination:** cursor-based via `pageCursor` query param; follow `links.next` until it is `null`
- **Entity fields are workspace-specific** — use `GET /v2/entities/configurations/feature` to discover available fields; standard ones are `name`, `owner`, `tags`, `status`, `timeframe`, `archived`

#### Incremental sync — critical difference between entity types
- **Notes:** use `GET /v2/notes?updatedFrom=<ISO-8601>` — the simple list endpoint supports date filtering
- **Features/entities:** `GET /v2/entities` does **not** support `updatedAt` filtering; you **must** use `POST /v2/entities/search` with `{"data": {"filter": {"type": ["feature"], "updatedAt": {"from": "<ISO-8601>"}}}}` and pass `?pageCursor=` as a query param on subsequent pages (not in the body)

Store `last_synced_at` per entity type in `sync_state.json`.

#### Rate limits
HTTP `429` is returned when exceeded; no `Retry-After` header is provided. Use exponential backoff (`2 ** attempt` seconds). Specific numeric limits are not published — be conservative.

### Microsoft Graph API (OneDrive backend)
- **Base URL:** `https://graph.microsoft.com/v1.0`
- **Auth:** app-only via client credentials flow (unattended sync) — `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `GRAPH_TENANT_ID`
