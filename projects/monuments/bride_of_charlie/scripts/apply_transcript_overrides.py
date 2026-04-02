#!/usr/bin/env python3
"""
Apply transcript_overrides.json — human-curated fixes after STT + Neo4j + editorial regex.

Pipeline order:
  neo4j_corrections apply-dir → editorial_transcript_pass → **this script** → sync_transcript_hashes

Only items with status \"accepted\" are applied. Use Draft Editor (Transcripts tab) or edit JSON.

Usage:
  cd projects/monuments/bride_of_charlie
  python3 scripts/apply_transcript_overrides.py --dry-run
  python3 scripts/apply_transcript_overrides.py --apply
  python3 scripts/apply_transcript_overrides.py --apply --episode 6

This module is importable (preview_item, run_apply, load_store, save_store) for apps/draft_editor.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_STORE = PROJECT_DIR / "config" / "transcript_overrides.json"

_FLAG = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
}

DEFAULT_TIERS = ("inscription", "transcripts_corrected", "transcripts")


def load_store(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_STORE
    if not p.is_file():
        return {"version": 1, "items": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save_store(data: dict[str, Any], path: Path | None = None) -> None:
    p = path or DEFAULT_STORE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_item_id() -> str:
    return str(uuid.uuid4())[:12]


def paths_for_episode(project: Path, episode: int, tiers: list[str] | None) -> list[Path]:
    want = set(tiers or list(DEFAULT_TIERS))
    ep = int(episode)
    out: list[Path] = []
    if "inscription" in want:
        ins = project / "inscription" / f"episode_{ep:03d}_transcript.txt"
        if ins.is_file():
            out.append(ins)
    if "transcripts_corrected" in want:
        corr = project / "transcripts_corrected"
        if corr.is_dir():
            out.extend(sorted(corr.glob(f"episode_{ep:03d}_*.txt")))
    if "transcripts" in want:
        raw = project / "transcripts"
        if raw.is_dir():
            out.extend(sorted(raw.glob(f"episode_{ep:03d}_*.txt")))
    # Dedupe stable
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in out:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    return uniq


def apply_item_to_text(text: str, item: dict[str, Any]) -> tuple[str, int]:
    """Return (new_text, replacement_count)."""
    mode = (item.get("match_mode") or "literal").strip().lower()
    find = item.get("find") or ""
    replace = item.get("replace")
    if replace is None:
        replace = ""
    max_r = item.get("max_replacements")
    if max_r is not None:
        max_r = int(max_r)

    if mode == "literal":
        if not find:
            return text, 0
        n = 0
        cur = text
        limit = max_r if max_r is not None else cur.count(find)
        for _ in range(limit):
            if find not in cur:
                break
            cur = cur.replace(find, replace, 1)
            n += 1
        return cur, n

    if mode == "regex":
        if not find:
            return text, 0
        flags = 0
        for name in item.get("flags") or []:
            flags |= _FLAG.get(str(name).upper(), 0)
        rx = re.compile(find, flags)
        # count=0 → replace all (Python re)
        count_arg = 0 if max_r is None else max_r
        return rx.subn(replace, text, count=count_arg)

    raise ValueError(f"Unknown match_mode: {mode!r}")


def _match_in_text(text: str, item: dict[str, Any]) -> bool:
    mode = (item.get("match_mode") or "literal").strip().lower()
    find = item.get("find") or ""
    if mode == "literal":
        return bool(find) and find in text
    if mode == "regex":
        flags = 0
        for name in item.get("flags") or []:
            flags |= _FLAG.get(str(name).upper(), 0)
        return bool(re.search(find, text, flags))
    return False


def preview_item(
    project_dir: Path,
    item: dict[str, Any],
    *,
    store_path: Path | None = None,
) -> dict[str, Any] | None:
    """Simulate one item on first matching file; return preview dict or None."""
    ep = item.get("episode")
    if ep is None:
        return None
    tiers = item.get("tiers") or list(DEFAULT_TIERS)
    paths = paths_for_episode(project_dir, int(ep), tiers)
    for pth in paths:
        text = pth.read_text(encoding="utf-8")
        if not _match_in_text(text, item):
            continue
        new_text, n = apply_item_to_text(text, item)
        # Snippet around first match (literal)
        find = item.get("find") or ""
        mode = (item.get("match_mode") or "literal").strip().lower()
        idx = text.find(find) if mode == "literal" and find else -1
        if idx < 0 and mode == "regex":
            rf = 0
            for name in item.get("flags") or []:
                rf |= _FLAG.get(str(name).upper(), 0)
            m = re.search(find, text, rf)
            idx = m.start() if m else -1
        lo = max(0, idx - 120)
        hi = min(len(text), idx + 200) if idx >= 0 else min(400, len(text))
        clo = max(0, idx - 500) if idx >= 0 else 0
        chi = min(len(text), idx + 500) if idx >= 0 else min(1000, len(text))
        return {
            "file": str(pth.relative_to(project_dir)),
            "replacements": n,
            "match_offset": idx if idx >= 0 else None,
            "before_excerpt": text[lo:hi],
            "after_excerpt": new_text[lo:hi],
            "context_excerpt": text[clo:chi] if idx >= 0 else text[: min(1000, len(text))],
        }
    return {"file": None, "replacements": 0, "before_excerpt": "", "after_excerpt": "", "note": "no match in tier files"}


def run_apply(
    project_dir: Path | None = None,
    *,
    store_path: Path | None = None,
    dry_run: bool = False,
    episode_filter: int | None = None,
    item_id: str | None = None,
) -> dict[str, Any]:
    project_dir = project_dir or PROJECT_DIR
    data = load_store(store_path)
    items: list[dict[str, Any]] = list(data.get("items") or [])
    accepted = [
        it
        for it in items
        if (it.get("status") or "").strip().lower() == "accepted"
        and (episode_filter is None or int(it.get("episode", -1)) == episode_filter)
        and (item_id is None or it.get("id") == item_id)
    ]
    accepted.sort(key=lambda x: (int(x.get("priority", 0) or 0), items.index(x)))

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "files_touched": [],
        "total_replacements": 0,
        "items_applied": len(accepted),
    }

    # Group by file path
    from collections import defaultdict

    file_ops: dict[Path, list[dict[str, Any]]] = defaultdict(list)
    for it in accepted:
        ep = it.get("episode")
        if ep is None:
            continue
        tiers = it.get("tiers") or list(DEFAULT_TIERS)
        for pth in paths_for_episode(project_dir, int(ep), tiers):
            file_ops[pth].append(it)

    for pth, item_list in sorted(file_ops.items(), key=lambda x: str(x[0])):
        text = pth.read_text(encoding="utf-8")
        original = text
        n_file = 0
        for it in item_list:
            text, c = apply_item_to_text(text, it)
            n_file += c
        if text != original:
            report["total_replacements"] += n_file
            rel = str(pth.relative_to(project_dir))
            report["files_touched"].append({"path": rel, "replacements": n_file})
            if not dry_run:
                pth.write_text(text, encoding="utf-8")

    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply transcript_overrides.json")
    ap.add_argument("--apply", action="store_true", help="Write files (default is dry-run if neither flag)")
    ap.add_argument("--dry-run", action="store_true", help="Print plan only")
    ap.add_argument("--episode", type=int, default=None, help="Only items for this episode")
    ap.add_argument("--id", dest="item_id", default=None, help="Only this override id")
    ap.add_argument("--store", type=Path, default=None, help="Override JSON path")
    args = ap.parse_args()
    dry = args.dry_run or not args.apply
    rep = run_apply(
        store_path=args.store,
        dry_run=dry,
        episode_filter=args.episode,
        item_id=args.item_id,
    )
    print("[transcript_overrides]", "dry-run" if dry else "apply", rep)
    for ft in rep.get("files_touched", []):
        print(f"  {ft['path']}: {ft['replacements']} replacement(s)")
    if rep.get("total_replacements", 0) == 0 and rep.get("items_applied", 0) > 0:
        print("  (no file changes — find text may already match target or patterns missed)")
    return 0


# --- helpers for Draft Editor API ---


def validate_item_body(body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Normalize a new/patched item; return (item, error)."""
    try:
        ep = int(body.get("episode"))
    except (TypeError, ValueError):
        return None, "episode must be an integer"
    find = (body.get("find") or "").strip()
    if not find:
        return None, "find is required"
    replace = body.get("replace")
    if replace is None:
        replace = ""
    if not isinstance(replace, str):
        replace = str(replace)
    mode = (body.get("match_mode") or "literal").strip().lower()
    if mode not in ("literal", "regex"):
        return None, "match_mode must be literal or regex"
    tiers = body.get("tiers")
    if tiers is not None and not isinstance(tiers, list):
        return None, "tiers must be a list of strings"
    raw_flags = body.get("flags")
    if raw_flags is None:
        raw_flags = []
    if not isinstance(raw_flags, list):
        return None, "flags must be a list of strings (e.g. IGNORECASE)"
    item: dict[str, Any] = {
        "id": (body.get("id") or "").strip() or new_item_id(),
        "episode": ep,
        "status": (body.get("status") or "proposed").strip().lower(),
        "match_mode": mode,
        "find": find,
        "replace": replace,
        "note": (body.get("note") or "").strip(),
        "priority": int(body.get("priority") or 0),
        "tiers": tiers if tiers else list(DEFAULT_TIERS),
        "flags": [str(x) for x in raw_flags],
    }
    if body.get("max_replacements") is not None:
        item["max_replacements"] = int(body.get("max_replacements"))
    if item["status"] not in ("proposed", "accepted", "rejected"):
        return None, "status must be proposed, accepted, or rejected"
    if mode == "regex":
        try:
            flags = 0
            for name in item["flags"]:
                flags |= _FLAG.get(str(name).upper(), 0)
            re.compile(find, flags)
        except re.error as e:
            return None, f"invalid regex: {e}"
    return item, None


