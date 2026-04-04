from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import main


class FakeRepo:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self._id_counter = 0

    def _new_id(self) -> str:
        self._id_counter += 1
        return f"item-{self._id_counter}"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def create(self, payload):
        item_id = self._new_id()
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
        self.items[item_id] = data
        return data

    def get(self, item_id: str):
        return self.items.get(item_id)

    def update(self, item_id: str, payload):
        existing = self.items.get(item_id)
        if existing is None:
            return None
        updates = payload.model_dump(exclude_unset=True)
        existing.update(updates)
        existing["updated_date"] = self._now()
        return existing

    def delete(self, item_id: str) -> bool:
        if item_id not in self.items:
            return False
        del self.items[item_id]
        return True

    def list(self, limit: int = 50, offset: int = 0):
        rows = list(self.items.values())
        return rows[offset : offset + limit]

    def count(self) -> int:
        return len(self.items)

    def list_all_for_search(self, max_items: int = 500):
        rows = list(self.items.values())
        return rows[:max_items]


class FakeVertexClient:
    def search(self, query: str, page_size: int = 10):
        return [
            {
                "id": "vertex-1",
                "title": f"Result for {query}",
                "snippet": "Mocked vertex snippet",
            }
        ][:page_size]


@pytest.fixture()
def client():
    fake_repo = FakeRepo()
    fake_vertex = FakeVertexClient()

    main._repo = fake_repo
    main._vertex_client = fake_vertex

    with TestClient(main.app) as test_client:
        yield test_client


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_crud_flow(client: TestClient):
    create_response = client.post(
        "/api/v1/items",
        json={
            "title": "Running Shoes",
            "description": "Lightweight pair",
            "abstraction": "Lightweight daily trainer",
            "tags": ["sport", "shoe"],
            "author_id": "author-1",
            "author_name": "Alice",
            "source": "blog",
            "url": "https://example.com/running-shoes",
            "citations": ["https://example.com/source-1"],
        },
    )
    assert create_response.status_code == 200
    item = create_response.json()
    item_id = item["id"]

    get_response = client.get(f"/api/v1/items/{item_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Running Shoes"

    update_response = client.patch(
        f"/api/v1/items/{item_id}",
        json={"description": "Updated description", "author_name": "Alice Updated"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Updated description"
    assert update_response.json()["author_name"] == "Alice Updated"

    delete_response = client.delete(f"/api/v1/items/{item_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    missing_response = client.get(f"/api/v1/items/{item_id}")
    assert missing_response.status_code == 404


def test_listing_and_paging(client: TestClient):
    for idx in range(1, 6):
        client.post(
            "/api/v1/items",
            json={
                "title": f"Item {idx}",
                "description": f"Description {idx}",
                "abstraction": f"Abstract {idx}",
                "tags": ["tag"],
                "citations": [],
            },
        )

    list_response = client.get("/api/v1/items?limit=3")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 3

    page_response = client.get("/api/v1/items/paged?page=2&page_size=2")
    assert page_response.status_code == 200
    body = page_response.json()
    assert body["meta"]["page"] == 2
    assert body["meta"]["page_size"] == 2
    assert body["meta"]["total"] == 5
    assert len(body["items"]) == 2


def test_keyword_search(client: TestClient):
    response = client.get("/api/v1/items/search/keyword?q=shoe&page_size=5")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["source"] == "vertex_ai_search"


def test_fuzzy_search(client: TestClient):
    client.post(
        "/api/v1/items",
        json={
            "title": "Nike Running Shoe",
            "description": "Great for marathon",
            "abstraction": "High-cushion long distance shoe",
            "tags": ["sport", "running"],
            "author_name": "Nike Team",
            "source": "catalog",
            "citations": ["https://example.com/nike"],
        },
    )
    client.post(
        "/api/v1/items",
        json={
            "title": "Leather Wallet",
            "description": "Brown wallet",
            "abstraction": "Minimal leather wallet",
            "tags": ["fashion"],
            "author_name": "Fashion Team",
            "source": "catalog",
            "citations": [],
        },
    )

    response = client.get("/api/v1/items/search/fuzzy?q=running shoe&limit=2")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[0]["source"] == "fuzzy"
    assert "item" in body[0]
