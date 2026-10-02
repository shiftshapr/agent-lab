#!/usr/bin/env python3
"""Residual scan: FALSE_NEW vs Batch1-2+earlier catch-up, and META_NAME_LIE."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
CANON = CKA / "canonical" / "nodes.json"

NID_RE = re.compile(r"\bN-(\d+)\b")
RANGE_RE = re.compile(r"N-(\d+)\s+through\s+N-(\d+)", re.I)
NID_WITH_NAME = re.compile(r"(N-(\d+))(\s*\(([^)]*)\))?")
YAML_NEW = re.compile(r"^  - New Nodes Introduced:\s*(.*)$", re.M)
BODY_NEW_LINE = re.compile(
    r"^([ \t]*[-*]?\s*\*{0,2}New Nodes Introduced\*{0,2}:\s*)(.+)$", re.M
)
MULTILINE_NEW_START = re.compile(r"(?m)^(#{1,3}\s*)?New Nodes Introduced:\s*$")


def expand(chunk: str) -> list[str]:
    ids, seen = [], set()
    stop = re.search(r"(?i)\b(Existing Nodes Reused|Reused Nodes Appearing|Cross-Episode)\b", chunk)
    text = chunk[: stop.start()] if stop else chunk
    for a, b in RANGE_RE.findall(text):
        for i in range(int(a), int(b) + 1):
            nid = f"N-{i}"
            if nid not in seen:
                seen.add(nid)
                ids.append(nid)
    for m in NID_RE.finditer(text):
        nid = f"N-{m.group(1)}"
        if nid not in seen:
            seen.add(nid)
            ids.append(nid)
    return ids


def _balanced_paren_name(s: str, open_idx: int) -> str | None:
    """open_idx points at '('; return inside text with nested parens, or None."""
    if open_idx >= len(s) or s[open_idx] != "(":
        return None
    depth = 0
    for i in range(open_idx, len(s)):
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
            if depth == 0:
                return s[open_idx + 1 : i]
    return None


def named_entries(chunk: str) -> list[tuple[str, str | None]]:
    stop = re.search(r"(?i)\b(Existing Nodes Reused|Reused Nodes Appearing|Cross-Episode)\b", chunk)
    text = chunk[: stop.start()] if stop else chunk
    out, seen = [], set()
    for a, b in RANGE_RE.findall(text):
        for i in range(int(a), int(b) + 1):
            nid = f"N-{i}"
            if nid not in seen:
                seen.add(nid)
                out.append((nid, None))
    for m in re.finditer(r"N-(\d+)", text):
        nid = f"N-{m.group(1)}"
        # look for parenthetical immediately after
        j = m.end()
        while j < len(text) and text[j].isspace():
            j += 1
        nm = _balanced_paren_name(text, j) if j < len(text) and text[j] == "(" else None
        if nid in seen:
            if nm is not None:
                for i, (n, oldnm) in enumerate(out):
                    if n == nid and oldnm is None:
                        out[i] = (nid, nm.strip())
                        break
            continue
        seen.add(nid)
        out.append((nid, nm.strip() if nm is not None else None))
    return out


def multiline_span(text: str, start: int) -> tuple[int, int, str]:
    rest = text[start:]
    m_end = re.search(
        r"(?m)^(Existing Nodes Reused:|Cross-Episode|\*\*Existing|---$|##\s)",
        rest[1:],
    )
    if m_end:
        end = start + 1 + m_end.start()
    else:
        m_blank = re.search(r"\n\n", rest[1:])
        end = start + 1 + m_blank.start() if m_blank else len(text)
    return start, end, text[start:end]


def collect_new_chunks(text: str) -> list[str]:
    chunks = []
    spans = []

    def overlaps(a, b):
        return any(a < e and b > s for s, e in spans)

    for m in YAML_NEW.finditer(text):
        chunks.append(m.group(1))
        spans.append((m.start(), m.end()))
    for m in MULTILINE_NEW_START.finditer(text):
        if overlaps(m.start(), m.start() + 10):
            continue
        s, e, block = multiline_span(text, m.start())
        rest = block.split("\n", 1)
        if len(rest) > 1 and rest[1].strip():
            second = rest[1].lstrip().split("\n", 1)[0]
            if second.startswith(("-", "*", "N-")):
                chunks.append(block)
                spans.append((s, e))
    for m in BODY_NEW_LINE.finditer(text):
        if overlaps(m.start(), m.end()):
            continue
        if not m.group(2).strip() or m.group(0).rstrip().endswith(":"):
            continue
        chunks.append(m.group(2))
        spans.append((m.start(), m.end()))
    return chunks


def main() -> int:
    canon = {
        nid: (meta or {}).get("canonical_name") or ""
        for nid, meta in json.loads(CANON.read_text())["nodes"].items()
    }
    intro: dict[str, int] = {}
    for ep in range(1, 21):
        p = DRAFTS / f"episode_{ep:03d}.md"
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        for chunk in collect_new_chunks(text):
            for nid in expand(chunk):
                intro.setdefault(nid, ep)

    false_new = []
    meta_lie = []

    for ep in range(21, 157):
        p = DRAFTS / f"episode_{ep:03d}.md"
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        chunks = collect_new_chunks(text)
        claimed = []
        seen = set()
        named = []
        for chunk in chunks:
            for nid in expand(chunk):
                if nid not in seen:
                    seen.add(nid)
                    claimed.append(nid)
            named.extend(named_entries(chunk))

        for nid in claimed:
            if nid in intro and intro[nid] < ep:
                false_new.append((ep, nid, intro[nid]))
            else:
                intro.setdefault(nid, ep)

        for nid, nm in named:
            if not nm:
                continue
            truth = canon.get(nid)
            if not truth:
                continue
            if nm.strip().lower() != truth.strip().lower():
                # Only flag when this id appears under a New Nodes chunk with that name
                meta_lie.append((ep, nid, nm, truth))

    # dedupe meta
    meta_dedup = []
    seen_m = set()
    for row in meta_lie:
        key = (row[0], row[1], row[2])
        if key not in seen_m:
            seen_m.add(key)
            meta_dedup.append(row)

    print(f"RESIDUAL FALSE_NEW: {len(false_new)}")
    for ep, nid, first in false_new:
        print(f"  P0 FALSE_NEW ep{ep} {nid} (first ep{first})")
    print(f"RESIDUAL META_NAME_LIE: {len(meta_dedup)}")
    for ep, nid, claimed, truth in meta_dedup:
        print(f"  P0 META_NAME_LIE ep{ep} {nid}: claimed '{claimed}' vs '{truth}'")

    out = {
        "FALSE_NEW": len(false_new),
        "META_NAME_LIE": len(meta_dedup),
        "false_new": [{"ep": e, "id": n, "first": f} for e, n, f in false_new],
        "meta_name_lie": [
            {"ep": e, "id": n, "claimed": c, "truth": t} for e, n, c, t in meta_dedup
        ],
    }
    out_path = Path("/workspace/cka-pr43-fix/residual_scan.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0 if not false_new and not meta_dedup else 1


if __name__ == "__main__":
    raise SystemExit(main())
