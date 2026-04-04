from __future__ import annotations

import argparse
from typing import Any

import httpx


def fetch_all_items(client: httpx.Client, page_size: int = 100) -> list[dict[str, Any]]:
    page = 1
    all_items: list[dict[str, Any]] = []

    while True:
        response = client.get("/api/v1/items/paged", params={"page": page, "page_size": page_size})
        response.raise_for_status()
        payload = response.json()

        items = payload.get("items", [])
        meta = payload.get("meta", {})
        total = int(meta.get("total", 0))

        all_items.extend(items)

        if len(all_items) >= total or not items:
            break
        page += 1

    return all_items


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete seeded test items by source value")
    parser.add_argument("--base-url", required=True, help="Items service base URL, e.g. https://...run.app")
    parser.add_argument("--source", default="integration_seed_v1", help="Source marker to delete")
    parser.add_argument("--dry-run", action="store_true", help="Only print items to be deleted")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        items = fetch_all_items(client)
        targets = [item for item in items if (item.get("source") == args.source)]

        if not targets:
            print(f"No items found with source={args.source}")
            return

        print(f"Found {len(targets)} item(s) with source={args.source}")

        for item in targets:
            print(f"- {item.get('id')} | {item.get('title')}")
            if args.dry_run:
                continue

            response = client.delete(f"/api/v1/items/{item['id']}")
            response.raise_for_status()

        if args.dry_run:
            print("Dry run complete. No items were deleted.")
        else:
            print("Deletion complete.")


if __name__ == "__main__":
    main()
