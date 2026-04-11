#!/usr/bin/env python3
"""
Apply transcript_overrides.json — human-curated fixes after STT + Neo4j + editorial regex.

Pipeline order:
  neo4j_corrections apply-dir → editorial_transcript_pass → **this script** → sync_transcript_hashes

Only items with status \"accepted\" are applied. Use Draft Editor (Transcripts tab) or edit JSON.

Optional per item: ``apply_all_episodes`` (bool) — when true, Accept/apply runs the same find/replace on
every episode file for the selected tiers (inscription + corrected + raw as configured).

Prune stale queue rows:

```bash
python3 scripts/apply_transcript_overrides.py --prune-status proposed
python3 scripts/apply_transcript_overrides.py --prune-status proposed --confirm-prune
```

Usage:
  cd projects/monuments/bride_of_charlie
  python3 scripts/apply_transcript_overrides.py --dry-run
  python3 scripts/apply_transcript_overrides.py --apply
  python3 scripts/apply_transcript_overrides.py --apply --episode 6
  python3 scripts/apply_transcript_overrides.py --verify-inscription
  python3 scripts/apply_transcript_overrides.py --verify-inscription --episode 1

This module is importable (preview_item, run_apply, load_store, save_store) for apps/draft_editor.
"""

from __future__ import annotations

import argparse
import json
import re
import string
import sys
import unicodedata
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


def _truthy(val: Any) -> bool:
    if val is True:
        return True
    if isinstance(val, (int, float)) and val == 1:
        return True
    if isinstance(val, str) and val.strip().lower() in ("1", "true", "yes", "on"):
        return True
    return False


_LITERAL_NOT_FOLLOWED_BY_MAX = 64
_LITERAL_NFB_MAX_PARTS = 8


def _literal_next_char_bypasses_not_followed_by(ch: str) -> bool:
    """If True, ``literal_not_followed_by`` does not apply (suffix is only checked vs letters/digits/etc.)."""
    if not ch:
        return False
    if ch.isspace():
        return True
    if ch in string.punctuation:
        return True
    # Curly quotes, dashes, etc.
    return unicodedata.category(ch).startswith("P")


def literal_require_ws_or_punct_after(item: dict[str, Any]) -> bool:
    """
    When True (literal mode only), only count/apply ``find`` where the next character is
    end-of-text, whitespace, or punctuation (same classification as
    :func:`_literal_next_char_bypasses_not_followed_by`). Generic way to avoid matching a short
    literal that is only a prefix of a longer token (e.g. name truncation vs full spelling).
    """
    if (item.get("match_mode") or "literal").strip().lower() != "literal":
        return False
    return _truthy(item.get("literal_require_ws_or_punct_after"))


def _after_find_is_ws_punct_or_eof(text: str, find_end: int) -> bool:
    """True if ``find_end`` is at EOF or ``text[find_end]`` is whitespace/punctuation (Unicode P*)."""
    if find_end < 0:
        return False
    if find_end >= len(text):
        return True
    return _literal_next_char_bypasses_not_followed_by(text[find_end])


def _parse_literal_not_followed_by_raw(raw: str) -> list[str]:
    """Split/comma-trim suffix list for ``literal_not_followed_by`` (max parts / length per part)."""
    raw = raw.strip()
    if not raw:
        return []
    out: list[str] = []
    for part in raw.split(","):
        p = part.strip()[:_LITERAL_NOT_FOLLOWED_BY_MAX]
        if p:
            out.append(p)
        if len(out) >= _LITERAL_NFB_MAX_PARTS:
            break
    return out


def literal_not_followed_by_suffixes(item: dict[str, Any]) -> list[str]:
    """
    When non-empty (literal mode only), do not count or apply a match if ``Find`` is immediately
    followed by **any** of these substrings (case-insensitive).

    **Never** applies when the character right after ``Find`` is whitespace or punctuation
    (e.g. ``Nicole Rothst `` or ``Nicole Rothst,``) — those always count, even if a suffix is ``ein``.

    Field ``literal_not_followed_by`` may be **comma-separated** (e.g. ``ein,stein``) so one row can
    skip both ``Nicole Rothstein`` and ``Nicole Rothststein`` while still matching plain ``Nicole Rothst``.

    Also accepts legacy ``literal_guard_suffix`` in stored JSON (single suffix).
    """
    if (item.get("match_mode") or "literal").strip().lower() != "literal":
        return []
    raw = (item.get("literal_not_followed_by") or item.get("literal_guard_suffix") or "").strip()
    return _parse_literal_not_followed_by_raw(raw)


