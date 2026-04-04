# Items Service API Documentation

## 1. Overview

The Items Service is a FastAPI-based REST API for managing item records stored in Google Firestore, with integrated search capabilities via Vertex AI Search and local fuzzy fallback.

- Service name: items-service
- API version: v1
- OpenAPI title/version: Items Service / 1.0.0
- Primary data store: Google Firestore
- Search backends:
  - Vertex AI Search keyword search
  - Local fuzzy ranking fallback

## 2. Base URLs and API Surfaces

- Local development base URL: http://localhost:8080
- Versioned API base path: /api/v1
- Health endpoint: /health
- OpenAPI JSON: /openapi.json
- Swagger UI: /docs

## 3. Authentication and Authorization

No application-level authentication is currently enforced by this API.

Important: This does not imply the service is publicly accessible in all environments. Network- or platform-level access controls may still apply.

## 4. Common Data Types

### 4.1 Item Object

Field definitions:

- id: string, server-generated UUID
- title: string, required, min length 1, max length 300
- description: string or null, optional, max length 5000
- abstraction: string, required in create, max length 5000
- tags: array of string
- author_id: string or null
- author_name: string or null, max length 200
- source: string or null, max length 200
- url: string or null, max length 2000
- citations: array of string or null
- created_date: datetime (ISO-8601)
- updated_date: datetime (ISO-8601)

### 4.2 Pagination Metadata

- page: integer
- page_size: integer
- total: integer

### 4.3 Keyword Search Result

- id: string
- title: string
- snippet: string or null
- score: number or null
- score_breakdown: object or null
- item: full Item object or null
- source: string

### 4.4 Fuzzy Search Result

- item: full Item object
- score: number
- source: string (default: fuzzy)

## 5. Error Handling

### 5.1 HTTP Status Codes

- 200 OK: successful operation
- 404 Not Found: item not found for item-specific retrieval/update/delete
- 422 Unprocessable Entity: request validation failed (invalid payload or query parameters)

### 5.2 Standard Error Shapes

404 response example:

{
  "detail": "Item not found"
}

422 response example (FastAPI validation):

{
  "detail": [
    {
      "loc": ["query", "page_size"],
      "msg": "Input should be less than or equal to 50",
      "type": "less_than_equal"
    }
  ]
}

## 6. Endpoint Specifications

## 6.1 Health

### GET /health

Purpose:

- Liveness/basic service metadata check.

Response 200:

{
  "status": "ok",
  "service": "items-service",
  "env": "local"
}

## 6.2 Create Item

### POST /api/v1/items

Purpose:

- Creates a new item.
- Triggers asynchronous best-effort Vertex document upsert for search indexing.

Request body:

- Content-Type: application/json
- Schema: ItemCreate

Required fields:

- title
- abstraction

Optional fields:

- description, tags, author_id, author_name, source, url, citations

Request example:

{
  "title": "Transformers and Attention",
  "description": "Overview of self-attention",
  "abstraction": "A short abstract",
  "tags": ["nlp", "transformers"],
  "author_id": "author-1",
  "author_name": "Ada Nguyen",
  "source": "blog",
  "url": "https://example.com/article",
  "citations": ["https://arxiv.org/abs/1706.03762"]
}

Response 200:

- Schema: Item
- Returns persisted item with server-generated id and timestamps.

Notes:

- Vertex sync failures are logged and do not fail the create request.

## 6.3 List Items

### GET /api/v1/items

Purpose:

- Returns a non-paginated slice of items ordered by created_date descending.

Query parameters:

- limit: integer, optional, default 50, range 1..200

Response 200:

- Schema: array of Item

Request example:

- /api/v1/items?limit=25

## 6.4 List Items (Paged)

### GET /api/v1/items/paged

Purpose:

- Returns paginated items plus pagination metadata.

Query parameters:

- page: integer, optional, default 1, minimum 1
- page_size: integer, optional, default 20, range 1..100

Response 200:

{
  "items": [
    {
      "id": "f5179bc6-78e5-41b9-bf8f-f2d40e1ed4ec",
      "title": "Sample",
      "description": null,
      "abstraction": "Sample abstract",
      "tags": [],
      "author_id": null,
      "author_name": null,
      "source": null,
      "url": null,
      "citations": null,
      "created_date": "2026-03-28T08:10:12.123456+00:00",
      "updated_date": "2026-03-28T08:10:12.123456+00:00"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 120
  }
}

## 6.5 Get Item by ID

### GET /api/v1/items/

Purpose:

- Returns a single item by id.

Path parameters:

- item_id: string

Responses:

- 200: Item
- 404: Item not found

## 6.6 Update Item

### PATCH /api/v1/items/

Purpose:

- Partially updates an existing item.
- Triggers best-effort Vertex document upsert using updated record.

Path parameters:

- item_id: string

Request body:

- Content-Type: application/json
- Schema: ItemUpdate (all fields optional)

Request example:

{
  "description": "Updated description",
  "author_name": "Updated Author"
}

Responses:

- 200: Item (updated)
- 404: Item not found

Notes:

- Vertex sync failures are logged and do not fail the update request.

## 6.7 Delete Item

### DELETE /api/v1/items/

Purpose:

- Deletes an item and attempts to remove corresponding Vertex document.

Path parameters:

- item_id: string

Response 200:

{
  "deleted": true,
  "id": "<item_id>"
}

Error responses:

- 404: Item not found

Notes:

- Vertex delete failures are logged and do not fail the delete request.

## 6.8 Keyword Search

### GET /api/v1/items/search/keyword

Purpose:

- Executes keyword search using Vertex AI Search.
- On empty Vertex results or Vertex error, falls back to local keyword/fuzzy ranking.

Query parameters:

- q: string, required, minimum length 1
- page_size: integer, optional, default 10, range 1..50

Response 200:

- Schema: array of KeywordSearchResult

Response headers:

- X-Search-Backend:
  - vertex
  - fallback_vertex_empty
  - fallback_vertex_error
- X-Search-Result-Count: number of returned rows

Response example:

[
  {
    "id": "vertex-1",
    "title": "Result for transformer",
    "snippet": "Mocked vertex snippet",
    "score": null,
    "score_breakdown": null,
    "item": null,
    "source": "vertex_ai_search"
  }
]

Behavior details:

- When Vertex returns rows, each row is enriched with a Firestore lookup by id, producing item when available.
- If Vertex returns no rows, local fallback returns source as keyword_fallback with best-match item payloads.

## 6.9 Fuzzy Search

### GET /api/v1/items/search/fuzzy

Purpose:

- Performs local fuzzy search across Firestore items.

Query parameters:

- q: string, required, minimum length 1
- limit: integer, optional, default 10, range 1..50

Response 200:

- Schema: array of FuzzySearchResult

Response example:

[
  {
    "item": {
      "id": "f5179bc6-78e5-41b9-bf8f-f2d40e1ed4ec",
      "title": "Nike Running Shoe",
      "description": "Great for marathon",
      "abstraction": "High-cushion long distance shoe",
      "tags": ["sport", "running"],
      "author_id": null,
      "author_name": "Nike Team",
      "source": "catalog",
      "url": null,
      "citations": ["https://example.com/nike"],
      "created_date": "2026-03-28T08:10:12.123456+00:00",
      "updated_date": "2026-03-28T08:10:12.123456+00:00"
    },
    "score": 0.92,
    "source": "fuzzy"
  }
]
