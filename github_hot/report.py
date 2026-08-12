from __future__ import annotations

import statistics
from collections import Counter
from typing import Any


def build_report(rows: list[dict[str, Any]], limit: int = 30) -> dict[str, Any]:
    ranked = [row for row in rows if row.get("weekly_stars") is not None]
    ranked.sort(key=lambda row: row["weekly_stars"], reverse=True)
    ranked = ranked[:limit]

    items: list[dict[str, Any]] = []
    for rank, row in enumerate(ranked, start=1):
        weekly = row["weekly_stars"] or 0
        stars = row.get("stars") or 0
        previous = max(stars - weekly, 0)
        growth = (weekly / previous) if previous > 0 else None
        item = dict(row)
        item["rank"] = rank
        item["weekly_growth"] = round(growth * 100, 1) if growth is not None else None
        item["is_ai"] = bool(row.get("ai_reasons"))
        items.append(item)

    total_weekly = sum(item["weekly_stars"] or 0 for item in items)
    median_weekly = (
        round(statistics.median(item["weekly_stars"] or 0 for item in items), 1)
        if items
        else 0
    )
    language_counter = Counter(
        item.get("language") or "Unknown" for item in items
    )
    source_counter = Counter(item.get("source") or "unknown" for item in items)
    ai_count = sum(1 for item in items if item.get("ai_reasons"))
    collected_at = rows[0].get("collected_at") if rows else None

    return {
        "items": items,
        "meta": {
            "collected_at": collected_at,
            "repo_count": len(items),
            "ai_count": ai_count,
            "total_weekly_stars": total_weekly,
            "median_weekly_stars": median_weekly,
            "languages": language_counter.most_common(),
            "sources": dict(source_counter),
        },
    }
