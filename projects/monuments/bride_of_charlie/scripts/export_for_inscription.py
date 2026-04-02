"""
Export for Inscription — Episode JSON + Corrected Transcript

Bundles inscription-ready outputs for each episode:
  - inscription/episode_NNN.json — Episode analysis (JSON-LD with real IDs)
  - inscription/episode_NNN_transcript.txt — **Display** transcript (inscribed / hash source; see dual mode)

**Dual transcripts (optional):**

- ``--dual-transcripts`` also writes ``episode_NNN_transcript_verbatim.txt`` — a copy of the **source**
  file from ``transcripts_corrected/`` (caption-faithful after name-corrections + editorial rules).
- With ``--display-clean``, ``episode_NNN_transcript.txt`` is a **light** disfluency pass (standalone
  *uh* / *um*) for readability; **verbatim** is unchanged. Without ``--display-clean``, both files are
  identical copies when dual mode is on.

**Hash policy:** ``sync_transcript_hashes.py`` and validators use ``inscription/episode_NNN_transcript.txt``
as the file whose bytes match ``meta.transcript_sha256`` (the **display** path). Verbatim is not hashed.

Requires two-phase mode (EPISODE_ANALYSIS_TWO_PHASE=1) — assign_ids writes JSON to inscription/.

Usage:
  cd ~/workspace/agent-lab
  uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/export_for_inscription.py

  --drafts DIR       Drafts/inscription source (default: project drafts/)
  --inscription DIR  Output directory (default: project inscription/)
  --transcripts DIR  Corrected transcripts (default: project transcripts_corrected/)
  --dual-transcripts Emit verbatim + display pair (see above)
  --display-clean    With --dual-transcripts, strip standalone uh/um in display file only
  --no-validate      Skip node↔claim check (default: run ``screen_node_claim_consistency`` and exit non-zero on errors)

This script only copies JSON; it does not rewrite edges. To fix existing node↔claim edges in place, run
``scripts/repair_inscription_node_claims.py`` (applies the same policy as ``node_claim_sync``). To regenerate
from Phase 1, re-run ``assign_ids.py`` (which sanitizes before writing). Then export again.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
AGENT_LAB_ROOT = Path(__file__).resolve().parents[4]
DRAFTS_DIR = PROJECT_DIR / "drafts"
INSCRIPTION_DIR = PROJECT_DIR / "inscription"
TRANSCRIPTS_DIR = PROJECT_DIR / "transcripts_corrected"

# Standalone disfluencies only; does not alter timestamps or bracketed caption lines by rule.
_DISFLUENCY_TOKEN = re.compile(r"\b([Uu]h|[Uu]m)\b\s*")


def _strip_disfluencies(text: str) -> str:
    return _DISFLUENCY_TOKEN.sub("", text)


def _episode_num_from_name(name: str) -> int:
    m = re.search(r"episode_(\d+)", name, re.I)
    return int(m.group(1)) if m else 0


def _canonical_json_name(ep: int) -> str:
    return f"episode_{ep:03d}.json"


def _collect_episode_nums_with_json(inscription_dir: Path, drafts_dir: Path) -> list[int]:
    """Episode numbers that have at least one episode_NNN*.json in inscription or drafts."""
    found: set[int] = set()
    for d in (inscription_dir, drafts_dir):
        if d.exists():
            for p in d.glob("episode_*.json"):
                ep = _episode_num_from_name(p.name)
                if ep:
                    found.add(ep)
    return sorted(found)


def _resolve_json_source(ep: int, inscription_dir: Path, drafts_dir: Path) -> Path | None:
    """
    One source file per episode: prefer inscription/episode_NNN.json, else first
    inscription/episode_NNN_*.json, else drafts/episode_NNN_*.json.
    """
    base = f"episode_{ep:03d}"
    canon = inscription_dir / f"{base}.json"
    if canon.exists():
        return canon
    if inscription_dir.exists():
        longs = sorted(inscription_dir.glob(f"{base}_*.json"))
        if longs:
            return longs[0]
    if drafts_dir.exists():
        longs = sorted(drafts_dir.glob(f"{base}_*.json"))
        if longs:
            return longs[0]
    return None


def _validate_inscription_graph(*, include_backlinks: bool) -> int:
    """Return 0 if no errors; 1 if screen_node_claim_consistency reports errors."""
    if str(AGENT_LAB_ROOT) not in sys.path:
        sys.path.insert(0, str(AGENT_LAB_ROOT))
    try:
        from apps.draft_editor import bride_hub as bh
    except ImportError as e:
        print(f"[export] validate skipped (cannot import bride_hub): {e}")
        return 0
    out = bh.screen_node_claim_consistency(
        PROJECT_DIR, include_backlinks=include_backlinks
    )
    err_n = int(out.get("error_count") or 0)
    warn_n = int(out.get("warning_count") or 0)
    print(
        f"[export] validate-node-claims: ok={out.get('ok')} "
        f"errors={err_n} warnings={warn_n}"
    )
    if err_n > 0:
        print(
            "[export] Fix inscription JSON or run with --no-validate. "
            "See: projects/monuments/bride_of_charlie/scripts/validate_inscription_node_claims.py"
        )
        return 1
    return 0


def export(
    drafts_dir: Path,
    inscription_dir: Path,
    transcripts_dir: Path,
    *,
    prune_long_json: bool = True,
    dual_transcripts: bool = False,
    display_clean: bool = False,
) -> int:
    """
    Copy episode JSON and corrected transcripts to inscription/ using canonical names.
    Returns number of artifact files written (json + transcript + manifest lines not counted as 2).
    """
    inscription_dir.mkdir(parents=True, exist_ok=True)

    episode_nums = _collect_episode_nums_with_json(inscription_dir, drafts_dir)
    if not episode_nums:
        print("[export] No episode JSON found. Run two-phase generation first (assign_ids writes JSON).")
        return 0

    transcript_files = (
        {_episode_num_from_name(p.name): p for p in transcripts_dir.glob("episode_*.txt")}
        if transcripts_dir.exists()
        else {}
    )

    count = 0
    for ep in episode_nums:
        base = f"episode_{ep:03d}"
        jpath = _resolve_json_source(ep, inscription_dir, drafts_dir)
        if not jpath or not jpath.exists():
            print(f"  [{base}] skip — no JSON source")
            continue

        dest_json = inscription_dir / f"{base}.json"
        if jpath.resolve() != dest_json.resolve():
            shutil.copy2(jpath, dest_json)
            count += 1
        if prune_long_json and inscription_dir.exists():
            for redundant in inscription_dir.glob(f"{base}_*.json"):
                if redundant.resolve() != dest_json.resolve():
                    redundant.unlink()
                    print(f"  (pruned {redundant.name})")
        print(f"  {base}.json")

        if ep in transcript_files:
            src_txt = transcript_files[ep]
            body = src_txt.read_text(encoding="utf-8")
            if dual_transcripts:
                dest_ver = inscription_dir / f"{base}_transcript_verbatim.txt"
                dest_ver.write_text(body, encoding="utf-8")
                print(f"  {base}_transcript_verbatim.txt")
                count += 1
                dest_txt = inscription_dir / f"{base}_transcript.txt"
                if display_clean:
                    dest_txt.write_text(_strip_disfluencies(body), encoding="utf-8")
                    print(f"  {base}_transcript.txt (display-clean from corrected)")
                else:
                    dest_txt.write_text(body, encoding="utf-8")
                    print(f"  {base}_transcript.txt (same bytes as verbatim)")
                count += 1
            else:
                dest_txt = inscription_dir / f"{base}_transcript.txt"
                shutil.copy2(src_txt, dest_txt)
                print(f"  {base}_transcript.txt")
                count += 1
        else:
            print(f"  (no transcript for episode {ep})")

    # Manifest: canonical inscription bundle only (no duplicate long-named JSON)
    canonical_json = sorted(inscription_dir.glob("episode_*.json"))
    canonical_json = [p for p in canonical_json if re.match(r"^episode_\d{3}\.json$", p.name, re.I)]
    episodes_sorted = [_episode_num_from_name(p.name) for p in canonical_json]
    manifest_files: list[str] = []
    for p in canonical_json:
        manifest_files.append(p.name)
        tx = inscription_dir / p.name.replace(".json", "_transcript.txt")
        if tx.exists():
            manifest_files.append(tx.name)
        tv = inscription_dir / p.name.replace(".json", "_transcript_verbatim.txt")
        if tv.exists():
            manifest_files.append(tv.name)

    has_dual = any(
        (inscription_dir / f"episode_{e:03d}_transcript_verbatim.txt").exists()
        for e in episodes_sorted
    )
    manifest: dict = {
        "version": 2 if has_dual else 1,
        "episodes": episodes_sorted,
        "files": sorted(manifest_files),
    }
    if has_dual:
        manifest["transcript_roles"] = {
            "display": "episode_NNN_transcript.txt (bytes hashed in meta.transcript_sha256)",
            "verbatim": "episode_NNN_transcript_verbatim.txt (optional; not hashed)",
        }
    (inscription_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  manifest.json")
    print(
        f"[export] Summary: {len(episodes_sorted)} episode(s), "
        f"{len(manifest_files)} file(s) listed in manifest."
    )

    return count


def main() -> int:
    ap = argparse.ArgumentParser(description="Export episode JSON + corrected transcript for inscription")
    ap.add_argument("--drafts", type=Path, default=DRAFTS_DIR, help="Drafts/inscription source")
    ap.add_argument("--inscription", type=Path, default=INSCRIPTION_DIR, help="Output directory")
    ap.add_argument("--transcripts", type=Path, default=TRANSCRIPTS_DIR, help="Corrected transcripts")
    ap.add_argument(
        "--no-prune",
        action="store_true",
        help="Keep episode_NNN_videoId.json alongside episode_NNN.json (default: remove redundant long names from inscription/)",
    )
    ap.add_argument(
        "--dual-transcripts",
        action="store_true",
        help="Write episode_NNN_transcript_verbatim.txt + episode_NNN_transcript.txt (see module doc)",
    )
    ap.add_argument(
        "--display-clean",
        action="store_true",
        help="With --dual-transcripts, strip standalone uh/um in display file only",
    )
    ap.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip node↔claim consistency check (default: run after export, fail on errors)",
    )
    ap.add_argument(
        "--validate-no-backlinks",
        action="store_true",
        help="When validating, omit backlink warnings (faster triage)",
    )
    args = ap.parse_args()

    print(f"[export] Exporting to {args.inscription}")
    if args.display_clean and not args.dual_transcripts:
        print("[export] --display-clean requires --dual-transcripts; enabling dual output.")
        args.dual_transcripts = True
    export(
        args.drafts,
        args.inscription,
        args.transcripts,
        prune_long_json=not args.no_prune,
        dual_transcripts=args.dual_transcripts,
        display_clean=args.display_clean,
    )
    if not args.no_validate:
        code = _validate_inscription_graph(
            include_backlinks=not args.validate_no_backlinks
        )
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    exit(main())