def upsert_item(store_path: Path | None, item: dict[str, Any]) -> dict[str, Any]:
    data = load_store(store_path)
    items: list[dict[str, Any]] = list(data.get("items") or [])
    iid = item["id"]
    now = _now_iso()
    found = False
    for i, it in enumerate(items):
        if it.get("id") == iid:
            prev = dict(it)
            merged = {**prev, **item}
            merged["updated_at"] = now
            merged.setdefault("created_at", prev.get("created_at", now))
            items[i] = merged
            found = True
            break
    if not found:
        item["created_at"] = now
        item["updated_at"] = now
        items.append(item)
    data["items"] = items
    save_store(data, store_path)
    return data


def delete_item(item_id: str, store_path: Path | None = None) -> bool:
    data = load_store(store_path)
    items = [it for it in (data.get("items") or []) if it.get("id") != item_id]
    if len(items) == len(data.get("items") or []):
        return False
    data["items"] = items
    save_store(data, store_path)
    return True


def _proposed_replace_signatures(items: list[dict[str, Any]]) -> set[tuple[Any, ...]]:
    out: set[tuple[Any, ...]] = set()
    for x in items:
        if (x.get("status") or "").strip().lower() != "proposed":
            continue
        try:
            ep = int(x.get("episode", -1))
        except (TypeError, ValueError):
            continue
        find = (x.get("find") or "").strip()
        repl = x.get("replace")
        if repl is None:
            repl = ""
        if not isinstance(repl, str):
            repl = str(repl)
        mode = (x.get("match_mode") or "literal").strip().lower()
        out.add((ep, find, repl, mode))
    return out


