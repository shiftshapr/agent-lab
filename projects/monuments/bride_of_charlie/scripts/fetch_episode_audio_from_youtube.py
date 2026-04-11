#!/usr/bin/env python3
"""
Download per-episode audio from URLs in input/youtube_links.txt using yt-dlp.

Writes files expected by the Draft Editor and bride_transcript_media.find_episode_audio_file:
  input/audio/episode_001.m4a, episode_002.m4a, ...

Line order in youtube_links.txt matches episode index (same as fetch_transcripts.py / bride_transcript_media).

Requires: yt-dlp on PATH (https://github.com/yt-dlp/yt-dlp)

See docs/EPISODE_AUDIO_FROM_VIDEO.md for workflow and policy notes.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import bride_transcript_media as btm  # noqa: E402


def _which_yt_dlp(binary: str | None) -> str:
    if binary:
        p = Path(binary).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p.resolve())
        w = shutil.which(binary)
        if w:
            return w
        raise SystemExit(f"yt-dlp not found: {binary}")
    found = shutil.which("yt-dlp") or shutil.which("yt_dlp")
    if not found:
        raise SystemExit(
            "yt-dlp not found on PATH. Install: brew install yt-dlp  OR  pip install yt-dlp"
        )
    return found


def fetch_one(
    *,
    yt_dlp: str,
    project: Path,
    episode: int,
    video_id: str,
    force: bool,
    dry_run: bool,
) -> tuple[bool, str]:
    """Return (skipped, message)."""
    existing = btm.find_episode_audio_file(episode, project)
    if existing is not None and not force:
        if dry_run:
            return True, f"ep{episode}: would skip (exists: {existing.name}; use --force to replace)"
        return True, f"ep{episode}: skip (exists: {existing.name})"

    adir = project / "input" / "audio"
    out_template = adir / f"episode_{int(episode):03d}.%(ext)s"
    url = f"https://www.youtube.com/watch?v={video_id}"

    adir.mkdir(parents=True, exist_ok=True)

    cmd = [
        yt_dlp,
        "--no-playlist",
        "--no-warnings",
        "-f",
        "bestaudio/best",
        "-x",
        "--audio-format",
        "m4a",
        "--audio-quality",
        "0",
        "-o",
        str(out_template),
        url,
    ]

    if dry_run:
        return False, "DRY-RUN: " + " ".join(cmd)

    r = subprocess.run(cmd, cwd=str(project), capture_output=True, text=True)
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "").strip()
        return False, f"ep{episode}: FAILED ({err[:500]})"

    found = btm.find_episode_audio_file(episode, project)
    if found is None:
        return False, f"ep{episode}: yt-dlp exited 0 but no episode_{int(episode):03d}.* audio file found"
    return False, f"ep{episode}: ok → {found.name}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Download episode audio from youtube_links.txt via yt-dlp.")
    ap.add_argument(
        "--project",
        type=Path,
        default=PROJECT_DIR,
        help="Bride project root (default: parent of scripts/)",
    )
    ap.add_argument("--episode", type=int, default=None, help="Only this episode number (1-based)")
    ap.add_argument("--force", action="store_true", help="Re-download even if audio file already exists")
    ap.add_argument("--dry-run", action="store_true", help="Print yt-dlp commands only")
    ap.add_argument("--binary", type=str, default=None, help="Path to yt-dlp executable")
    args = ap.parse_args()

    project = args.project.resolve()
    links = project / "input" / "youtube_links.txt"
    if not links.is_file():
        print(f"Missing {links}", file=sys.stderr)
        return 1

    ids = btm.load_youtube_video_ids(project)
    if not ids:
        print("No video IDs parsed from input/youtube_links.txt", file=sys.stderr)
        return 1

    try:
        yt_dlp = _which_yt_dlp(args.binary)
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 1

    if args.episode is not None:
        if args.episode < 1:
            print("--episode must be >= 1", file=sys.stderr)
            return 1
        if args.episode > len(ids):
            print(f"--episode {args.episode} out of range (1..{len(ids)})", file=sys.stderr)
            return 1

    n_ok = n_skip = n_fail = 0
    for i, vid in enumerate(ids, start=1):
        if args.episode is not None and i != args.episode:
            continue
        skipped, msg = fetch_one(
            yt_dlp=yt_dlp,
            project=project,
            episode=i,
            video_id=vid,
            force=bool(args.force),
            dry_run=bool(args.dry_run),
        )
        print(msg)
        if "FAILED" in msg or "no episode_" in msg:
            n_fail += 1
        elif skipped:
            n_skip += 1
        elif args.dry_run:
            pass
        else:
            n_ok += 1

    print(f"Done: ok={n_ok} skipped={n_skip} failed={n_fail}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
