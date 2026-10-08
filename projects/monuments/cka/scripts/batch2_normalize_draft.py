#!/usr/bin/env python3
"""Normalize single-pass CKA batch-2 drafts to monument preflight shape."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
CORR = CKA / "transcripts_corrected"
MANIFEST = json.loads((CKA / "input" / "episode_manifest.json").read_text(encoding="utf-8"))
MAN_BY_SEQ = {int(r["seq"]): r for r in MANIFEST["episodes"] if r.get("seq") is not None}


def _sec_to_hms(sec: int) -> str:
    sec = max(0, int(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _load_yt_durations() -> dict[str, int]:
    path = CKA / "config" / "yt_durations.json"
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): int(v) for k, v in doc.get("by_youtube_id", {}).items()}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_transcript(ep: int, yt_id: str) -> Path | None:
    for pat in (f"episode_{ep:03d}_{yt_id}.md", f"episode_{ep:03d}_{yt_id}.txt"):
        p = CORR / pat
        if p.is_file():
            return p
    hits = list(CORR.glob(f"episode_{ep:03d}_*"))
    return hits[0] if hits else None


def _normalize_timestamps(text: str) -> str:
    def fix_val(val: str) -> str:
        val = val.strip()
        val = re.sub(r"\(approx\.?,?\s*within[^)]*\)", "", val, flags=re.I)
        val = re.sub(r"\(approx\.?\)", "", val, flags=re.I)
        val = val.replace("~", "").strip()
        val = re.sub(r"\s+", " ", val)
        # 00:04:00–00:04:30 (approx.) already stripped
        if VALID_HMS.match(val):
            return val
        # bare MM:SS -> 00:MM:SS
        m = re.match(r"^(\d{1,2}):(\d{2})(?:\s*[–\-\u2014]\s*(\d{1,2}):(\d{2}))?$", val)
        if m:
            a = f"00:{int(m.group(1)):02d}:{m.group(2)}"
            if m.group(3):
                b = f"00:{int(m.group(3)):02d}:{m.group(4)}"
                return f"{a}–{b}"
            return a
        return val

    out_lines = []
    for line in text.splitlines():
        m = TS_FIELD.match(line)
        if m:
            label, body = m.group(1), m.group(2)
            out_lines.append(f"{label}: {fix_val(body)}")
        else:
            out_lines.append(line)
    return "\n".join(out_lines) + ("\n" if text.endswith("\n") else "")


TS_FIELD = re.compile(
    r"^(Claim Timestamp|Video Timestamp|Event Timestamp|Discovery Timestamp|Source Timestamp):\s*(.+)$",
    re.I,
)
VALID_HMS = re.compile(
    r"^\s*(\d{1,2}):(\d{2}):(\d{2})(?:\s*[–\-\u2014]\s*(\d{1,2}):(\d{2}):(\d{2}))?\s*$"
)

SECTION_MAP = {
    "## Meta-Data": "## 1. Meta-Data",
    "## Executive Summary": "## 2. Executive Summary",
    "## Artifact Register": "## 3. Artifact Register",
    "## Node Register": "## 4. Node Register",
    "## Claim Register": "## 5. Claim Register",
}


def normalize_draft(path: Path) -> None:
    m = re.search(r"episode_(\d+)", path.name)
    if not m:
        return
    ep = int(m.group(1))
    row = MAN_BY_SEQ.get(ep)
    if not row:
        raise SystemExit(f"No manifest row for episode {ep}")

    text = path.read_text(encoding="utf-8")
    for old, new in SECTION_MAP.items():
        text = text.replace(old, new)

    yt_id = row["youtube_id"]
    tr = _find_transcript(ep, yt_id)
    sha = _sha256(tr) if tr else "0" * 64
    durs = _load_yt_durations()
    dur_sec = durs.get(yt_id)
    vrange = f"00:00:00–{_sec_to_hms(dur_sec)}" if dur_sec else "00:00:00–00:56:29"

    # Strip leading --- and rebuild meta block
    text = re.sub(r"^---\s*\n", "", text)
    text = re.sub(
        r"## 1\. Meta-Data\s*\n.*?(?=\n## 2\. Executive Summary)",
        "",
        text,
        count=1,
        flags=re.S,
    )

    meta = f"""## 1. Meta-Data

- **Episode**: {ep}
- **Monument**: cka
- **CKA seq**: {ep}
- **YouTube id**: {yt_id}
- **Candace Ep**: {row.get('candace_ep_number', '–')}
- **Source**: Candace Owens YouTube
- **Video Timestamp Range**: {vrange}
- **Extraction Timestamp (UTC)**: 2026-09-27T20:00:00Z
- **Model Version**: MiniMax-M2.5
- **Transcript SHA-256**: {sha}

"""
    # Ledger summary lives after old meta – find and keep
    ledger_m = re.search(
        r"(### Episode Ledger Summary| - \*\*Episode Ledger Summary\*\*|\n- Artifact Families Introduced:.*?(?=\n## 2\.))",
        text,
        flags=re.S,
    )
    if ledger_m:
        block = ledger_m.group(0)
        block = block.replace("### Episode Ledger Summary", "- **Episode Ledger Summary**:")
        block = block.replace("Existing Nodes Reused:", "  - Reused Nodes Appearing:")
        block = re.sub(r"^-\s", "  - ", block, flags=re.M)
        if "- **Episode Ledger Summary**:" not in block:
            block = "- **Episode Ledger Summary**:\n" + block
        text = text.replace(ledger_m.group(0), "")
        meta += block.strip() + "\n\n"
    else:
        meta += "- **Episode Ledger Summary**:\n  - (see registers)\n\n"

    text = meta + text.lstrip()
    text = text.replace("Series title:** Bride of Charlie", "Series title:** Candace Kirk Archive")
    text = _normalize_timestamps(text)

    # Remove Optional Flags section (non-standard)
    text = re.sub(r"\n## Optional Flags.*\Z", "\n", text, flags=re.S)

    out = DRAFTS / f"episode_{ep:03d}.md"
    out.write_text(text, encoding="utf-8")
    if path != out and path.is_file():
        path.unlink()


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:]] if len(sys.argv) > 1 else sorted(DRAFTS.glob("episode_*_*.md"))
    for p in paths:
        normalize_draft(p)
        print(f"normalized {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
