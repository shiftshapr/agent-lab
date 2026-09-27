#!/usr/bin/env python3
"""Single safe post-process pass for CKA batch-2 drafts (after batch2_extract_seq.sh)."""

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


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=str(REPO))


def _person_ids() -> set[int]:
    out: set[int] = set()
    for path in DRAFTS.glob("episode_*.md"):
        for m in re.finditer(r"\bN-(\d+)\b", path.read_text(encoding="utf-8")):
            n = int(m.group(1))
            if n < 1000:
                out.add(n)
    return out


def _decrement_person_band_if_176_free() -> None:
    ids = _person_ids()
    if 176 in ids or 177 not in ids:
        return
    batch = [
        p
        for p in sorted(DRAFTS.glob("episode_*.md"))
        if re.match(r"episode_\d{3}\.md$", p.name) and int(re.search(r"episode_(\d+)", p.name).group(1)) >= 11
    ]
    for path in batch:
        text = path.read_text(encoding="utf-8")

        def repl(m: re.Match[str]) -> str:
            n = int(m.group(1))
            if n >= 177:
                return f"N-{n - 1}"
            return m.group(0)

        path.write_text(re.sub(r"\bN-(\d+)\b", repl, text), encoding="utf-8")
    print("Decremented person ids >=177 by 1 (fill N-176 slot)")


def _fix_ledger() -> None:
    spec = importlib.util.spec_from_file_location("hf", SCRIPTS / "hostile_fix_batch1.py")
    hf = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(hf)
    paths = [
        p
        for p in sorted(DRAFTS.glob("episode_*.md"))
        if re.match(r"episode_\d{3}\.md$", p.name) and int(re.search(r"episode_(\d+)", p.name).group(1)) >= 11
    ]
    hf.fix_ledger(paths)
    hf.fix_meta_and_names(paths, hf._load_yt_durations())


def main() -> int:
    _run([sys.executable, str(SCRIPTS / "batch2_entity_reuse.py"), "--from-ep", "11"])
    _decrement_person_band_if_176_free()
    _run([sys.executable, str(SCRIPTS / "batch2_remap_topic_band.py")])
    _run([sys.executable, str(SCRIPTS / "batch2_fix_stamps.py")])
    for _ in range(15):
        _run([sys.executable, str(SCRIPTS / "batch2_fix_orphans.py")])
    _fix_ledger()
    _run([sys.executable, str(SCRIPTS / "batch2_rebuild_canonical.py")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
