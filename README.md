# Items Service API (Minimal)

FastAPI service for items with Firestore storage and Vertex AI Search integration.

## Quick Run

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## Deploy (Cloud Run)

```powershell
& .\scripts\deploy_cloud_run.ps1 -ProjectId sphereless -Region us-central1 -ServiceName items-service-v2 -VertexDataStoreId items-datastore-v3
```

## API Endpoints

- `GET /health`
- `POST /api/v1/items`
- `GET /api/v1/items/{item_id}`
- `PATCH /api/v1/items/{item_id}`
- `DELETE /api/v1/items/{item_id}`
- `GET /api/v1/items?limit=50`
- `GET /api/v1/items/paged?page=1&page_size=20`
- `GET /api/v1/items/search/fuzzy?q=keyword&limit=10`
- `GET /api/v1/items/search/keyword?q=keyword&page_size=10`

## Keyword Search Response (Important)

Each row includes:
- `id`
- `title`
- `snippet`
- `score`
- `score_breakdown`
- `source`
- `item` (full item payload merged from Firestore)

Diagnostic headers:
- `X-Search-Backend`: `vertex` | `fallback_vertex_empty` | `fallback_vertex_error`
- `X-Search-Result-Count`

## Auto Sync

This service now auto-syncs Vertex docs when item APIs are called:
- Create item -> upsert Vertex doc
- Update item -> upsert Vertex doc
- Delete item -> delete Vertex doc

## Manual Sync (Optional)

```powershell
& .\scripts\run_items_vertex_sync.ps1 -ProjectId sphereless -Location global -DatastoreId items-datastore-v3 -Collection items_catalog_v2 -IncludeContent
```

## Remove Seeded Test Data

Integration seed cleanup:

```powershell
.\.venv\Scripts\python.exe .\scripts\cleanup_seed_items.py --base-url https://items-service-v2-83689773481.us-central1.run.app --source integration_seed_v1
```

Bulk seed cleanup:

```powershell
.\.venv\Scripts\python.exe .\scripts\cleanup_bulk_seed_items.py --base-url https://items-service-v2-83689773481.us-central1.run.app --source bulk_seed_sync_test_v1
```
