"""
Export for Inscription — Episode JSON + Corrected Transcript

Bundles inscription-ready outputs for each episode:
  - inscription/episode_NNN.json — Episode analysis (JSON-LD with real IDs)
  - inscription/episode_NNN_transcript.txt — Corrected transcript

Requires two-phase mode (EPISODE_ANALYSIS_TWO_PHASE=1) — assign_ids writes JSON to inscription/.

Usage:
  cd ~/workspace/agent-lab
  uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/export_for_inscription.py

  --drafts DIR       Drafts/inscription source (default: project drafts/)
  --inscription DIR  Output directory (default: project inscription/)
  --transcripts DIR  Corrected transcripts (default: project transcripts/)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DRAFTS_DIR = PROJECT_DIR / "drafts"
INSCRIPTION_DIR = PROJECT_DIR / "inscription"
TRANSCRIPTS_DIR = PROJECT_DIR / "transcripts"


def _episode_num_from_name(name: str) -> int:
    m = re.search(r"episode_(\d+)", name, re.I)
    return int(m.group(1)) if m else 0


def export(drafts_dir: Path, inscription_dir: Path, transcripts_dir: Path) -> int:
    """Copy episode JSON and corrected transcripts to inscription/. Returns count."""
    inscription_dir.mkdir(parents=True, exist_ok=True)

    # Find JSON files (assign_ids writes to inscription/ in two-phase mode)
    json_sources = list(inscription_dir.glob("episode_*.json")) or list(drafts_dir.glob("episode_*.json"))
    if not json_sources:
        # Check for phase1_output + run assign_ids, or look for .json in inscription
        print("[export] No episode JSON found. Run two-phase generation first (assign_ids writes JSON).")
        return 0

    transcript_files = {_episode_num_from_name(p.name): p for p in transcripts_dir.glob("episode_*.txt")} if transcripts_dir.exists() else {}

    count = 0
    for jpath in sorted(json_sources, key=lambda p: _episode_num_from_name(p.name)):
        ep = _episode_num_from_name(jpath.name)
        base = f"episode_{ep:03d}"

        # Copy or rename JSON
        dest_json = inscription_dir / f"{base}.json"
        if jpath != dest_json:
            shutil.copy2(jpath, dest_json)
        count += 1
        print(f"  {base}.json")

        # Copy corrected transcript
        if ep in transcript_files:
            dest_txt = inscription_dir / f"{base}_transcript.txt"
            shutil.copy2(transcript_files[ep], dest_txt)
            print(f"  {base}_transcript.txt")
            count += 1
        else:
            print(f"  (no transcript for episode {ep})")

    # Write manifest
    manifest = {
        "version": 1,
        "episodes": sorted({_episode_num_from_name(p.name) for p in inscription_dir.glob("episode_*.json")}),
        "files": [p.name for p in sorted(inscription_dir.glob("episode_*"))],
    }
    (inscription_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  manifest.json")

    return count


def main() -> int:
    ap = argparse.ArgumentParser(description="Export episode JSON + corrected transcript for inscription")
    ap.add_argument("--drafts", type=Path, default=DRAFTS_DIR, help="Drafts/inscription source")
    ap.add_argument("--inscription", type=Path, default=INSCRIPTION_DIR, help="Output directory")
    ap.add_argument("--transcripts", type=Path, default=TRANSCRIPTS_DIR, help="Corrected transcripts")
    args = ap.parse_args()

    print(f"[export] Exporting to {args.inscription}")
    count = export(args.drafts, args.inscription, args.transcripts)
    print(f"[export] Done. {count} file(s) ready for inscription.")
    return 0


if __name__ == "__main__":
    exit(main())
