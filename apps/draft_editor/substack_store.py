"""Substack links store — draft and published post URLs for navigation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

STORE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "substack_links.json"


def _load() -> list[dict]:
    if not STORE_PATH.exists():
        return []
    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(links: list[dict]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(links, indent=2), encoding="utf-8")


def list_links() -> dict:
    """Return drafts and published grouped."""
    links = _load()
    drafts = [l for l in links if l.get("type") == "draft"]
    published = [l for l in links if l.get("type") == "published"]
    return {"drafts": drafts, "published": published}


def add_link(url: str, link_type: str = "draft", title: str = "") -> dict:
    """Add a Substack link. link_type: draft | published."""
    links = _load()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "url": url.strip(),
        "type": link_type if link_type in ("draft", "published") else "draft",
        "title": (title or "").strip(),
        "added_at": datetime.utcnow().isoformat() + "Z",
    }
    links.append(entry)
    _save(links)
    return entry


def delete_link(link_id: str) -> bool:
    """Remove a link by id."""
    links = _load()
    orig_len = len(links)
    links = [l for l in links if l.get("id") != link_id]
    if len(links) == orig_len:
        return False
    _save(links)
    return True
