# productboard-sync

Syncs all Productboard REST API v2 data into CSV files and writes the results to a local folder, OneDrive, or SharePoint. Each run is a full rewrite of every selected dataset — no incremental state, no stale data.

Designed for teams that need to expose Productboard data to product managers or AI tools without distributing admin-level API keys.

---

## Prerequisites

- Python 3.12
- A Productboard API token (Settings → Integrations → API)
- For OneDrive or SharePoint: an Azure app registration with `Files.ReadWrite.All` (application permission, admin-consented)

---

## Quickstart (local backend)

```bash
git clone <repo-url> productboard-sync && cd productboard-sync
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in PRODUCTBOARD_API_KEY and LOCAL_OUTPUT_DIR
python -m productboard_sync
```

CSVs are written to `LOCAL_OUTPUT_DIR`. Run `--dry-run` to verify config without writing anything.

---

## CLI reference

```
python -m productboard_sync [OPTIONS]

Options:
  --entity ENTITY     Entity type to sync (repeatable). Pass "all" or omit to use SYNC_ENTITIES config.
  --dry-run           Fetch and transform but do not write to storage.
  --log-level LEVEL   DEBUG | INFO | WARNING | ERROR (default: INFO or LOG_LEVEL env var).
```

Examples:

```bash
python -m productboard_sync                              # sync everything
python -m productboard_sync --entity feature --entity notes
python -m productboard_sync --entity all --dry-run
```

---

## Output files

Each CSV is a full rewrite on every run. Standard columns (`id`, `type`, `createdAt`, `updatedAt`) are always present; entity CSVs also include your workspace's custom fields discovered dynamically from the API.

| File | Source | Fixed columns |
|---|---|---|
| `features.csv` | `POST /v2/entities/search` | id, type, createdAt, updatedAt + dynamic fields |
| `subfeatures.csv` | `POST /v2/entities/search` | id, type, createdAt, updatedAt + dynamic fields |
| `components.csv` | `POST /v2/entities/search` | id, type, createdAt, updatedAt + dynamic fields |
| `products.csv` | `POST /v2/entities/search` | id, type, createdAt, updatedAt + dynamic fields |
| `initiatives.csv` | `POST /v2/entities/search` | id, type, createdAt, updatedAt + dynamic fields |
| `objectives.csv` | `POST /v2/entities/search` | id, type, createdAt, updatedAt + dynamic fields |
| `key_results.csv` | `POST /v2/entities/search` | id, type, createdAt, updatedAt + dynamic fields |
| `releases.csv` | `POST /v2/entities/search` | id, type, createdAt, updatedAt + dynamic fields |
| `release_groups.csv` | `POST /v2/entities/search` | id, type, createdAt, updatedAt + dynamic fields |
| `notes.csv` | `GET /v2/notes` | id, type, name, content, owner, creator, tags, processed, archived, linked_features, createdAt, updatedAt |
| `members.csv` | `GET /v2/members` | id, name, email, role, disabled |
| `teams.csv` | `GET /v2/teams` | id, name, handle, description, createdAt, updatedAt |

---

## Configuration

Copy `.env.example` to `.env` and fill in the values for your chosen backend.

### All backends

| Variable | Required | Default | Description |
|---|---|---|---|
| `PRODUCTBOARD_API_KEY` | Yes | — | Productboard API token |
| `STORAGE_BACKEND` | Yes | — | `local`, `onedrive`, or `sharepoint` |
| `SYNC_ENTITIES` | No | `all` | `all` or comma-separated list (e.g. `feature,notes,members`) |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `REQUEST_TIMEOUT` | No | `30` | HTTP request timeout in seconds for all API calls |

### Local backend

| Variable | Required | Description |
|---|---|---|
| `LOCAL_OUTPUT_DIR` | Yes | Absolute or relative path to the output folder |

### OneDrive backend

Uses app-only auth (client credentials). The app must have the `Files.ReadWrite.All` **application** permission (not delegated) granted by an admin.

| Variable | Required | Description |
|---|---|---|
| `ONEDRIVE_TENANT_ID` | Yes | Azure AD tenant ID |
| `ONEDRIVE_CLIENT_ID` | Yes | Azure app (service principal) client ID |
| `ONEDRIVE_CLIENT_SECRET` | Yes | Azure app client secret |
| `ONEDRIVE_DRIVE_ID` | Yes | OneDrive drive ID (use Graph Explorer: `GET /v1.0/drives` or `GET /v1.0/users/{userId}/drives`) |
| `ONEDRIVE_FOLDER_ID` | Yes | Target folder item ID within that drive |

### SharePoint backend

| Variable | Required | Description |
|---|---|---|
| `ONEDRIVE_TENANT_ID` | Yes | Azure AD tenant ID |
| `ONEDRIVE_CLIENT_ID` | Yes | Azure app client ID |
| `ONEDRIVE_CLIENT_SECRET` | Yes | Azure app client secret |
| `SHAREPOINT_SITE_ID` | Yes | SharePoint site ID (`GET /v1.0/sites?search=<name>`) |
| `SHAREPOINT_DRIVE_ID` | Yes | Document library drive ID (`GET /v1.0/sites/{siteId}/drives`) |
| `SHAREPOINT_FOLDER_ID` | Yes | Target folder item ID within that drive |

---

## Deployment (Docker + daily schedule)

See [docs/how-to-deploy.md](docs/how-to-deploy.md) for full instructions. Quick reference:

```bash
# First-time setup
cp .env.example .env          # fill in your values
docker compose up -d --build scheduler

# View logs
docker compose logs -f sync

# Update after a code change
docker compose build --no-cache && docker compose up -d
```

The `scheduler` service (Ofelia) runs the sync daily at 02:00. The sync container is named `productboard-sync` — this name is hardcoded in `ofelia.ini` and `docker-compose.yml` and must not be changed without updating both files.

---

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest                        # run all tests
pytest --cov=productboard_sync --cov-report=term-missing   # with coverage
```

For detailed run and backend setup instructions see [docs/how-to-run.md](docs/how-to-run.md).
