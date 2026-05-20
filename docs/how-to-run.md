# How to run

## Environment setup

### Using venv + pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### Using venv + uv

```bash
python -m venv .venv
source .venv/bin/activate
pip install uv
uv pip install -r requirements.txt -r requirements-dev.txt
```

## Local backend example

```env
PRODUCTBOARD_API_KEY=pb_xxx
STORAGE_BACKEND=local
LOCAL_OUTPUT_DIR=./output
SYNC_ENTITIES=all
LOG_LEVEL=INFO
```

Run a full sync:

```bash
python -m productboard_sync
```

## OneDrive backend setup summary

1. Create an Azure app registration.
2. Generate a client secret.
3. Add Microsoft Graph application permission `Files.ReadWrite.All`.
4. Grant admin consent.
5. Find the drive ID: `GET https://graph.microsoft.com/v1.0/users/{userId}/drives` or `GET https://graph.microsoft.com/v1.0/drives`
6. Find the target folder item ID within that drive.
7. Configure:

```env
PRODUCTBOARD_API_KEY=pb_xxx
STORAGE_BACKEND=onedrive
ONEDRIVE_TENANT_ID=tenant-id
ONEDRIVE_CLIENT_ID=client-id
ONEDRIVE_CLIENT_SECRET=client-secret
ONEDRIVE_DRIVE_ID=drive-id
ONEDRIVE_FOLDER_ID=folder-item-id
```

## SharePoint backend setup summary

1. Reuse or create an Azure app registration with Graph application access.
2. Find the site ID:
   - `GET https://graph.microsoft.com/v1.0/sites?search=your-site`
3. Find the drive ID:
   - `GET https://graph.microsoft.com/v1.0/sites/{site-id}/drives`
4. Find the destination folder item ID inside that drive.
5. Configure:

```env
PRODUCTBOARD_API_KEY=pb_xxx
STORAGE_BACKEND=sharepoint
ONEDRIVE_TENANT_ID=tenant-id
ONEDRIVE_CLIENT_ID=client-id
ONEDRIVE_CLIENT_SECRET=client-secret
SHAREPOINT_SITE_ID=site-id
SHAREPOINT_DRIVE_ID=drive-id
SHAREPOINT_FOLDER_ID=folder-id
```

## Common commands

Full sync:

```bash
python -m productboard_sync
```

Subset sync:

```bash
python -m productboard_sync --entity feature --entity notes
```

Dry run:

```bash
python -m productboard_sync --dry-run --entity members
```

## Cron example

Run daily at 2am:

```cron
0 2 * * * cd /path/to/productboard-sync && . .venv/bin/activate && python -m productboard_sync >> sync.log 2>&1
```
