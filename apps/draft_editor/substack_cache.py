"""Substack cache — JSON persistence per publication, merge-only refresh."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "substack_cache.json"

_lock = threading.Lock()
_refreshing: dict[str, bool] = {}  # publication_id -> bool


def _empty_pub() -> dict:
    return {"drafts": [], "scheduled": [], "published": [], "updated_at": None, "refreshing": False}


def _read_raw() -> dict:
    """Read raw JSON from disk. Caller must hold _lock."""
    if not CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _migrate_legacy(raw: dict) -> dict:
    """Migrate old top-level format to publication-keyed format."""
    if "drafts" in raw and "published" in raw:
        return {"metaweb": raw}
    return raw


def load(publication_id: str) -> dict:
    """Load cache for a publication. Returns drafts, published, updated_at, refreshing."""
    with _lock:
        raw = _read_raw()
        raw = _migrate_legacy(raw)
        pub = raw.get(publication_id, _empty_pub())
        if not isinstance(pub, dict):
            pub = _empty_pub()
        return {
            "drafts": pub.get("drafts", []),
            "scheduled": pub.get("scheduled", []),
            "published": pub.get("published", []),
            "updated_at": pub.get("updated_at"),
            "refreshing": pub.get("refreshing", False),
        }


def _merge_existing(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Merge incoming into existing; only add items not already present (by url)."""
    urls = {e["url"] for e in existing if e.get("url")}
    merged = list(existing)
    for item in incoming:
        url = (item.get("url") or "").strip()
        if url and url not in urls:
            urls.add(url)
            entry = {"url": url, "title": (item.get("title") or url).strip()}
            if item.get("date"):
                entry["date"] = item["date"]
            merged.append(entry)
    return merged


def merge_and_save(publication_id: str, drafts: list[dict], scheduled: list[dict], published: list[dict]) -> None:
    """Merge drafts (add new only). Replace scheduled and published entirely."""
    global _refreshing
    with _lock:
        raw = _read_raw()
        raw = _migrate_legacy(raw)
        pub = raw.get(publication_id, _empty_pub())
        if not isinstance(pub, dict):
            pub = _empty_pub()
        new_drafts = _merge_existing(pub.get("drafts", []), drafts)
        # Replace scheduled and published (fresh data with dates)
        def _norm(items: list[dict]) -> list[dict]:
            out = []
            for i in items:
                entry = {"url": i.get("url", "").strip(), "title": (i.get("title") or i.get("url", "")).strip()}
                if i.get("date"):
                    entry["date"] = i["date"]
                if entry["url"]:
                    out.append(entry)
            return out
        new_scheduled = _norm(scheduled)
        new_published = _norm(published)
        raw[publication_id] = {
            "drafts": new_drafts,
            "scheduled": new_scheduled,
            "published": new_published,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "refreshing": False,
        }
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        _refreshing[publication_id] = False


def is_refreshing(publication_id: str) -> bool:
    return _refreshing.get(publication_id, False)


def set_refreshing(publication_id: str, val: bool) -> None:
    _refreshing[publication_id] = val


def mark_refreshing(publication_id: str) -> None:
    """Write refreshing=true to disk for this publication."""
    with _lock:
        raw = _read_raw()
        raw = _migrate_legacy(raw)
        pub = raw.get(publication_id, _empty_pub())
        if not isinstance(pub, dict):
            pub = _empty_pub()
        raw[publication_id] = {
            "drafts": pub.get("drafts", []),
            "scheduled": pub.get("scheduled", []),
            "published": pub.get("published", []),
            "updated_at": pub.get("updated_at"),
            "refreshing": True,
        }
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        set_refreshing(publication_id, True)


def clear_refreshing(publication_id: str) -> None:
    """Set refreshing=false without changing data."""
    with _lock:
        raw = _read_raw()
        raw = _migrate_legacy(raw)
        pub = raw.get(publication_id, _empty_pub())
        if not isinstance(pub, dict):
            pub = _empty_pub()
        raw[publication_id] = {
            "drafts": pub.get("drafts", []),
            "scheduled": pub.get("scheduled", []),
            "published": pub.get("published", []),
            "updated_at": pub.get("updated_at"),
            "refreshing": False,
        }
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        set_refreshing(publication_id, False)
