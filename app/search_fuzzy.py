from __future__ import annotations

from datetime import datetime, timezone
from math import exp, log

from rapidfuzz import fuzz


def _safe_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _coerce_datetime(value: object | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
    return None


def _freshness_score(created_date: object | None, halflife_days: float) -> float:
    if halflife_days <= 0:
        return 0.0

    dt = _coerce_datetime(created_date)
    if dt is None:
        return 0.0

    now = datetime.now(timezone.utc)
    age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
    decay = log(2.0) / halflife_days
    return exp(-decay * age_days)


def fuzzy_search_items(
    items: list[dict],
    keyword: str,
    limit: int = 10,
    freshness_halflife_days: float = 180.0,
) -> list[dict]:
    scored: list[dict] = []

    for item in items:
        title = _safe_text(item.get("title"))
        abstraction = _safe_text(item.get("abstraction"))
        description = _safe_text(item.get("description"))
        tags = " ".join([_safe_text(t) for t in (item.get("tags") or [])])

        # Text score combines requested fields first: title + abstraction + description.
        text_corpus = f"{title} {abstraction} {description} {tags}".strip()
        text_score = fuzz.WRatio(keyword, text_corpus) / 100.0

        business_score = _freshness_score(
            created_date=item.get("created_date"),
            halflife_days=freshness_halflife_days,
        )

        # Weighted final score: lexical relevance + freshness business signal.
        final_score = ((0.8 * text_score) + (0.2 * business_score)) * 100.0

        if final_score > 0:
            scored.append(
                {
                    "item": item,
                    "score": float(final_score),
                    "score_breakdown": {
                        "text_score": round(text_score * 100.0, 4),
                        "business_score": round(business_score * 100.0, 4),
                        "text_weight": 0.8,
                        "business_weight": 0.2,
                        "final_score": round(final_score, 4),
                    },
                }
            )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
