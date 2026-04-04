from __future__ import annotations

import argparse
import os
from datetime import datetime
from typing import Any

import google.auth
from google.api_core.exceptions import AlreadyExists
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import firestore


def env(name: str, fallback: str | None = None) -> str:
    value = os.getenv(name)
    if value is not None and value.strip() != "":
        return value
    if fallback is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return fallback


def to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    return value


def content_text(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "")
    abstraction = str(item.get("abstraction") or "")
    description = str(item.get("description") or "")
    return "\n\n".join([part for part in [title, abstraction, description] if part]).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Firestore items to Vertex AI Search datastore")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--location", default=None)
    parser.add_argument("--datastore-id", default=None)
    parser.add_argument("--collection", default=None)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--prune", action="store_true", help="Delete Vertex docs not found in Firestore")
    parser.add_argument("--include-content", action="store_true", help="Send Document.content payload (for CONTENT_REQUIRED datastore)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    project_id = args.project_id or env("GCP_PROJECT_ID")
    location = args.location or env("VERTEX_SEARCH_LOCATION_SERVICE", env("VERTEX_SEARCH_LOCATION", "global"))
    datastore_id = args.datastore_id or env(
        "VERTEX_SEARCH_ITEMS_DATASTORE_ID_SERVICE",
        env("VERTEX_SEARCH_ITEMS_DATASTORE_ID", "items-datastore-v2"),
    )
    collection = args.collection or env("FIRESTORE_ITEMS_COLLECTION_SERVICE", "items_catalog_v2")

    credentials, _ = google.auth.default(quota_project_id=project_id)

    fs_client = firestore.Client(project=project_id, credentials=credentials)
    doc_client = discoveryengine.DocumentServiceClient(credentials=credentials)

    branch = (
        f"projects/{project_id}/locations/{location}/collections/default_collection/"
        f"dataStores/{datastore_id}/branches/default_branch"
    )

    query = fs_client.collection(collection).order_by("created_date", direction=firestore.Query.DESCENDING).limit(args.limit)
    fs_docs = list(query.stream())

    print(f"Found {len(fs_docs)} Firestore items in collection '{collection}'")

    firestore_ids: set[str] = set()
    created_count = 0
    updated_count = 0

    for snap in fs_docs:
        item = snap.to_dict() or {}
        item_id = str(item.get("id") or snap.id)
        firestore_ids.add(item_id)

        struct_data = {
            "id": item_id,
            "title": str(item.get("title") or ""),
            "abstraction": str(item.get("abstraction") or ""),
            "description": str(item.get("description") or ""),
            "tags": list(item.get("tags") or []),
            "author_id": item.get("author_id"),
            "author_name": item.get("author_name"),
            "source": item.get("source"),
            "url": item.get("url"),
            "citations": list(item.get("citations") or []),
            "created_date": to_jsonable(item.get("created_date")),
            "updated_date": to_jsonable(item.get("updated_date")),
        }

        vertex_doc = discoveryengine.Document(id=item_id, struct_data=struct_data)
        if args.include_content:
            vertex_doc.content = discoveryengine.Document.Content(
                raw_bytes=content_text(item).encode("utf-8"),
                mime_type="text/plain",
            )

        if args.dry_run:
            print(f"[DRY-RUN] upsert {item_id} | {struct_data['title']}")
            continue

        try:
            doc_client.create_document(
                discoveryengine.CreateDocumentRequest(
                    parent=branch,
                    document=vertex_doc,
                    document_id=item_id,
                )
            )
            created_count += 1
        except AlreadyExists:
            vertex_doc.name = f"{branch}/documents/{item_id}"
            doc_client.update_document(
                discoveryengine.UpdateDocumentRequest(document=vertex_doc, allow_missing=True)
            )
            updated_count += 1

    deleted_count = 0
    if args.prune:
        existing_vertex_ids: set[str] = set()
        for doc in doc_client.list_documents(request=discoveryengine.ListDocumentsRequest(parent=branch)):
            existing_vertex_ids.add(doc.id)

        to_delete = sorted(existing_vertex_ids - firestore_ids)
        print(f"Prune enabled: {len(to_delete)} stale Vertex docs")

        for doc_id in to_delete:
            if args.dry_run:
                print(f"[DRY-RUN] delete {doc_id}")
                continue

            doc_client.delete_document(
                request=discoveryengine.DeleteDocumentRequest(name=f"{branch}/documents/{doc_id}")
            )
            deleted_count += 1

    if args.dry_run:
        print("Dry-run finished.")
        return

    print(
        "Sync completed. "
        f"created={created_count}, updated={updated_count}, deleted={deleted_count}, total_source={len(fs_docs)}"
    )


if __name__ == "__main__":
    main()
