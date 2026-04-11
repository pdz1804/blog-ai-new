import logging
import uuid

from fastapi import FastAPI, HTTPException, Query, Response

from app.config import get_settings
from app.repository import FirestoreItemRepository
from app.schemas import (
    FuzzySearchResult,
    ItemCreate,
    ItemOut,
    ItemUpdate,
    KeywordSearchResult,
    PageMeta,
    PagedItems,
    PagedItemsByTag,
    PresignedUrlRequest,
    PresignedUrlResponse,
    TagCount,
)
from app.search_fuzzy import fuzzy_search_items
from app.search_vertex import VertexKeywordSearchClient
from app.sync_vertex import delete_item_document, upsert_item_document
from app.storage import generate_upload_signed_url_v4

settings = get_settings()

app = FastAPI(title="Items Service", version="1.0.0")
logger = logging.getLogger("items.search")

_repo: FirestoreItemRepository | None = None
_vertex_client: VertexKeywordSearchClient | None = None


def get_repo() -> FirestoreItemRepository:
    global _repo
    if _repo is None:
        _repo = FirestoreItemRepository(
            project_id=settings.gcp_project_id,
            collection_name=settings.firestore_items_collection_service,
        )
    return _repo


def get_vertex_client() -> VertexKeywordSearchClient:
    global _vertex_client
    if _vertex_client is None:
        _vertex_client = VertexKeywordSearchClient(
            project_id=settings.gcp_project_id,
            location=settings.vertex_search_location_service,
            datastore_id=settings.vertex_search_items_datastore_id_service,
        )
    return _vertex_client


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": settings.app_name, "env": settings.app_env}


