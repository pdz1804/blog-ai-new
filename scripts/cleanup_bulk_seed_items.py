from __future__ import annotations

import argparse
from typing import Any

import httpx


def fetch_all(client: httpx.Client) -> list[dict[str, Any]]:
    page = 1
    page_size = 100
    rows: list[dict[str, Any]] = []

    while True:
        resp = client.get("/api/v1/items/paged", params={"page": page, "page_size": page_size})
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("items", [])
        rows.extend(items)
        total = int(payload.get("meta", {}).get("total", 0))
        if len(rows) >= total or not items:
            break
        page += 1

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete seeded bulk test items by source marker")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--source", default="bulk_seed_sync_test_v1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        rows = fetch_all(client)
        targets = [r for r in rows if r.get("source") == args.source]
        print(f"Found {len(targets)} items with source={args.source}")

        for item in targets:
            print(f"- {item.get('id')} | {item.get('title')}")
            if args.dry_run:
                continue
            resp = client.delete(f"/api/v1/items/{item['id']}")
            resp.raise_for_status()

        if args.dry_run:
            print("Dry-run complete.")
        else:
            print("Deletion complete.")


if __name__ == "__main__":
    main()
