#!/usr/bin/env python3
"""Extend config/yt_durations.json from batch-2 transcript YAML frontmatter."""

from __future__ import annotations

import json
import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
CORR = CKA / "transcripts_corrected"
CFG = CKA / "config" / "yt_durations.json"


def _parse_duration(s: str) -> int | None:
    m = re.match(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", s.strip())
    if not m:
        return None
    if m.group(3) is not None:
        h, mi, se = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        h, mi, se = 0, int(m.group(1)), int(m.group(2))
    return h * 3600 + mi * 60 + se


def main() -> int:
    doc = json.loads(CFG.read_text(encoding="utf-8"))
    by = doc.setdefault("by_youtube_id", {})
    for path in sorted(CORR.glob("episode_*.md")):
        text = path.read_text(encoding="utf-8")
        ym = re.search(r"^duration:\s*\"([^\"]+)\"", text, re.M)
        idm = re.search(r"^youtube_id:\s*(\S+)", text, re.M)
        if not ym or not idm:
            continue
        sec = _parse_duration(ym.group(1))
        if sec:
            by[idm.group(1)] = sec
    doc["description"] = "YouTube duration seconds for CKA seq 1–20."
    CFG.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {CFG.name} ({len(by)} ids)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
