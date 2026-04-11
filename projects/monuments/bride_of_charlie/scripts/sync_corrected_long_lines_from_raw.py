#!/usr/bin/env python3
"""
Where corrected text is much longer than raw on the *same* line (same index
and timestamp), replace the corrected line body with the raw body — fixes
hallucinated insertions (e.g. 'Charlie Kirk and Turning Point', Elizabeth Lane
boilerplate) without using total line count as a signal.

Episode 001 has a different line count than raw; handle known merges/URL
separately in CORRECTED_EP001_FIXES.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
RAW = PROJECT / "transcripts"
CORR = PROJECT / "transcripts_corrected"
LINE_RE = re.compile(r"^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*)$")

# Longer than raw by more than this many characters => trust raw for this line.
LEN_MARGIN = 8


def _sync_file(raw_path: Path, corr_path: Path) -> tuple[int, list[str]]:
    raw_lines = raw_path.read_text(encoding="utf-8").splitlines()
    corr_lines = corr_path.read_text(encoding="utf-8").splitlines()
    notes: list[str] = []
    if len(raw_lines) != len(corr_lines):
        notes.append(
            f"{corr_path.name}: skip zip ({len(raw_lines)} raw vs {len(corr_lines)} corrected lines)"
        )
        return 0, notes

    out: list[str] = []
    n = 0
    for i, (lr, lc) in enumerate(zip(raw_lines, corr_lines), start=1):
        mr, mc = LINE_RE.match(lr), LINE_RE.match(lc)
        if not mr or not mc:
            out.append(lc)
            continue
        ts_r, body_r = mr.group(1), mr.group(2)
        ts_c, body_c = mc.group(1), mc.group(2)
        if ts_r != ts_c:
            notes.append(f"{corr_path.name}:{i}: timestamp mismatch {ts_r!r} vs {ts_c!r}")
            out.append(lc)
            continue
        if len(body_c) - len(body_r) > LEN_MARGIN:
            out.append(f"[{ts_r}] {body_r}")
            n += 1
        else:
            out.append(lc)

    if n:
        corr_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return n, notes


def _fix_ep001() -> None:
    """Split merged quote line and shorten ad read to match raw."""
    p = CORR / "episode_001_ZAsV0fHGBiM.txt"
    t = p.read_text(encoding="utf-8")
    t2 = t.replace(
        "[18:27] But I am an anthropologist,\n",
        "[18:27] But\n[18:27] >> I am an anthropologist,\n",
        1,
    )
    t2 = t2.replace(
        "[30:29] price. Visit getkickoff.com/candace.\n",
        "[30:29] price. Visit getkickoff\n",
        1,
    )
    if t2 != t:
        p.write_text(t2, encoding="utf-8")


def main() -> None:
    total = 0
    all_notes: list[str] = []
    for raw_path in sorted(RAW.glob("episode_*.txt")):
        name = raw_path.name
        corr_path = CORR / name
        if not corr_path.is_file():
            continue
        if name == "episode_001_ZAsV0fHGBiM.txt":
            _fix_ep001()
            all_notes.append("episode_001: applied merge split + getkickoff sync")
            continue
        n, notes = _sync_file(raw_path, corr_path)
        total += n
        all_notes.extend(notes)
    print(f"Replaced {total} lengthened line(s) with raw text (episodes 002–007).")
    for line in all_notes:
        print(line)


if __name__ == "__main__":
    main()
