#!/usr/bin/env python3
"""Audit claim stamp vs snippet window (±60s) and artifact VTS overlap."""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PROJECT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import pipeline_gates as pg  # noqa: E402


def _parse_range(raw: str) -> tuple[int | None, int | None]:
    raw = raw.strip().replace("—", "–")
    parts = re.split(r"\s*[–-]\s*", raw)
    secs = [pg._parse_hms_to_seconds(p.strip()) for p in parts if p.strip()]
    secs = [s for s in secs if s is not None]
    if not secs:
        return None, None
    if len(secs) == 1:
        return secs[0], secs[0]
    return secs[0], secs[1]


def _artifact_vts(content: str) -> dict[str, tuple[int | None, int | None]]:
    out: dict[str, tuple[int | None, int | None]] = {}
    for m in re.finditer(r"^\*\*A-(\d+\.\d+)\*\*", content, re.MULTILINE):
        aid = f"A-{m.group(1)}"
        start = m.end()
        nxt = re.search(r"^\*\*(?:A-|C-)\d", content[start:], re.MULTILINE)
        end = start + nxt.start() if nxt else len(content)
        sec = content[start:end]
        vts = re.search(r"^Video Timestamp:\s*(.+)$", sec, re.MULTILINE | re.IGNORECASE)
        if vts:
            out[aid] = _parse_range(vts.group(1))
    return out


def audit(project_dir: Path) -> list[str]:
    errs: list[str] = []
    targets = {
        "C-1000", "C-1003", "C-1010", "C-1011", "C-1015", "C-1026",
        "C-1052", "C-1055", "C-1056", "C-1058", "C-1073", "C-1074",
        "C-1077", "C-1089", "C-1092", "C-1097", "C-1098",
    }
    for p in sorted((project_dir / "drafts").glob("episode_*.md")):
        if "cross" in p.name:
            continue
        ep_m = re.search(r"episode_(\d+)", p.name)
        if not ep_m:
            continue
        ep = int(ep_m.group(1))
        tpath = pg.resolve_corrected_transcript(project_dir, ep)
        if not tpath:
            continue
        tx = tpath.read_text(encoding="utf-8")
        content = p.read_text(encoding="utf-8")
        arts = _artifact_vts(content)
        for cm in re.finditer(r"^\*\*C-(\d+)\*\*", content, re.MULTILINE):
            cid = f"C-{cm.group(1)}"
            if cid not in targets:
                continue
            start = cm.end()
            nxt = re.search(r"^\*\*C-\d+\*\*", content[start:], re.MULTILINE)
            end = start + nxt.start() if nxt else len(content)
            sec = content[start:end]
            cts_m = re.search(r"^Claim Timestamp:\s*(.+)$", sec, re.MULTILINE)
            sn_m = re.search(r"^Transcript Snippet:\s*(.+)$", sec, re.MULTILINE)
            an_m = re.search(r"^Anchored Artifacts:\s*(.+)$", sec, re.MULTILINE)
            if not cts_m or not sn_m:
                errs.append(f"{cid}: missing timestamp or snippet")
                continue
            c_lo, c_hi = _parse_range(cts_m.group(1))
            snip = sn_m.group(1).strip()
            if not pg.snippet_in_transcript(snip, tx):
                errs.append(f"{cid}: snippet not in transcript")
                continue
            # snippet should appear within ±60s of claim window
            if c_lo is not None:
                window = pg._transcript_window_text(tx, c_lo, radius=60)
                if c_hi and c_hi != c_lo:
                    window += "\n" + pg._transcript_window_text(tx, c_hi, radius=60)
                if not pg.snippet_in_transcript(snip, window):
                    errs.append(f"{cid}: GROUNDING_STAMP_MISMATCH snippet outside ±60s of claim stamp")
            if an_m:
                for aid in re.findall(r"A-\d+\.\d+", an_m.group(1)):
                    vts = arts.get(aid)
                    if not vts or vts[0] is None:
                        errs.append(f"{cid}: unknown artifact {aid}")
                        continue
                    a_lo, a_hi = vts
                    if c_lo is None:
                        continue
                    claim_hi = c_hi if c_hi is not None else c_lo
                    art_hi = a_hi if a_hi is not None else a_lo
                    overlap = not (art_hi < c_lo - 60 or a_lo > claim_hi + 60)
                    if not overlap:
                        errs.append(
                            f"{cid}: artifact {aid} VTS {a_lo}-{art_hi} does not overlap claim {c_lo}-{claim_hi}"
                        )
    return errs


if __name__ == "__main__":
    problems = audit(PROJECT)
    if problems:
        print("FAIL:")
        for p in problems:
            print(f"  {p}")
        raise SystemExit(1)
    print("PASS: all targeted claims grounded")