def literal_not_followed_by_suffix(item: dict[str, Any]) -> str | None:
    """First suffix only; prefer :func:`literal_not_followed_by_suffixes` for multi-suffix rules."""
    s = literal_not_followed_by_suffixes(item)
    return s[0] if s else None


def _literal_suffix_excludes_match(text: str, find_end: int, suf: str) -> bool:
    """
    True if this occurrence should be dropped (suffix matches at ``find_end``).
    False if ``find_end`` is past EOF, or the next character is whitespace or punctuation
    (suffix rule skipped).
    """
    if not suf or find_end < 0:
        return False
    if find_end >= len(text):
        return False
    if _literal_next_char_bypasses_not_followed_by(text[find_end]):
        return False
    if find_end + len(suf) > len(text):
        return False
    return text[find_end : find_end + len(suf)].lower() == suf.lower()


def _literal_suffixes_exclude_match(text: str, find_end: int, suffixes: list[str]) -> bool:
    return any(_literal_suffix_excludes_match(text, find_end, s) for s in suffixes)


def _literal_guard_rejects_at(text: str, end: int, item: dict[str, Any]) -> bool:
    """True if a match ending at ``end`` (start of trailing text) must be skipped."""
    suffixes = literal_not_followed_by_suffixes(item)
    if not suffixes:
        return False
    return _literal_suffixes_exclude_match(text, end, suffixes)


def iter_literal_match_starts(text: str, find: str, item: dict[str, Any]) -> list[int]:
    """Start indices of each literal match, respecting boundary and ``literal_not_followed_by`` when set."""
    find_s = str(find)
    if not find_s:
        return []
    suffixes = literal_not_followed_by_suffixes(item)
    need_boundary = literal_require_ws_or_punct_after(item)
    out: list[int] = []
    start = 0
    while True:
        pos = text.find(find_s, start)
        if pos < 0:
            break
        end = pos + len(find_s)
        if need_boundary and not _after_find_is_ws_punct_or_eof(text, end):
            start = pos + max(1, len(find_s))
            continue
        if suffixes and _literal_suffixes_exclude_match(text, end, suffixes):
            start = pos + max(1, len(find_s))
            continue
        out.append(pos)
        start = pos + max(1, len(find_s))
    return out


