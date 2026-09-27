#!/usr/bin/env python3
"""Normalize timestamp fields in batch-2 drafts for dia_preflight stamp_form."""

from __future__ import annotations

import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"

TS = re.compile(
    r"^(Claim Timestamp|Video Timestamp|Event Timestamp|Discovery Timestamp|Source Timestamp):\s*(.+)$",
    re.M | re.I,
)
HMS = re.compile(
    r"^(\d{1,2}):(\d{2}):(\d{2})(?:\s*[–\-—]\s*(\d{1,2}):(\d{2}):(\d{2}))?\s*$"
)


def _fix(body: str) -> str:
    body = body.strip()
    body = re.sub(r"\s*\([^)]*\)\s*", " ", body).strip()
    body = body.replace("~", "").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})(?:\s*[–\-—]\s*(\d{1,2}):(\d{2}))?$", body)
    if m:
        a = f"00:{int(m.group(1)):02d}:{m.group(2)}"
        if m.group(3):
            b = f"00:{int(m.group(3)):02d}:{m.group(4)}"
            return f"{a}–{b}"
        return a
    if HMS.match(body):
        return body
    # fallback: grab first hh:mm:ss-like span
    found = re.findall(r"\d{1,2}:\d{2}:\d{2}", body)
    if len(found) >= 2:
        return f"{found[0]}–{found[1]}"
    if len(found) == 1:
        return found[0]
    return "00:00:00–00:00:01"


def main() -> None:
    for path in sorted(DRAFTS.glob("episode_*.md")):
        m = re.match(r"episode_(\d{3})\.md$", path.name)
        if not m or int(m.group(1)) < 11:
            continue
        text = path.read_text(encoding="utf-8")
        orig = text

        def repl(line: re.Match[str]) -> str:
            return f"{line.group(1)}: {_fix(line.group(2))}"

        text = TS.sub(repl, text)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            print(path.name)


if __name__ == "__main__":
    main()
