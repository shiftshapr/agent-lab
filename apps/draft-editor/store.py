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
) -> dict:
    """Create a new draft."""
    draft_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat() + "Z"
    draft = {
        "content": content,
        "platform": platform,
        "metadata": metadata or {},
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