def list_all_episode_numbers(project: Path) -> list[int]:
    """Episode indices that appear under inscription / transcripts_corrected / transcripts."""
    nums: set[int] = set()
    ins = project / "inscription"
    if ins.is_dir():
        for p in ins.glob("episode_*_transcript.txt"):
            m = re.search(r"episode_(\d+)_transcript\.txt$", p.name, re.I)
            if m:
                nums.add(int(m.group(1)))
    for sub_name in ("transcripts_corrected", "transcripts"):
        sub = project / sub_name
        if sub.is_dir():
            for p in sub.glob("episode_*_*.txt"):
                m = re.search(r"episode_(\d+)", p.name, re.I)
                if m:
                    nums.add(int(m.group(1)))
    return sorted(nums)


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

    mso = item.get("match_start_offset")
    if mso is not None:
        try:
            pos = int(mso)
        except (TypeError, ValueError):
            pos = None
        if pos is not None and pos >= 0:
            if mode == "literal":
                if not find:
                    return text, 0
                end = pos + len(find)
                if end > len(text) or text[pos:end] != find:
                    return text, 0
                if _literal_guard_rejects_at(text, end, item):
                    return text, 0
                if literal_require_ws_or_punct_after(item) and not _after_find_is_ws_punct_or_eof(
                    text, end
                ):
                    return text, 0
                return text[:pos] + replace + text[end:], 1
            if mode == "regex":
                if not find:
                    return text, 0
                flags = 0
                for name in item.get("flags") or []:
                    flags |= _FLAG.get(str(name).upper(), 0)
                rx = re.compile(find, flags)
                for m in rx.finditer(text):
                    if m.start() == pos:
                        new_t = text[: m.start()] + m.expand(replace) + text[m.end() :]
                        return new_t, 1
                return text, 0

    if mode == "literal":
        if not find:
            return text, 0
        if literal_not_followed_by_suffixes(item) or literal_require_ws_or_punct_after(item):
            starts = iter_literal_match_starts(text, find, item)
            if max_r is not None:
                starts = starts[: int(max_r)]
            cur = text
            for pos in reversed(starts):
                end = pos + len(find)
                cur = cur[:pos] + replace + cur[end:]
            return cur, len(starts)
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
    mso = item.get("match_start_offset")
    if mso is not None:
        try:
            pos = int(mso)
        except (TypeError, ValueError):
            pos = None
        if pos is not None and pos >= 0:
            if mode == "literal":
                if not find:
                    return False
                end = pos + len(find)
                if end > len(text) or text[pos:end] != find:
                    return False
                if _literal_guard_rejects_at(text, end, item):
                    return False
                if literal_require_ws_or_punct_after(item) and not _after_find_is_ws_punct_or_eof(
                    text, end
                ):
                    return False
                return True
            if mode == "regex":
                if not find:
                    return False
                try:
                    flags = 0
                    for name in item.get("flags") or []:
                        flags |= _FLAG.get(str(name).upper(), 0)
                    for m in re.finditer(find, text, flags):
                        if m.start() == pos:
                            return True
                    return False
                except re.error:
                    return False
    if mode == "literal":
        if not find:
            return False
        if literal_not_followed_by_suffixes(item) or literal_require_ws_or_punct_after(item):
            return bool(iter_literal_match_starts(text, find, item))
        return find in text
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
    tiers = item.get("tiers") or list(DEFAULT_TIERS)
    if _truthy(item.get("apply_all_episodes")):
        eps = list_all_episode_numbers(project_dir)
        paths: list[Path] = []
        for epn in eps:
            paths.extend(paths_for_episode(project_dir, int(epn), tiers))
    else:
        ep = item.get("episode")
        if ep is None:
            return None
        paths = paths_for_episode(project_dir, int(ep), tiers)
    for pth in paths:
        text = pth.read_text(encoding="utf-8")
        if not _match_in_text(text, item):
            continue
        new_text, n = apply_item_to_text(text, item)
        # Snippet around first match (literal)
        find = item.get("find") or ""
        mode = (item.get("match_mode") or "literal").strip().lower()
        mso = item.get("match_start_offset")
        idx = -1
        if mso is not None:
            try:
                idx = int(mso)
            except (TypeError, ValueError):
                idx = -1
        if idx < 0:
            if mode == "literal" and find:
                _starts = iter_literal_match_starts(text, find, item)
                idx = _starts[0] if _starts else -1
            else:
                idx = -1
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
    accepted: list[dict[str, Any]] = []
    for it in items:
        if (it.get("status") or "").strip().lower() != "accepted":
            continue
        if item_id is not None and it.get("id") != item_id:
            continue
        if episode_filter is not None:
            try:
                iep = int(it.get("episode", -1))
            except (TypeError, ValueError):
                iep = -1
            if iep != episode_filter and not _truthy(it.get("apply_all_episodes")):
                continue
        accepted.append(it)
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
        tiers = it.get("tiers") or list(DEFAULT_TIERS)
        if _truthy(it.get("apply_all_episodes")):
            if episode_filter is not None:
                eps = [int(episode_filter)]
            else:
                eps = list_all_episode_numbers(project_dir)
            for epn in eps:
                for pth in paths_for_episode(project_dir, int(epn), tiers):
                    file_ops[pth].append(it)
            continue
        ep = it.get("episode")
        if ep is None:
            continue
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


def count_find_occurrences(text: str, item: dict[str, Any]) -> tuple[int, str | None]:
    """Count how many times this item's find matches in text. Returns (count, regex_error)."""
    find = item.get("find") or ""
    mode = (item.get("match_mode") or "literal").strip().lower()
    mso = item.get("match_start_offset")
    if mso is not None:
        try:
            pos = int(mso)
        except (TypeError, ValueError):
            pos = None
        if pos is not None and pos >= 0:
            if mode == "literal":
                if not find:
                    return 0, None
                end = pos + len(find)
                if end > len(text) or text[pos:end] != find:
                    return 0, None
                if _literal_guard_rejects_at(text, end, item):
                    return 0, None
                if literal_require_ws_or_punct_after(item) and not _after_find_is_ws_punct_or_eof(
                    text, end
                ):
                    return 0, None
                return 1, None
            if mode == "regex":
                if not find:
                    return 0, None
                try:
                    flags = 0
                    for name in item.get("flags") or []:
                        flags |= _FLAG.get(str(name).upper(), 0)
                    for m in re.finditer(find, text, flags):
                        if m.start() == pos:
                            return 1, None
                    return 0, None
                except re.error as e:
                    return 0, str(e)
    if not find:
        return 0, None
    if mode == "literal":
        if literal_not_followed_by_suffixes(item) or literal_require_ws_or_punct_after(item):
            return len(iter_literal_match_starts(text, find, item)), None
        return text.count(find), None
    if mode == "regex":
        try:
            flags = 0
            for name in item.get("flags") or []:
                flags |= _FLAG.get(str(name).upper(), 0)
            return sum(1 for _ in re.finditer(find, text, flags)), None
        except re.error as e:
            return 0, str(e)
    return 0, f"unknown match_mode: {mode!r}"


