from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from google.cloud import firestore

from app.schemas import ItemCreate, ItemUpdate


class FirestoreItemRepository:
    def __init__(self, project_id: str, collection_name: str) -> None:
        self._db = firestore.Client(project=project_id)
        self._collection = self._db.collection(collection_name)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def create(self, payload: ItemCreate) -> dict:
        item_id = str(uuid4())
        now = self._now()
        data = {
            "id": item_id,
            "title": payload.title,
            "description": payload.description,
            "abstraction": payload.abstraction,
            "tags": payload.tags,
            "author_id": payload.author_id,
            "author_name": payload.author_name,
            "source": payload.source,
            "url": payload.url,
            "citations": payload.citations,
            "created_date": now,
            "updated_date": now,
        }
        self._collection.document(item_id).set(data)
        return data

    def get(self, item_id: str) -> dict | None:
        doc = self._collection.document(item_id).get()
        if not doc.exists:
            return None
        return doc.to_dict()

    def update(self, item_id: str, payload: ItemUpdate) -> dict | None:
        existing = self.get(item_id)
        if existing is None:
            return None

        updates = payload.model_dump(exclude_unset=True)
        updates["updated_date"] = self._now()

        self._collection.document(item_id).update(updates)
        updated = self.get(item_id)
        return updated

    def delete(self, item_id: str) -> bool:
        doc = self._collection.document(item_id).get()
        if not doc.exists:
            return False
        self._collection.document(item_id).delete()
        return True

    def count(self) -> int:
        count = 0
        for _ in self._collection.stream():
            count += 1
        return count

    def list(self, limit: int = 50, offset: int = 0) -> list[dict]:
        query = self._collection.order_by("created_date", direction=firestore.Query.DESCENDING)
        query = query.offset(offset).limit(limit)
        return [doc.to_dict() for doc in query.stream()]

    def list_all_for_search(self, max_items: int = 500) -> list[dict]:
        query = self._collection.order_by("created_date", direction=firestore.Query.DESCENDING).limit(max_items)
        return [doc.to_dict() for doc in query.stream()]

    def list_by_tag(self, tag: str, limit: int = 50, offset: int = 0) -> list[dict]:
        query = (
            self._collection
            .where("tags", "array_contains", tag)
            .order_by("created_date", direction=firestore.Query.DESCENDING)
            .offset(offset)
            .limit(limit)
        )
        return [doc.to_dict() for doc in query.stream()]

    def count_by_tag(self, tag: str) -> int:
        query = self._collection.where("tags", "array_contains", tag)
        return sum(1 for _ in query.stream())

    def get_top_tags(self, k: int = 10) -> list[dict]:
        tag_counts: dict[str, int] = {}
        for doc in self._collection.stream():
            data = doc.to_dict()
            for tag in data.get("tags") or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"tag": tag, "count": count} for tag, count in sorted_tags[:k]]