def bulk_propose_items(
    bodies: list[dict[str, Any]],
    *,
    store_path: Path | None = None,
    dedupe: bool = True,
) -> dict[str, Any]:
    """
    Append multiple proposed overrides (e.g. from Draft Editor heuristic / LLM scan).
    Each body: episode, find, replace, optional note, match_mode, tiers, flags, priority.
    """
    data = load_store(store_path)
    items_list: list[dict[str, Any]] = list(data.get("items") or [])
    sigs = _proposed_replace_signatures(items_list) if dedupe else set()
    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for raw in bodies:
        if not isinstance(raw, dict):
            skipped.append({"error": "not_an_object"})
            continue
        merged = {**raw, "status": "proposed"}
        item, err = validate_item_body(merged)
        if err:
            skipped.append({"error": err, "find_preview": str(raw.get("find", ""))[:100]})
            continue
        key = (item["episode"], item["find"], item["replace"], item["match_mode"])
        if dedupe and key in sigs:
            skipped.append(
                {"error": "duplicate_proposed", "find_preview": item["find"][:100]}
            )
            continue
        data = upsert_item(store_path, item)
        items_list = list(data.get("items") or [])
        sigs.add(key)
        created.append(item)

    return {
        "ok": True,
        "created_count": len(created),
        "skipped_count": len(skipped),
        "created": created,
        "skipped": skipped,
        "items": data.get("items", []),
    }


if __name__ == "__main__":
    sys.exit(main())