MATCH_OCCURRENCE_DETAIL_MAX = 40
MATCH_OCCURRENCE_CONTEXT_CHARS = 120


def match_occurrences_detail(
    text: str, item: dict[str, Any], *, max_hits: int = MATCH_OCCURRENCE_DETAIL_MAX
) -> list[dict[str, Any]]:
    """
    For each match of ``item``'s find in ``text``, return line number and a short context slice
    (for UI review — e.g. disambiguate literal \"France\" vs a name).
    """
    find_raw = item.get("find") or ""
    mode = (item.get("match_mode") or "literal").strip().lower()
    ctx = MATCH_OCCURRENCE_CONTEXT_CHARS
    out: list[dict[str, Any]] = []
    if not find_raw or max_hits <= 0:
        return out
    mso = item.get("match_start_offset")
    if mso is not None:
        try:
            pos = int(mso)
        except (TypeError, ValueError):
            pos = None
        if pos is not None and pos >= 0:
            mc, err = count_find_occurrences(text, item)
            if err or mc != 1:
                return out
            lo = max(0, pos - ctx)
            hi = min(len(text), pos + len(str(find_raw)) + ctx)
            line_no = text.count("\n", 0, pos) + 1
            one: dict[str, Any] = {
                "line": line_no,
                "start": pos,
                "context": text[lo:hi],
            }
            if mode == "regex":
                try:
                    flags = 0
                    for name in item.get("flags") or []:
                        flags |= _FLAG.get(str(name).upper(), 0)
                    for m in re.finditer(find_raw, text, flags):
                        if m.start() == pos:
                            one["matched"] = m.group(0)
                            break
                except re.error:
                    return out
            return [one]
    if mode == "literal":
        find = str(find_raw)
        if not find:
            return out
        for pos in iter_literal_match_starts(text, find, item):
            if len(out) >= max_hits:
                break
            lo = max(0, pos - ctx)
            hi = min(len(text), pos + len(find) + ctx)
            line_no = text.count("\n", 0, pos) + 1
            out.append({"line": line_no, "start": pos, "context": text[lo:hi]})
        return out
    if mode == "regex":
        try:
            flags = 0
            for name in item.get("flags") or []:
                flags |= _FLAG.get(str(name).upper(), 0)
            for m in re.finditer(find_raw, text, flags):
                if len(out) >= max_hits:
                    break
                pos = m.start()
                lo = max(0, pos - ctx)
                hi = min(len(text), m.end() + ctx)
                line_no = text.count("\n", 0, pos) + 1
                out.append(
                    {
                        "line": line_no,
                        "start": pos,
                        "context": text[lo:hi],
                        "matched": m.group(0),
                    }
                )
        except re.error:
            return out
        return out
    return out


def expand_whitespace_token_containing(text: str, start: int, find: str) -> str | None:
    """
    Maximal whitespace-delimited substring that contains [start, start + len(find)),
    if and only if ``text[start : start + len(find)] == find``.
    Used when the queue row stores a short Find (prefix) but the inscription continues
    with more characters in the same token (e.g. STT garbage).
    """
    if not find:
        return None
    if start < 0 or start + len(find) > len(text):
        return None
    if text[start : start + len(find)] != find:
        return None
    lo = start
    while lo > 0 and text[lo - 1] not in "\n\r\t ":
        lo -= 1
    hi = start + len(find)
    while hi < len(text) and text[hi] not in "\n\r\t ":
        hi += 1
    return text[lo:hi]


