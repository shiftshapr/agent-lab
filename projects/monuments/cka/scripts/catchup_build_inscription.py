#!/usr/bin/env python3
"""Build inscription JSON + transcript sidecars for CKA catch-up seq 21–156."""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
DRAFTS = CKA / "drafts"
CORR = CKA / "transcripts_corrected"
INS = CKA / "inscription"
BOC_BUILD = REPO / "projects" / "monuments" / "bride_of_charlie" / "scripts" / "build_inscription_from_drafts.py"


def update_transcript_sha(ep: int) -> None:
    draft = DRAFTS / f"episode_{ep:03d}.md"
    if not draft.is_file():
        return
    text = draft.read_text(encoding="utf-8")
    m = re.search(r"- \*\*YouTube id\*\*:\s*(\S+)", text, re.I)
    yt = m.group(1) if m else None
    tr = None
    if yt:
        for p in CORR.glob(f"episode_{ep:03d}_{yt}.*"):
            tr = p
            break
    if tr is None:
        hits = list(CORR.glob(f"episode_{ep:03d}_*"))
        tr = hits[0] if hits else None
    if tr is None:
        return
    digest = hashlib.sha256(tr.read_bytes()).hexdigest()
    text = re.sub(
        r"(- \*\*Transcript SHA-256\*\*:\s*)\S+",
        lambda m: f"{m.group(1)}{digest}",
        text,
        count=1,
    )
    draft.write_text(text, encoding="utf-8")
    sha_dir = DRAFTS / ".transcript_sha"
    sha_dir.mkdir(parents=True, exist_ok=True)
    (sha_dir / f"episode_{ep:03d}.sha256").write_text(digest + "\n", encoding="utf-8")


def main() -> int:
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 21
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else 156
    for ep in range(lo, hi + 1):
        update_transcript_sha(ep)
    cmd = [
        sys.executable,
        str(BOC_BUILD),
        "--drafts",
        str(DRAFTS),
        "--inscription",
        str(INS),
    ]
    for ep in range(lo, hi + 1):
        cmd.extend(["--episode", str(ep)])
    subprocess.run(cmd, check=True, cwd=str(REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
