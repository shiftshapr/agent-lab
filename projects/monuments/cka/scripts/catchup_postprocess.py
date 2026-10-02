#!/usr/bin/env python3
"""Post-process CKA catch-up drafts (seq 21–156) after catchup_extract_seq.sh."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
REPO = CKA.parents[2]
DRAFTS = CKA / "drafts"
SCRIPTS = CKA / "scripts"
FROM_EP = 21


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=str(REPO))


def _fix_ledger() -> None:
    spec = importlib.util.spec_from_file_location("hf", SCRIPTS / "hostile_fix_batch1.py")
    hf = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(hf)
    paths = [
        p
        for p in sorted(DRAFTS.glob("episode_*.md"))
        if re.match(r"episode_\d{3}\.md$", p.name)
        and int(re.search(r"episode_(\d+)", p.name).group(1)) >= FROM_EP
    ]
    hf.fix_ledger(paths)
    hf.fix_meta_and_names(paths, hf._load_yt_durations())


def main() -> int:
    _run([sys.executable, str(SCRIPTS / "batch2_entity_reuse.py"), "--from-ep", str(FROM_EP)])
    _run([sys.executable, str(SCRIPTS / "batch2_remap_topic_band.py")])
    _run([sys.executable, str(SCRIPTS / "batch2_fix_stamps.py")])
    for _ in range(20):
        _run([sys.executable, str(SCRIPTS / "batch2_fix_orphans.py")])
    _fix_ledger()
    _run([sys.executable, str(SCRIPTS / "catchup_scrub_transcripts.py"), "21", "156"])
    _run([sys.executable, str(SCRIPTS / "batch2_rebuild_canonical.py")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
