from __future__ import annotations

from typing import Any

from google.api_core.exceptions import AlreadyExists, InvalidArgument, NotFound
from google.cloud import discoveryengine_v1beta as discoveryengine


def _branch_path(project_id: str, location: str, datastore_id: str) -> str:
    return (
        f"projects/{project_id}/locations/{location}/collections/default_collection/"
        f"dataStores/{datastore_id}/branches/default_branch"
    )


def _content_text(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "")
    abstraction = str(item.get("abstraction") or "")
    description = str(item.get("description") or "")
    return "\n\n".join([p for p in [title, abstraction, description] if p]).strip()


def _struct_data(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "title": str(item.get("title") or ""),
        "abstraction": str(item.get("abstraction") or ""),
        "description": str(item.get("description") or ""),
        "tags": list(item.get("tags") or []),
        "author_id": item.get("author_id"),
        "author_name": item.get("author_name"),
        "source": item.get("source"),
        "url": item.get("url"),
        "citations": list(item.get("citations") or []),
        "created_date": str(item.get("created_date") or ""),
        "updated_date": str(item.get("updated_date") or ""),
    }


def upsert_item_document(
    project_id: str,
    location: str,
    datastore_id: str,
    item: dict[str, Any],
) -> None:
    doc_id = str(item.get("id") or "")
    if not doc_id:
        return

    parent = _branch_path(project_id=project_id, location=location, datastore_id=datastore_id)
    doc_client = discoveryengine.DocumentServiceClient()

    def build_document(include_content: bool) -> discoveryengine.Document:
        doc = discoveryengine.Document(id=doc_id, struct_data=_struct_data(item))
        if include_content:
            doc.content = discoveryengine.Document.Content(
                raw_bytes=_content_text(item).encode("utf-8"),
                mime_type="text/plain",
            )
        return doc

    try:
        doc_client.create_document(
            request=discoveryengine.CreateDocumentRequest(
                parent=parent,
                document=build_document(include_content=True),
                document_id=doc_id,
            )
        )
        return
    except AlreadyExists:
        pass
    except InvalidArgument:
        doc_client.create_document(
            request=discoveryengine.CreateDocumentRequest(
                parent=parent,
                document=build_document(include_content=False),
                document_id=doc_id,
            )
        )
        return

    try:
        update_doc = build_document(include_content=True)
        update_doc.name = f"{parent}/documents/{doc_id}"
        doc_client.update_document(
            request=discoveryengine.UpdateDocumentRequest(document=update_doc, allow_missing=True)
        )
    except InvalidArgument:
        update_doc = build_document(include_content=False)
        update_doc.name = f"{parent}/documents/{doc_id}"
        doc_client.update_document(
            request=discoveryengine.UpdateDocumentRequest(document=update_doc, allow_missing=True)
        )


def delete_item_document(project_id: str, location: str, datastore_id: str, doc_id: str) -> None:
    if not doc_id:
        return

    parent = _branch_path(project_id=project_id, location=location, datastore_id=datastore_id)
    doc_client = discoveryengine.DocumentServiceClient()
    name = f"{parent}/documents/{doc_id}"
    try:
        doc_client.delete_document(request=discoveryengine.DeleteDocumentRequest(name=name))
    except NotFound:
        return
