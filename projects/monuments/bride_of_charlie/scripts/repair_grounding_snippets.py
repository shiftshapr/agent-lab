#!/usr/bin/env python3
"""
Repair draft Transcript Snippet fields with verbatim caption text from transcripts_corrected.

Joins multi-line caption windows with "..." so each segment matches a single timestamp line
(compatible with pipeline_gates.snippet_in_transcript).

Also fills empty Anchored Artifacts from artifact Related cross-references when available.

Usage:
  python3 projects/monuments/bride_of_charlie/scripts/repair_grounding_snippets.py [--episode N] [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pipeline_gates as pg  # noqa: E402

_TIMESTAMP_LINE_RE = re.compile(r"^\[(\d{1,2}):(\d{2})\]\s*(.*)$")
_VIDEO_TS_RE = re.compile(r"^Video Timestamp:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_CLAIM_TS_RE = re.compile(r"^Claim Timestamp:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_TRANSCRIPT_SNIPPET_RE = re.compile(r"^Transcript Snippet:\s*(.*)$", re.MULTILINE)
_ANCHORED_RE = re.compile(r"^Anchored Artifacts:[ \t]*([^\n]*)\s*$", re.MULTILINE)
_ARTIFACT_ITEM_RE = re.compile(r"^\*\*A-(\d+)\.(\d+)\*\*", re.MULTILINE)
_CLAIM_ITEM_RE = re.compile(r"^\*\*C-(\d+)\*\*", re.MULTILINE)
_RELATED_RE = re.compile(r"^\*Related:\s*([^*]+)\*", re.MULTILINE)
_ID_TOKEN = re.compile(r"^[A-Z]+-\d+(?:\.\d+)?$")

# Narration-only claims: best-effort artifact anchors when no artifact Related back-link exists.
ANCHOR_HINTS: dict[str, list[str]] = {
    "C-1015": ["A-1010.1"],
    "C-1026": ["A-1017.1"],
    "C-1052": ["A-1031.1"],
    "C-1056": ["A-1029.1", "A-1029.2"],
    "C-1057": ["A-1025.1"],
    "C-1058": ["A-1026.3"],
    "C-1059": ["A-1025.1"],
    "C-1074": ["A-1038.1"],
    "C-1092": ["A-1054.1"],
}


def _parse_ts_range(raw: str) -> tuple[int | None, int | None]:
    raw = raw.strip().replace("—", "–")
    parts = re.split(r"\s*[–-]\s*", raw)
    secs: list[int | None] = []
    for part in parts:
        part = part.strip()
        if part:
            secs.append(pg._parse_hms_to_seconds(part))
    if not secs:
        return None, None
    if len(secs) == 1:
        return secs[0], secs[0]
    return secs[0], secs[1]


def _parse_transcript_lines(transcript: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for line in transcript.splitlines():
        m = _TIMESTAMP_LINE_RE.match(line)
        if m:
            sec = int(m.group(1)) * 60 + int(m.group(2))
            out.append((sec, m.group(3).strip()))
    return out


def extract_verbatim_snippet(
    transcript: str,
    start_sec: int | None,
    end_sec: int | None,
    *,
    pad_before: int = 0,
    pad_after: int = 30,
    max_lines: int = 8,
    must_include: list[str] | None = None,
) -> str:
    lines = _parse_transcript_lines(transcript)
    if not lines:
        return ""
    if start_sec is None:
        start_sec = lines[0][0]
    if end_sec is None:
        end_sec = start_sec
    lo = max(0, start_sec - pad_before)
    hi = end_sec + pad_after
    picked = [text for sec, text in lines if lo <= sec <= hi and text]

    if must_include:
        norm_tx = pg._normalize_for_match(transcript)
        for token in must_include:
            nt = pg._normalize_for_match(token)
            if nt and nt not in pg._normalize_for_match(" ".join(picked)):
                # Widen window to first caption line containing token
                for sec, text in lines:
                    if nt in pg._normalize_for_match(text):
                        extra_lo = max(0, sec - 30)
                        extra_hi = sec + 60
                        extra = [t for s, t in lines if extra_lo <= s <= extra_hi and t]
                        for t in extra:
                            if t not in picked:
                                picked.append(t)
                        break

    if not picked:
        picked = [min(lines, key=lambda x: abs(x[0] - start_sec))[1]]
    if len(picked) > max_lines:
        picked = picked[:max_lines]
    return "...".join(picked)


def _artifact_claim_map(content: str) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for art_m in _ARTIFACT_ITEM_RE.finditer(content):
        aid = f"A-{art_m.group(1)}.{art_m.group(2)}"
        start = art_m.end()
        end = len(content)
        for nm in (_ARTIFACT_ITEM_RE.search(content, start), _CLAIM_ITEM_RE.search(content, start)):
            if nm and nm.start() < end:
                end = nm.start()
        rel_m = _RELATED_RE.search(content[start:end])
        if not rel_m:
            continue
        for part in re.split(r"[,;]", rel_m.group(1)):
            token = part.strip()
            if token.startswith("C-") and _ID_TOKEN.match(token):
                mapping.setdefault(token, [])
                if aid not in mapping[token]:
                    mapping[token].append(aid)
    return mapping


def _node_artifact_map(content: str) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for m in re.finditer(r"^\*\*N-(\d+)\*\*", content, re.MULTILINE):
        nid = f"N-{int(m.group(1))}"
        start = m.end()
        next_m = re.search(r"^\*\*(?:N-|C-|A-)\d", content[start:], re.MULTILINE)
        end = start + next_m.start() if next_m else len(content)
        rel_m = _RELATED_RE.search(content[start:end])
        if not rel_m:
            continue
        arts = [
            t.strip()
            for t in re.split(r"[,;]", rel_m.group(1))
            if t.strip().startswith("A-") and _ID_TOKEN.match(t.strip())
        ]
        if arts:
            mapping[nid] = arts
    return mapping


def _claim_related_nodes(section: str) -> list[str]:
    nodes_m = re.compile(r"^Related Nodes:\s*(.+)$", re.MULTILINE).search(section)
    if not nodes_m:
        return []
    return [
        t.strip()
        for t in re.split(r"[,;]", nodes_m.group(1))
        if t.strip().startswith("N-") and _ID_TOKEN.match(t.strip())
    ]


def infer_anchors(content: str, claim_id: str, art_map: dict[str, list[str]], node_map: dict[str, list[str]], section: str) -> list[str]:
    if claim_id in art_map:
        return art_map[claim_id]
    if claim_id in ANCHOR_HINTS:
        return ANCHOR_HINTS[claim_id]
    anchors: list[str] = []
    for nid in _claim_related_nodes(section):
        for aid in node_map.get(nid, []):
            if aid not in anchors:
                anchors.append(aid)
    return anchors


def _set_or_insert_field(section: str, field: str, value: str) -> str:
    pat = re.compile(rf"^{re.escape(field)}:\s*.*$", re.MULTILINE)
    line = f"{field}: {value}"
    if pat.search(section):
        return pat.sub(line, section, count=1)
    for anchor_field in ("Claim:", "Video Timestamp:", "Event Timestamp:"):
        m = re.search(rf"^({re.escape(anchor_field)}\s*.+)$", section, re.MULTILINE)
        if m:
            return section[: m.end()] + f"\n{line}" + section[m.end() :]
    return section.rstrip() + f"\n{line}\n"


def _section_end(content: str, start: int, kind: str) -> int:
    if kind == "artifact":
        nxt = _ARTIFACT_ITEM_RE.search(content, start)
        clm = _CLAIM_ITEM_RE.search(content, start)
    else:
        nxt = _CLAIM_ITEM_RE.search(content, start)
        clm = None
    end = len(content)
    for nm in (nxt, clm):
        if nm and nm.start() < end:
            end = nm.start()
    return end


def repair_draft_content(content: str, transcript: str, ep_name: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    art_map = _artifact_claim_map(content)
    node_map = _node_artifact_map(content)

    # Artifacts
    for art_m in list(_ARTIFACT_ITEM_RE.finditer(content)):
        aid = f"A-{art_m.group(1)}.{art_m.group(2)}"
        abs_start = art_m.end()
        abs_end = _section_end(content, abs_start, "artifact")
        section = content[abs_start:abs_end]

        vts_m = _VIDEO_TS_RE.search(section)
        if not vts_m:
            continue
        start_sec, end_sec = _parse_ts_range(vts_m.group(1))
        snip_m = _TRANSCRIPT_SNIPPET_RE.search(section)
        current = snip_m.group(1).strip() if snip_m else ""
        if current and pg.snippet_in_transcript(current, transcript):
            continue
        if start_sec is None:
            continue
        new_snip = extract_verbatim_snippet(transcript, start_sec, end_sec)
        if not new_snip or new_snip == current:
            continue
        new_section = _set_or_insert_field(section, "Transcript Snippet", new_snip)
        content = content[:abs_start] + new_section + content[abs_end:]
        changes.append(f"{ep_name} {aid}: snippet repaired")

    # Claims (rebuild maps if artifacts changed — anchors only need claim sections)
    art_map = _artifact_claim_map(content)
    for claim_m in list(_CLAIM_ITEM_RE.finditer(content)):
        cid = f"C-{claim_m.group(1)}"
        abs_start = claim_m.end()
        abs_end = _section_end(content, abs_start, "claim")
        section = content[abs_start:abs_end]

        anchor_m = _ANCHORED_RE.search(section)
        current_anchors = anchor_m.group(1).strip() if anchor_m else ""
        if not current_anchors:
            inferred = infer_anchors(content, cid, art_map, node_map, section)
            if inferred:
                section = _set_or_insert_field(section, "Anchored Artifacts", ", ".join(inferred))
                content = content[:abs_start] + section + content[abs_end:]
                changes.append(f"{ep_name} {cid}: anchors -> {', '.join(inferred)}")
                abs_end = abs_start + len(section)
                section = content[abs_start:abs_end]

        cts_m = _CLAIM_TS_RE.search(section)
        if not cts_m:
            continue
        start_sec, end_sec = _parse_ts_range(cts_m.group(1))
        snip_m = _TRANSCRIPT_SNIPPET_RE.search(section)
        current = snip_m.group(1).strip() if snip_m else ""

        # Collect person-name tokens that must appear in grounded window
        must_include: list[str] = []
        node_names = pg._load_node_names(content)
        for nid in _claim_related_nodes(section):
            nm = node_names.get(nid)
            if nm:
                must_include.extend(pg._person_name_tokens(nm))

        needs_repair = not current or not pg.snippet_in_transcript(current, transcript)
        if not needs_repair and must_include:
            window = pg._transcript_window_text(transcript, start_sec, radius=120)
            search = pg._normalize_for_match(f"{current}\n{window}")
            if any(pg._normalize_for_match(t) not in search for t in must_include):
                needs_repair = True

        if not needs_repair:
            continue
        if start_sec is None:
            continue
        new_snip = extract_verbatim_snippet(
            transcript,
            start_sec,
            end_sec,
            pad_before=15,
            pad_after=45,
            must_include=must_include or None,
        )
        if not new_snip or new_snip == current:
            continue
        new_section = _set_or_insert_field(section, "Transcript Snippet", new_snip)
        content = content[:abs_start] + new_section + content[abs_end:]
        changes.append(f"{ep_name} {cid}: snippet repaired")

    return content, changes


def main() -> int:
    ap = argparse.ArgumentParser(description="Repair draft grounding snippets from corrected transcripts")
    ap.add_argument("--episode", type=str, default=None, help="Episode number or comma list")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    episodes: list[int] | None = None
    if args.episode:
        episodes = sorted({int(x.strip()) for x in args.episode.split(",") if x.strip().isdigit()})

    drafts_dir = PROJECT_DIR / "drafts"
    all_changes: list[str] = []

    for p in sorted(drafts_dir.glob("episode_*.md")):
        if "cross_episode" in p.name:
            continue
        m = re.search(r"episode_(\d+)", p.name, re.I)
        if not m:
            continue
        ep = int(m.group(1))
        if episodes and ep not in episodes:
            continue
        tpath = pg.resolve_corrected_transcript(PROJECT_DIR, ep)
        if not tpath:
            print(f"[repair] skip {p.name}: no transcript", file=sys.stderr)
            continue
        transcript = tpath.read_text(encoding="utf-8")
        new_content, changes = repair_draft_content(p.read_text(encoding="utf-8"), transcript, p.name)
        if changes and not args.dry_run:
            p.write_text(new_content, encoding="utf-8")
        all_changes.extend(changes)

    if all_changes:
        print(f"[repair] {'would apply' if args.dry_run else 'applied'} {len(all_changes)} change(s):")
        for c in all_changes:
            print(f"  {c}")
    else:
        print("[repair] no changes needed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