def suggested_find_for_occurrence(
    project_dir: Path,
    item: dict[str, Any],
    occ_idx: int,
) -> dict[str, Any]:
    """
    For Draft Editor **Scope**: compute Find text from the inscription at a verify occurrence,
    expanding to the full whitespace-delimited token when the stored Find is only a prefix.

    Re-runs verify as if ``match_start_offset`` were unset so occurrence indices match the verify panel.
    """
    out: dict[str, Any] = {"ok": False}
    base = dict(item)
    base.pop("match_start_offset", None)
    row = verify_item_vs_inscription(project_dir, base)
    if row.get("regex_error"):
        out["error"] = "regex_error"
        out["detail"] = row.get("regex_error")
        return out
    occs = list(row.get("occurrences") or [])
    if occ_idx < 0 or occ_idx >= len(occs):
        out["error"] = "occurrence_index out of range"
        out["count"] = len(occs)
        return out
    occ = occs[occ_idx]
    start = occ.get("start")
    if start is None:
        out["error"] = "occurrence missing start"
        return out
    try:
        start_i = int(start)
    except (TypeError, ValueError):
        out["error"] = "invalid start"
        return out

    if _truthy(item.get("apply_all_episodes")):
        ep = occ.get("episode")
        if ep is None:
            out["error"] = "occurrence missing episode for apply-all item"
            return out
        try:
            ep_int = int(ep)
        except (TypeError, ValueError):
            out["error"] = "invalid episode on occurrence"
            return out
    else:
        ep = row.get("episode")
        if ep is None:
            out["error"] = "invalid episode"
            return out
        try:
            ep_int = int(ep)
        except (TypeError, ValueError):
            out["error"] = "invalid episode"
            return out

    ins = project_dir / "inscription" / f"episode_{ep_int:03d}_transcript.txt"
    if not ins.is_file():
        out["error"] = "inscription_missing"
        out["path"] = str(ins.relative_to(project_dir))
        return out

    text = ins.read_text(encoding="utf-8")
    find = item.get("find") or ""
    mode = (item.get("match_mode") or "literal").strip().lower()

    if not find:
        out["error"] = "empty find"
        return out

    if mode == "literal":
        sug = expand_whitespace_token_containing(text, start_i, find)
        if sug is None:
            out["error"] = "find_mismatch_at_occurrence"
            out["hint"] = (
                "Stored Find does not match the inscription at this occurrence. "
                "Re-run Verify vs inscription or adjust Find."
            )
            return out
        out["ok"] = True
        out["start"] = start_i
        out["episode"] = ep_int
        out["find_before"] = find
        out["suggested_find"] = sug
        out["changed"] = sug != find
        return out

    if mode == "regex":
        try:
            flags = 0
            for name in item.get("flags") or []:
                flags |= _FLAG.get(str(name).upper(), 0)
            rx = re.compile(find, flags)
        except re.error as e:
            out["error"] = "invalid regex"
            out["detail"] = str(e)
            return out
        matched: str | None = None
        for m in rx.finditer(text):
            if m.start() == start_i:
                matched = m.group(0)
                break
        if matched is None:
            out["error"] = "regex_match_not_at_occurrence"
            out["hint"] = "Re-run Verify vs inscription"
            return out
        sug = expand_whitespace_token_containing(text, start_i, matched)
        if sug is None:
            out["error"] = "internal_match_mismatch"
            return out
        out["ok"] = True
        out["start"] = start_i
        out["episode"] = ep_int
        out["find_before"] = find
        out["suggested_find"] = sug
        out["changed"] = sug != find
        return out

    out["error"] = "unknown match_mode"
    return out


def _verify_item_vs_inscription_all_episodes(project_dir: Path, item: dict[str, Any]) -> dict[str, Any]:
    """Sum inscription matches across every episode file (apply_all_episodes items)."""
    iid = str(item.get("id") or "")
    status = (item.get("status") or "").strip().lower()
    try:
        ref_ep = int(item.get("episode", -1))
    except (TypeError, ValueError):
        ref_ep = -1
    tiers = item.get("tiers") or list(DEFAULT_TIERS)
    tier_l = {str(t).strip().lower() for t in tiers}
    targets_ins = "inscription" in tier_l
    base: dict[str, Any] = {
        "id": iid,
        "status": status,
        "episode": ref_ep,
        "apply_all_episodes": True,
        "inscription_path": "(all episodes)",
        "inscription_missing": False,
        "targets_inscription": targets_ins,
        "match_count": 0,
        "replacements_if_applied_now": 0,
        "regex_error": None,
        "find_preview": (item.get("find") or "")[:120],
        "episodes_with_hits": [],
        "occurrences": [],
        "scoped_match_start_offset": None,
    }
    mso_raw = item.get("match_start_offset")
    if mso_raw is not None:
        try:
            mso_a = int(mso_raw)
        except (TypeError, ValueError):
            mso_a = None
        if mso_a is not None and mso_a >= 0:
            base["scoped_match_start_offset"] = mso_a

    if not targets_ins:
        base["note"] = "tiers omit inscription — inscription totals not computed"
        return base

    eps = list_all_episode_numbers(project_dir)
    total_mc = 0
    total_rep = 0
    hits: list[int] = []
    all_occ: list[dict[str, Any]] = []
    occ_budget = MATCH_OCCURRENCE_DETAIL_MAX
    rx_err: str | None = None
    for epn in eps:
        ins = project_dir / "inscription" / f"episode_{epn:03d}_transcript.txt"
        if not ins.is_file():
            continue
        text = ins.read_text(encoding="utf-8")
        list_item = _item_for_inscription_verify_listing(item)
        mc, err = count_find_occurrences(text, list_item)
        if err:
            rx_err = err
            break
        if mc > 0:
            hits.append(epn)
            total_mc += mc
            try:
                _, nrep = apply_item_to_text(text, item)
            except re.error as e:
                rx_err = str(e)
                break
            total_rep += nrep
            if occ_budget > 0:
                ods = match_occurrences_detail(text, list_item, max_hits=occ_budget)
                for o in ods:
                    ox = dict(o)
                    ox["episode"] = epn
                    all_occ.append(ox)
                occ_budget -= len(ods)
    base["regex_error"] = rx_err
    if rx_err:
        return base
    base["match_count"] = total_mc
    base["replacements_if_applied_now"] = total_rep
    base["episodes_with_hits"] = hits
    base["inscription_missing"] = len(eps) == 0
    base["occurrences"] = all_occ
    return base


