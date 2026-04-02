#!/usr/bin/env python3
"""
Recompute meta.transcript_sha256 from on-disk transcript text (UTF-8) and update JSON.

Resolution order per episode N:
  1) inscription/episode_NNN_transcript.txt
  2) first transcripts_corrected/episode_NNN*.txt
  3) first transcripts/episode_NNN*.txt

Updates:
  - inscription/episode_NNN.json  (if present)
  - phase1_output/episode_NNN*.json (each file for that episode)

Usage:
  cd projects/monuments/bride_of_charlie
  python3 scripts/sync_transcript_hashes.py
  python3 scripts/sync_transcript_hashes.py --episode 1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def sha256_utf8(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def resolve_transcript(ep: int) -> Path | None:
    ins = PROJECT_DIR / "inscription" / f"episode_{ep:03d}_transcript.txt"
    if ins.is_file():
        return ins
    corr = sorted((PROJECT_DIR / "transcripts_corrected").glob(f"episode_{ep:03d}_*.txt"))
    if corr:
        return corr[0]
    raw = sorted((PROJECT_DIR / "transcripts").glob(f"episode_{ep:03d}_*.txt"))
    if raw:
        return raw[0]
    return None


def update_json_meta(path: Path, digest: str, dry_run: bool) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[hash] Skip {path.name}: {e}", file=sys.stderr)
        return False
    meta = data.setdefault("meta", {})
    old = meta.get("transcript_sha256")
    if old == digest:
        return False
    meta["transcript_sha256"] = digest
    print(f"[hash] {path.relative_to(PROJECT_DIR)}: {old[:12] if old else '∅'}… -> {digest[:16]}…")
    if not dry_run:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync transcript_sha256 in inscription + phase1 JSON")
    ap.add_argument("--episode", type=int, help="Only this episode number")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    episodes: list[int]
    if args.episode:
        episodes = [args.episode]
    else:
        episodes = []
        for p in (PROJECT_DIR / "inscription").glob("episode_*.json"):
            m = re.match(r"episode_(\d{3})\.json$", p.name)
            if m:
                episodes.append(int(m.group(1)))
        episodes = sorted(set(episodes))

    n_ok = 0
    for ep in episodes:
        tpath = resolve_transcript(ep)
        if not tpath:
            print(f"[hash] Episode {ep}: no transcript file found", file=sys.stderr)
            continue
        body = tpath.read_bytes()
        digest = sha256_utf8(body)
        ins_json = PROJECT_DIR / "inscription" / f"episode_{ep:03d}.json"
        if ins_json.is_file():
            update_json_meta(ins_json, digest, args.dry_run)
        for p1 in sorted((PROJECT_DIR / "phase1_output").glob(f"episode_{ep:03d}_*.json")):
            update_json_meta(p1, digest, args.dry_run)
        n_ok += 1
        print(f"[hash] Episode {ep}: source {tpath.relative_to(PROJECT_DIR)} ({len(body)} bytes)")

    print(f"[hash] Processed {n_ok} episode(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
