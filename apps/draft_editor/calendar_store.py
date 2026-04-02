"""Master calendar + work log — JSON store for agent scheduling and habit capture."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent.parent
CALENDAR_PATH = AGENT_LAB_ROOT / "data" / "master_calendar.json"


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_default() -> dict:
    return {
        "schema_version": 1,
        "updated_at": _now_iso(),
        "events": [],
        "work_log": [],
    }


def load_calendar() -> dict:
    if not CALENDAR_PATH.exists():
        data = _ensure_default()
        CALENDAR_PATH.parent.mkdir(parents=True, exist_ok=True)
        CALENDAR_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    try:
        return json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _ensure_default()


def save_calendar(data: dict) -> None:
    data["updated_at"] = _now_iso()
    CALENDAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALENDAR_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_events(
    date_from: str | None = None,
    date_to: str | None = None,
    tag: str | None = None,
) -> list[dict]:
    """Return events with starts_at in [date_from, date_to]. Optional tag filters events that include that tag."""
    data = load_calendar()
    events = list(data.get("events", []))
    if not date_from and not date_to:
        start = datetime.utcnow() - timedelta(days=1)
        end = datetime.utcnow() + timedelta(days=120)
        date_from = start.isoformat() + "Z"
        date_to = end.isoformat() + "Z"

    def in_range(s: str) -> bool:
        if not s:
            return False
        if date_from and s < date_from:
            return False
        if date_to and s > date_to:
            return False
        return True

    def has_tag(ev: dict) -> bool:
        if not tag:
            return True
        tags = ev.get("tags") or []
        if not isinstance(tags, list):
            return False
        return tag in tags

    filtered = [e for e in events if in_range(e.get("starts_at", "")) and has_tag(e)]
    return sorted(filtered, key=lambda e: e.get("starts_at", ""))


def get_event(event_id: str) -> dict | None:
    for ev in load_calendar().get("events", []):
        if ev.get("id") == event_id:
            return ev
    return None


def add_event(
    *,
    kind: str,
    title: str,
    starts_at: str,
    ends_at: str | None = None,
    notes: str = "",
    draft_id: str | None = None,
    destination: str | None = None,
    alert_minutes_before: int | None = None,
    attachments: list[dict] | None = None,
    tags: list[str] | None = None,
    source: str = "user",
) -> dict:
    data = load_calendar()
    eid = str(uuid.uuid4())[:8]
    now = _now_iso()
    tag_list = [t.strip() for t in (tags or []) if isinstance(t, str) and t.strip()]
    ev = {
        "id": eid,
        "kind": kind,
        "title": title.strip(),
        "starts_at": starts_at.strip(),
        "ends_at": (ends_at or "").strip() or None,
        "notes": notes.strip(),
        "draft_id": draft_id,
        "destination": destination,
        "alert_minutes_before": alert_minutes_before,
        "attachments": attachments or [],
        "tags": tag_list,
        "source": source,
        "created_at": now,
        "updated_at": now,
    }
    data.setdefault("events", []).append(ev)
    save_calendar(data)
    return ev


def update_event(event_id: str, **fields) -> dict | None:
    data = load_calendar()
    events = data.get("events", [])
    for i, ev in enumerate(events):
        if ev.get("id") != event_id:
            continue
        for k, v in fields.items():
            if v is None and k in ev:
                ev.pop(k, None)
            elif v is not None:
                ev[k] = v
        ev["updated_at"] = _now_iso()
        events[i] = ev
        save_calendar(data)
        return ev
    return None


def delete_event(event_id: str) -> bool:
    data = load_calendar()
    events = data.get("events", [])
    new_events = [e for e in events if e.get("id") != event_id]
    if len(new_events) == len(events):
        return False
    data["events"] = new_events
    save_calendar(data)
    return True


def add_work_log_entry(
    *,
    text: str,
    status: str = "note",
    attachments: list[dict] | None = None,
    ingest: bool = True,
    tags: list[str] | None = None,
    source: str = "user",
) -> dict:
    data = load_calendar()
    wid = str(uuid.uuid4())[:8]
    now = _now_iso()
    entry = {
        "id": wid,
        "logged_at": now,
        "status": status,
        "text": text.strip(),
        "attachments": attachments or [],
        "ingest": bool(ingest),
        "tags": tags or [],
        "source": source,
        "created_at": now,
    }
    data.setdefault("work_log", []).insert(0, entry)
    save_calendar(data)
    return entry


def list_work_log(limit: int = 100) -> list[dict]:
    rows = load_calendar().get("work_log", [])
    return rows[:limit]


def sync_draft_schedule(
    draft_id: str,
    starts_at: str,
    title: str | None = None,
    *,
    tags: list[str] | None = None,
    merge_metadata: bool = True,
) -> tuple[dict, dict | None]:
    """Set draft metadata.scheduled_for and create or update a matching calendar event.

    Returns (draft_dict, event_dict).
    """
    from .store import get_draft, merge_draft_metadata

    draft = get_draft(draft_id)
    if not draft:
        raise ValueError("draft not found")

    if merge_metadata:
        merge_draft_metadata(draft_id, {"scheduled_for": starts_at.strip(), "calendar_synced": True})

    dest = (draft.get("metadata") or {}).get("destination", "")
    meta = draft.get("metadata") or {}
    tag_list: list[str] = []
    if tags:
        tag_list = [t.strip() for t in tags if isinstance(t, str) and t.strip()]
    elif meta.get("calendar_tags"):
        raw = meta["calendar_tags"]
        if isinstance(raw, list):
            tag_list = [str(t).strip() for t in raw if str(t).strip()]
        elif isinstance(raw, str) and raw.strip():
            tag_list = [x.strip() for x in raw.split(",") if x.strip()]
    t = title or strip_html_title(draft.get("content", ""))[:80] or f"Draft {draft_id}"

    data = load_calendar()
    events = data.get("events", [])
    existing = next((e for e in events if e.get("draft_id") == draft_id), None)
    if existing:
        final_tags = tag_list if tag_list else list(existing.get("tags") or [])
        updated = update_event(
            existing["id"],
            starts_at=starts_at.strip(),
            title=t,
            destination=dest or None,
            kind="post_schedule",
            tags=final_tags,
        )
        return get_draft(draft_id) or draft, updated

    ev = add_event(
        kind="post_schedule",
        title=t,
        starts_at=starts_at.strip(),
        draft_id=draft_id,
        destination=dest or None,
        tags=tag_list or None,
        source="user",
    )
    merge_draft_metadata(draft_id, {"calendar_event_id": ev["id"]})
    return get_draft(draft_id) or draft, ev


def strip_html_title(html: str) -> str:
    if not html:
        return ""
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    return " ".join(text.split())


def _ical_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _iso_to_ical_dt(iso: str) -> str | None:
    if not iso:
        return None
    s = iso.strip().rstrip("Z")
    try:
        if "T" not in s:
            return None
        date_part, time_part = s.split("T", 1)
        time_part = time_part.split(".")[0]
        ds = date_part.replace("-", "")
        tp = time_part.replace(":", "")
        if len(tp) == 4:
            tp = tp + "00"
        elif len(tp) == 5:
            tp = tp + "0"
        tp = (tp + "000000")[:6]
        return f"{ds}T{tp}Z"
    except Exception:
        return None


def events_to_ical(
    events: list[dict],
    *,
    calendar_name: str = "Agent-lab Master",
    draft_editor_base: str | None = None,
) -> str:
    """RFC 5545-ish iCalendar for subscribe-in-Apple-Google (reminders on phone/watch)."""
    import os

    base = draft_editor_base or os.environ.get("CALENDAR_PUBLIC_BASE_URL", "").rstrip("/")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//agent-lab//master_calendar//EN",
        f"X-WR-CALNAME:{_ical_escape(calendar_name)}",
        "CALSCALE:GREGORIAN",
    ]
    for ev in events:
        uid = f"{ev.get('id', 'ev')}@agent-lab"
        dt = _iso_to_ical_dt(ev.get("starts_at") or "")
        if not dt:
            continue
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}")
        lines.append(f"DTSTART:{dt}")
        lines.append(f"SUMMARY:{_ical_escape((ev.get('title') or 'Event')[:200])}")
        if ev.get("notes"):
            lines.append(f"DESCRIPTION:{_ical_escape((ev.get('notes') or '')[:2000])}")
        if base and ev.get("draft_id"):
            lines.append(f"URL;VALUE=URI:{base}/?highlightDraft={ev.get('draft_id')}")
        alert = ev.get("alert_minutes_before")
        if isinstance(alert, int) and alert > 0:
            lines.append("BEGIN:VALARM")
            lines.append("ACTION:DISPLAY")
            lines.append(f"DESCRIPTION:{_ical_escape(ev.get('title') or 'Reminder')}")
            lines.append(f"TRIGGER:-PT{alert}M")
            lines.append("END:VALARM")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