def _item_for_inscription_verify_listing(item: dict[str, Any]) -> dict[str, Any]:
    """
    Clone without ``match_start_offset`` so verify lists **all** inscription hits for triage.
    Scoped Accept still uses the original item (one replacement at ``match_start_offset``).
    """
    out = dict(item)
    out.pop("match_start_offset", None)
    return out


def verify_item_vs_inscription(project_dir: Path, item: dict[str, Any]) -> dict[str, Any]:
    """
    Check whether item.find matches the episode inscription file (read-only).
    Use after LLM queueing: match_count 0 usually means typo, wrong tier, or already applied.
    """
    if _truthy(item.get("apply_all_episodes")):
        return _verify_item_vs_inscription_all_episodes(project_dir, item)
    iid = str(item.get("id") or "")
    status = (item.get("status") or "").strip().lower()
    try:
        ep = int(item.get("episode", -1))
    except (TypeError, ValueError):
        return {
            "id": iid,
            "status": status,
            "episode": None,
            "error": "invalid_episode",
            "inscription_path": None,
            "inscription_missing": False,
            "targets_inscription": False,
            "match_count": 0,
            "replacements_if_applied_now": 0,
            "regex_error": None,
            "find_preview": "",
            "occurrences": [],
        }

    ins = project_dir / "inscription" / f"episode_{ep:03d}_transcript.txt"
    rel = str(ins.relative_to(project_dir))
    tiers = item.get("tiers") or list(DEFAULT_TIERS)
    tier_l = {str(t).strip().lower() for t in tiers}
    targets_ins = "inscription" in tier_l

    base: dict[str, Any] = {
        "id": iid,
        "status": status,
        "episode": ep,
        "inscription_path": rel,
        "inscription_missing": not ins.is_file(),
        "targets_inscription": targets_ins,
        "match_count": 0,
        "replacements_if_applied_now": 0,
        "regex_error": None,
        "find_preview": (item.get("find") or "")[:120],
        "occurrences": [],
        "scoped_match_start_offset": None,
    }

    if not ins.is_file():
        return base

    text = ins.read_text(encoding="utf-8")
    list_item = _item_for_inscription_verify_listing(item)
    mso = item.get("match_start_offset")
    if mso is not None:
        try:
            mso_i = int(mso)
        except (TypeError, ValueError):
            mso_i = None
        if mso_i is not None and mso_i >= 0:
            base["scoped_match_start_offset"] = mso_i

    match_count, rx_err = count_find_occurrences(text, list_item)
    base["match_count"] = match_count
    base["regex_error"] = rx_err
    if rx_err:
        return base
    try:
        _, n_apply = apply_item_to_text(text, item)
    except re.error as e:
        base["regex_error"] = str(e)
        return base
    base["replacements_if_applied_now"] = n_apply
    base["occurrences"] = match_occurrences_detail(text, list_item)
    return base


