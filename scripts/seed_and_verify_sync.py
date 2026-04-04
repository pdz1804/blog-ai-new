from __future__ import annotations

import argparse
import random
from typing import Any

import httpx

TOPICS = [
    ("Computer Networks", "routing protocols, congestion control, transport semantics"),
    ("Distributed Systems", "consensus, replication, failure domains"),
    ("Machine Learning", "generalization, regularization, evaluation"),
    ("Deep Learning", "attention, optimization, scaling behavior"),
    ("Databases", "indexing, transactions, query planning"),
    ("Operating Systems", "scheduling, memory management, isolation"),
    ("Compilers", "parsing, IR passes, optimization pipelines"),
    ("Information Retrieval", "ranking, recall, relevance feedback"),
    ("Cybersecurity", "threat modeling, cryptographic hygiene, access control"),
    ("Cloud Architecture", "resilience, observability, autoscaling patterns"),
]


def build_item(index: int) -> dict[str, Any]:
    topic, keywords = TOPICS[index % len(TOPICS)]
    return {
        "title": f"{topic} Practical Notes Vol.{index + 1}",
        "abstraction": f"A concise technical brief on {topic.lower()} with production-focused takeaways.",
        "description": (
            f"This document explores {topic.lower()} through design trade-offs, realistic failure cases, and implementation details. "
            f"Key focus areas include {keywords}. It also provides operational guidance, baseline metrics, and testing strategies "
            f"for teams shipping systems at scale."
        ),
        "tags": [topic.lower().replace(" ", "-"), "engineering", "production"],
        "author_id": f"seed-author-{index % 7}",
        "author_name": f"Seed Author {index % 7}",
        "source": "bulk_seed_sync_test_v1",
        "url": f"https://example.org/seed/{index + 1}",
        "citations": [
            "https://en.wikipedia.org/wiki/Computer_network",
            "https://en.wikipedia.org/wiki/Distributed_computing",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed many items and immediately verify keyword search sync")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--query", default="computer network")
    parser.add_argument("--wait-seconds", type=float, default=2.0)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    created_ids: list[str] = []

    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        for i in range(args.count):
            payload = build_item(i)
            response = client.post("/api/v1/items", json=payload)
            response.raise_for_status()
            created = response.json()
            created_ids.append(created["id"])

        print(f"Created {len(created_ids)} items with source=bulk_seed_sync_test_v1")

        # Small wait to allow near-real-time index propagation.
        if args.wait_seconds > 0:
            import time

            time.sleep(args.wait_seconds)

        search = client.get(
            "/api/v1/items/search/keyword",
            params={"q": args.query, "page_size": 10},
        )
        search.raise_for_status()

        backend = search.headers.get("X-Search-Backend", "")
        count_header = search.headers.get("X-Search-Result-Count", "")
        rows = search.json()

        print(f"Search backend: {backend}")
        print(f"Search header count: {count_header}")
        print(f"Search rows returned: {len(rows)}")

        for row in rows[:5]:
            print(f"- {row.get('title')} | score={row.get('score')} | source={row.get('source')}")


if __name__ == "__main__":
    main()
