"""Draft store — JSON files with rolling history (10 versions)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

STORE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "draft_store"
HISTORY_LIMIT = 10


def _ensure_store() -> Path:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    return STORE_DIR


def _draft_path(draft_id: str) -> Path:
    return _ensure_store() / f"{draft_id}.json"


def _load_index() -> list[str]:
    path = _ensure_store() / "index.json"
    if path.exists():
        return json.loads(path.read_text())
    return []


def _save_index(ids: list[str]) -> None:
    (_ensure_store() / "index.json").write_text(json.dumps(ids, indent=2))


def list_drafts() -> list[dict]:
    """List all drafts, newest first."""
    ids = _load_index()
    drafts = []
    for did in ids:
        p = _draft_path(did)
        if p.exists():
            try:
                d = json.loads(p.read_text())
                d["id"] = did
                drafts.append(d)
            except Exception:
                pass
    return sorted(drafts, key=lambda x: x.get("updated_at", ""), reverse=True)


def list_reply_drafts() -> list[dict]:
    """List drafts that are replies (metadata.parent_post_url or draft_type=reply)."""
    drafts = list_drafts()
    return [d for d in drafts if d.get("metadata", {}).get("parent_post_url") or d.get("metadata", {}).get("draft_type") == "reply"]


def get_draft(draft_id: str) -> dict | None:
    """Get a single draft by id."""
    p = _draft_path(draft_id)
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    d["id"] = draft_id
    return d


def create_draft(
    content: str,
    platform: str = "linkedin",
    metadata: dict | None = None,
    author: str = "agent",
    destination: str = "",
) -> dict:
    """Create a new draft. destination: where it will be published (e.g. 'LinkedIn · Daveed Benjamin', 'X · @shiftshapr')."""
    draft_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat() + "Z"
    meta = metadata or {}
    if destination:
        meta["destination"] = destination
    draft = {
        "content": content,
        "platform": platform,
        "metadata": meta,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "history": [
            {"timestamp": now, "content": content, "author": author, "milestone": "agent_draft"}
        ],
    }
    _draft_path(draft_id).write_text(json.dumps(draft, indent=2))
    ids = _load_index()
    ids.insert(0, draft_id)
    _save_index(ids)
    draft["id"] = draft_id
    return draft


def update_draft_metadata(
    draft_id: str,
    destination: str | None = None,
    platform: str | None = None,
    draft_location: str | None = None,
    draft_url: str | None = None,
) -> dict | None:
    """Update draft metadata without changing content."""
    draft = get_draft(draft_id)
    if not draft:
        return None
    meta = draft.get("metadata", {})
    if destination is not None:
        meta["destination"] = destination
    if platform is not None:
        draft["platform"] = platform
    if draft_location is not None:
        meta["draft_location"] = draft_location
    if draft_url is not None:
        meta["draft_url"] = draft_url
    draft["metadata"] = meta
    draft["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _draft_path(draft_id).write_text(json.dumps({k: v for k, v in draft.items() if k != "id"}, indent=2))
    draft["id"] = draft_id
    return draft


def merge_draft_metadata(draft_id: str, updates: dict | None) -> dict | None:
    """Merge keys into draft metadata (e.g. scheduled_for). Pass value None to remove a key."""
    if not updates:
        return get_draft(draft_id)
    draft = get_draft(draft_id)
    if not draft:
        return None
    meta = dict(draft.get("metadata", {}))
    for k, v in updates.items():
        if v is None:
            meta.pop(k, None)
        else:
            meta[k] = v
    draft["metadata"] = meta
    draft["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _draft_path(draft_id).write_text(json.dumps({k: v for k, v in draft.items() if k != "id"}, indent=2))
    draft["id"] = draft_id
    return draft


def update_draft(
    draft_id: str,
    content: str,
    author: str = "user",
    milestone: str | None = None,
) -> dict | None:
    """Update draft content, append to history (rolling window)."""
    draft = get_draft(draft_id)
    if not draft:
        return None
    now = datetime.utcnow().isoformat() + "Z"
    history = draft.get("history", [])
    history.append({
        "timestamp": now,
        "content": content,
        "author": author,
        "milestone": milestone,
    })
    draft["history"] = history[-HISTORY_LIMIT:]
    draft["content"] = content
    draft["updated_at"] = now
    draft["status"] = "edited"
    _draft_path(draft_id).write_text(json.dumps({k: v for k, v in draft.items() if k != "id"}, indent=2))
    draft["id"] = draft_id
    return draft


def publish_draft(draft_id: str) -> dict | None:
    """Mark draft as published, add milestone."""
    draft = get_draft(draft_id)
    if not draft:
        return None
    now = datetime.utcnow().isoformat() + "Z"
    history = draft.get("history", [])
    history.append({
        "timestamp": now,
        "content": draft["content"],
        "author": "system",
        "milestone": "published",
    })
    draft["history"] = history[-HISTORY_LIMIT:]
    draft["status"] = "published"
    draft["updated_at"] = now
    draft["published_at"] = now
    _draft_path(draft_id).write_text(json.dumps({k: v for k, v in draft.items() if k != "id"}, indent=2))
    draft["id"] = draft_id
    return draft


def delete_draft(draft_id: str) -> bool:
    """Delete a draft."""
    p = _draft_path(draft_id)
    if not p.exists():
        return False
    p.unlink()
    ids = [i for i in _load_index() if i != draft_id]
    _save_index(ids)
    return True