def run_verify_queue_vs_inscription(
    project_dir: Path | None = None,
    *,
    store_path: Path | None = None,
    episode_filter: int | None = None,
    statuses: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    """
    For each queue item in the given statuses, count matches in that episode's inscription file.
    Default statuses: proposed, accepted.
    """
    project_dir = project_dir or PROJECT_DIR
    want: set[str] = set(statuses) if statuses is not None else {"proposed", "accepted"}
    data = load_store(store_path)
    items: list[dict[str, Any]] = list(data.get("items") or [])
    rows: list[dict[str, Any]] = []
    for it in items:
        st = (it.get("status") or "").strip().lower()
        if st not in want:
            continue
        if episode_filter is not None:
            try:
                iep = int(it.get("episode", -1))
            except (TypeError, ValueError):
                iep = -1
            if iep != episode_filter and not _truthy(it.get("apply_all_episodes")):
                continue
        rows.append(verify_item_vs_inscription(project_dir, it))

    rows.sort(key=lambda r: (r.get("episode") is None, r.get("episode") or 0, r.get("status") or "", r.get("id") or ""))

    summary = {
        "items_checked": len(rows),
        "missing_inscription_file": sum(1 for r in rows if r.get("inscription_missing")),
        "regex_errors": sum(1 for r in rows if r.get("regex_error")),
        "zero_matches_in_file": sum(
            1
            for r in rows
            if not r.get("inscription_missing")
            and not r.get("regex_error")
            and not r.get("error")
            and int(r.get("match_count") or 0) == 0
        ),
        "has_at_least_one_match": sum(
            1
            for r in rows
            if not r.get("inscription_missing")
            and not r.get("regex_error")
            and int(r.get("match_count") or 0) > 0
        ),
        "not_targeting_inscription": sum(1 for r in rows if r.get("targets_inscription") is False),
        "invalid_episode": sum(1 for r in rows if r.get("error") == "invalid_episode"),
    }
    summary["all_find_strings_match"] = summary["items_checked"] > 0 and summary["zero_matches_in_file"] == 0

    return {
        "summary": summary,
        "items": rows,
        "statuses_filtered": sorted(want),
        "episode_filter": episode_filter,
    }


def queued_literal_finds_for_episode(
    project_dir: Path,
    episode: int,
    *,
    store_path: Path | None = None,
) -> set[str]:
    """Literal find strings already proposed/accepted for this episode (or global all-episode rows)."""
    del project_dir  # reserved for future path-scoped rules
    data = load_store(store_path)
    out: set[str] = set()
    for it in data.get("items") or []:
        st = (it.get("status") or "").strip().lower()
        if st not in ("proposed", "accepted"):
            continue
        if (it.get("match_mode") or "literal").strip().lower() != "literal":
            continue
        find = (it.get("find") or "").strip()
        if not find:
            continue
        if _truthy(it.get("apply_all_episodes")):
            out.add(find)
            continue
        try:
            if int(it.get("episode", -1)) == int(episode):
                out.add(find)
        except (TypeError, ValueError):
            continue
    return out


def filter_scan_findings_against_queue_and_file(
    project_dir: Path,
    episode: int,
    rows: list[dict[str, Any]],
    *,
    text_key: str,
    store_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Drop scan/LLM rows whose text is already in the override queue (literal),
    or whose text no longer appears in the inscription file (already fixed).
    """
    queued = queued_literal_finds_for_episode(project_dir, episode, store_path=store_path)
    ins_path = project_dir / "inscription" / f"episode_{int(episode):03d}_transcript.txt"
    inscribed = ins_path.read_text(encoding="utf-8") if ins_path.is_file() else ""
    kept: list[dict[str, Any]] = []
    stats = {"dropped_queued_duplicate": 0, "dropped_absent_from_inscription": 0}
    for row in rows:
        if not isinstance(row, dict):
            kept.append(row)
            continue
        if row.get("error") or row.get("raw_tail"):
            kept.append(row)
            continue
        text = (row.get(text_key) or "").strip()
        if not text:
            kept.append(row)
            continue
        if text in queued:
            stats["dropped_queued_duplicate"] += 1
            continue
        if inscribed and text not in inscribed:
            stats["dropped_absent_from_inscription"] += 1
            continue
        kept.append(row)
    return kept, stats


def prune_items_by_status(
    status: str,
    *,
    store_path: Path | None,
    confirm: bool,
) -> int:
    """Remove all override rows with given status (proposed or rejected)."""
    st = status.strip().lower()
    if st not in ("proposed", "rejected"):
        print("[prune] status must be proposed or rejected")
        return 1
    data = load_store(store_path)
    items: list[dict[str, Any]] = list(data.get("items") or [])
    to_drop = [it for it in items if (it.get("status") or "").strip().lower() == st]
    if not to_drop:
        print(f"[prune] No items with status={st!r}")
        return 0
    if not confirm:
        print(
            f"[prune] Would remove {len(to_drop)} item(s) with status={st!r}. "
            f"Re-run with --confirm-prune to write."
        )
        for it in to_drop[:25]:
            prev = (it.get("find") or "")[:60].replace("\n", " ")
            print(f"  id={it.get('id')} ep={it.get('episode')}  {prev!r}")
        if len(to_drop) > 25:
            print(f"  … and {len(to_drop) - 25} more")
        return 0
    kept = [it for it in items if (it.get("status") or "").strip().lower() != st]
    data["items"] = kept
    save_store(data, store_path)
    print(f"[prune] Removed {len(to_drop)} item(s); {len(kept)} remaining")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply transcript_overrides.json")
    ap.add_argument("--apply", action="store_true", help="Write files (default is dry-run if neither flag)")
    ap.add_argument("--dry-run", action="store_true", help="Print plan only")
    ap.add_argument(
        "--prune-status",
        choices=("proposed", "rejected"),
        default=None,
        help="Remove all rows with this status from the store (use --confirm-prune to apply)",
    )
    ap.add_argument(
        "--confirm-prune",
        action="store_true",
        help="Required to actually delete rows when using --prune-status",
    )
    ap.add_argument(
        "--verify-inscription",
        action="store_true",
        help="Report whether each queued item's find string appears in inscription (no writes)",
    )
    ap.add_argument("--episode", type=int, default=None, help="Only items for this episode")
    ap.add_argument("--id", dest="item_id", default=None, help="Only this override id")
    ap.add_argument("--store", type=Path, default=None, help="Override JSON path")
    args = ap.parse_args()
    if args.prune_status is not None:
        return prune_items_by_status(
            args.prune_status,
            store_path=args.store,
            confirm=bool(args.confirm_prune),
        )
    if args.verify_inscription:
        rep = run_verify_queue_vs_inscription(
            store_path=args.store,
            episode_filter=args.episode,
        )
        s = rep["summary"]
        print("[verify-inscription]", f"checked={s['items_checked']}", f"zero_matches={s['zero_matches_in_file']}", f"has_match={s['has_at_least_one_match']}")
        if s.get("missing_inscription_file"):
            print(f"  missing inscription file(s): {s['missing_inscription_file']}")
        if s.get("regex_errors"):
            print(f"  regex errors: {s['regex_errors']}")
        if s.get("not_targeting_inscription"):
            print(f"  items not targeting inscription tier: {s['not_targeting_inscription']}")
        for r in rep["items"]:
            if r.get("error"):
                tag = "ERR"
            elif r.get("inscription_missing"):
                tag = "NOFILE"
            elif r.get("regex_error"):
                tag = "REGEX"
            elif (r.get("match_count") or 0) == 0:
                tag = "ZERO"
            else:
                tag = f"×{r.get('match_count')}"
            prev = (r.get("find_preview") or "").replace("\n", " ")[:72]
            print(f"  {tag:5} ep{r.get('episode')} {r.get('status', ''):8} {r.get('id', '')}  {prev!r}")
        return 0

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
    if "match_start_offset" in body:
        if body.get("match_start_offset") is not None:
            item["match_start_offset"] = int(body.get("match_start_offset"))
        else:
            item["match_start_offset"] = None
    item["apply_all_episodes"] = _truthy(body.get("apply_all_episodes"))
    if item["status"] not in ("proposed", "accepted", "rejected"):
        return None, "status must be proposed, accepted, or rejected"
    if mode == "literal":
        nfb = (body.get("literal_not_followed_by") or body.get("literal_guard_suffix") or "").strip()
        parts = _parse_literal_not_followed_by_raw(nfb)
        if parts:
            item["literal_not_followed_by"] = ",".join(parts)
        else:
            item.pop("literal_not_followed_by", None)
        item.pop("literal_no_letter_after", None)
        item.pop("literal_guard_suffix", None)
        item["literal_require_ws_or_punct_after"] = bool(
            _truthy(body.get("literal_require_ws_or_punct_after"))
        )
    else:
        item.pop("literal_not_followed_by", None)
        item.pop("literal_no_letter_after", None)
        item.pop("literal_guard_suffix", None)
        item["literal_require_ws_or_punct_after"] = False
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
        all_eps = _truthy(x.get("apply_all_episodes"))
        out.add((ep, find, repl, mode, all_eps))
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
        key = (
            item["episode"],
            item["find"],
            item["replace"],
            item["match_mode"],
            bool(item.get("apply_all_episodes")),
        )
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