@app.post("/api/v1/items", response_model=ItemOut)
def create_item(payload: ItemCreate) -> ItemOut:
    data = get_repo().create(payload)
    try:
        upsert_item_document(
            project_id=settings.gcp_project_id,
            location=settings.vertex_search_location_service,
            datastore_id=settings.vertex_search_items_datastore_id_service,
            item=data,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("vertex_auto_sync create failed item_id=%s error=%s", data.get("id"), exc)
    return ItemOut(**data)


@app.get("/api/v1/items", response_model=list[ItemOut])
def list_items(limit: int = Query(default=50, ge=1, le=200)) -> list[ItemOut]:
    rows = get_repo().list(limit=limit, offset=0)
    return [ItemOut(**row) for row in rows]


@app.get("/api/v1/items/paged", response_model=PagedItems)
def list_items_paged(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PagedItems:
    offset = (page - 1) * page_size
    rows = get_repo().list(limit=page_size, offset=offset)
    total = get_repo().count()
    return PagedItems(
        items=[ItemOut(**row) for row in rows],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@app.get("/api/v1/items/search/keyword", response_model=list[KeywordSearchResult])
def search_items_keyword(
    response: Response,
    q: str = Query(min_length=1),
    page_size: int = Query(default=10, ge=1, le=50),
) -> list[KeywordSearchResult]:
    backend = "vertex"
    try:
        results = get_vertex_client().search(query=q, page_size=page_size)
    except Exception as exc:  # noqa: BLE001
        logger.exception("keyword_search vertex_error query=%s page_size=%s error=%s", q, page_size, exc)
        backend = "fallback_vertex_error"
        results = []

    if results:
        payload: list[KeywordSearchResult] = []
        for row in results:
            item_doc = get_repo().get(str(row.get("id", "")))
            item_full = ItemOut(**item_doc) if item_doc else None
            payload.append(
                KeywordSearchResult(
                    id=str(row.get("id", "")),
                    title=str(row.get("title", "")),
                    snippet=row.get("snippet"),
                    score=row.get("score"),
                    score_breakdown=row.get("score_breakdown"),
                    item=item_full,
                    source=str(row.get("source", "vertex_ai_search")),
                )
            )
        response.headers["X-Search-Backend"] = backend
        response.headers["X-Search-Result-Count"] = str(len(payload))
        logger.info("keyword_search backend=%s query=%s results=%s", backend, q, len(payload))
        return payload

    # Fallback: when Vertex index is empty/not yet indexed, return basic local keyword matches.
    local_items = get_repo().list_all_for_search(max_items=500)
    fallback = fuzzy_search_items(
        items=local_items,
        keyword=q,
        limit=page_size,
        freshness_halflife_days=settings.freshness_halflife_days,
    )
    payload = [
        KeywordSearchResult(
            id=str(row["item"].get("id", "")),
            title=str(row["item"].get("title", "")),
            snippet=str(row["item"].get("description") or row["item"].get("abstraction") or ""),
            score=float(row.get("score", 0.0)),
            score_breakdown=row.get("score_breakdown"),
            item=ItemOut(**row["item"]),
            source="keyword_fallback",
        )
        for row in fallback
    ]
    if backend == "vertex":
        backend = "fallback_vertex_empty"
    response.headers["X-Search-Backend"] = backend
    response.headers["X-Search-Result-Count"] = str(len(payload))
    logger.warning("keyword_search backend=%s query=%s results=%s", backend, q, len(payload))
    return payload


@app.get("/api/v1/items/search/fuzzy", response_model=list[FuzzySearchResult])
def search_items_fuzzy(
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[FuzzySearchResult]:
    items = get_repo().list_all_for_search(max_items=500)
    results = fuzzy_search_items(
        items=items,
        keyword=q,
        limit=limit,
        freshness_halflife_days=settings.freshness_halflife_days,
    )
    return [FuzzySearchResult(**r) for r in results]


@app.get("/api/v1/items/by-tag/{tag}", response_model=PagedItemsByTag)
def list_items_by_tag(
    tag: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PagedItemsByTag:
    offset = (page - 1) * page_size
    rows = get_repo().list_by_tag(tag=tag, limit=page_size, offset=offset)
    total = get_repo().count_by_tag(tag=tag)
    return PagedItemsByTag(
        tag=tag,
        items=[ItemOut(**row) for row in rows],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@app.get("/api/v1/tags/top", response_model=list[TagCount])
def get_top_tags(k: int = Query(default=10, ge=1, le=100)) -> list[TagCount]:
    results = get_repo().get_top_tags(k=k)
    return [TagCount(**r) for r in results]


@app.get("/api/v1/items/{item_id}", response_model=ItemOut)
def get_item(item_id: str) -> ItemOut:
    data = get_repo().get(item_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemOut(**data)


@app.patch("/api/v1/items/{item_id}", response_model=ItemOut)
def update_item(item_id: str, payload: ItemUpdate) -> ItemOut:
    data = get_repo().update(item_id, payload)
    if data is None:
        raise HTTPException(status_code=404, detail="Item not found")
    try:
        upsert_item_document(
            project_id=settings.gcp_project_id,
            location=settings.vertex_search_location_service,
            datastore_id=settings.vertex_search_items_datastore_id_service,
            item=data,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("vertex_auto_sync update failed item_id=%s error=%s", item_id, exc)
    return ItemOut(**data)


@app.delete("/api/v1/items/{item_id}")
def delete_item(item_id: str) -> dict:
    deleted = get_repo().delete(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    try:
        delete_item_document(
            project_id=settings.gcp_project_id,
            location=settings.vertex_search_location_service,
            datastore_id=settings.vertex_search_items_datastore_id_service,
            doc_id=item_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("vertex_auto_sync delete failed item_id=%s error=%s", item_id, exc)
    return {"deleted": True, "id": item_id}

@app.post("/api/v1/upload/presign", response_model=PresignedUrlResponse)
def get_upload_presigned_url(payload: PresignedUrlRequest) -> PresignedUrlResponse:
    # Use uuid to ensure unique object names and prevent overwriting
    ext = payload.filename.rsplit(".", 1)[-1] if "." in payload.filename else "bin"
    object_name = f"uploads/{uuid.uuid4().hex}.{ext}"

    try:
        url = generate_upload_signed_url_v4(
            bucket_name=settings.gcp_storage_bucket_images,
            blob_name=object_name,
            content_type=payload.content_type,
            expiration_minutes=15,
        )
    except Exception as exc:
        logger.exception("Failed to generate signed url")
        raise HTTPException(status_code=500, detail="Could not generate upload URL")

    return PresignedUrlResponse(url=url, object_name=object_name, method="PUT")
