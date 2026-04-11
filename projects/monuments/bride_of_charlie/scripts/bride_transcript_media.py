#!/usr/bin/env python3
"""
YouTube deep links + caption timestamps + suspicious-pattern scan for transcript review.

Used by Draft Editor API (see apps/draft_editor/app.py).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent.parent


def primary_episode_transcript_path(project: Path, episode: int) -> Path | None:
    """transcripts_corrected/ when present, else inscription transcript."""
    corr = sorted((project / "transcripts_corrected").glob(f"episode_{int(episode):03d}_*.txt"))
    if corr:
        return corr[0]
    ins = project / "inscription" / f"episode_{int(episode):03d}_transcript.txt"
    if ins.is_file():
        return ins
    return None


_CAPTION = re.compile(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]")

_FLAG = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
}


def load_youtube_video_ids(project: Path | None = None) -> list[str]:
    """Episode index 1..N from non-comment lines in youtube_links.txt."""
    project = project or PROJECT_DIR
    path = project / "input" / "youtube_links.txt"
    if not path.is_file():
        return []
    ids: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", line)
        if m:
            ids.append(m.group(1))
    return ids


def video_id_for_episode(episode: int, project: Path | None = None) -> str | None:
    ids = load_youtube_video_ids(project)
    i = int(episode) - 1
    if 0 <= i < len(ids):
        return ids[i]
    return None


def find_episode_audio_file(episode: int, project: Path | None = None) -> Path | None:
    """
    Optional per-episode audio files next to the project.

    Populate from the same URLs as ``input/youtube_links.txt`` using
    ``scripts/fetch_episode_audio_from_youtube.py`` (see docs/EPISODE_AUDIO_FROM_VIDEO.md).

    Convention: ``input/audio/episode_NNN.<ext>`` (``.m4a``, ``.mp3``, …).
    Served by Draft Editor at ``GET /api/bride/episode/<n>/audio`` when present.
    """
    project = project or PROJECT_DIR
    adir = project / "input" / "audio"
    if not adir.is_dir():
        return None
    stem = f"episode_{int(episode):03d}"
    for ext in (".m4a", ".mp3", ".opus", ".webm", ".ogg", ".wav", ".aac"):
        p = adir / (stem + ext)
        if p.is_file():
            return p
    return None


def last_caption_before(text: str, pos: int) -> tuple[int | None, str | None]:
    """Return (seconds_since_start, bracket_label) for last [M:SS] or [H:M:SS] before pos."""
    best: tuple[int, int, str] | None = None  # start, seconds, label
    for m in _CAPTION.finditer(text):
        if m.start() >= pos:
            break
        g1, g2, g3 = m.group(1), m.group(2), m.group(3)
        if g3 is not None:
            sec = int(g1) * 3600 + int(g2) * 60 + int(g3)
        else:
            sec = int(g1) * 60 + int(g2)
        best = (m.start(), sec, m.group(0))
    if not best:
        return None, None
    return best[1], best[2]


def youtube_urls(video_id: str, start_seconds: int | None) -> dict[str, str]:
    t = max(0, int(start_seconds)) if start_seconds is not None else 0
    watch = f"https://www.youtube.com/watch?v={video_id}"
    if t > 0:
        watch += f"&t={t}s"
    # youtube.com embed tends to behave better than nocookie in Safari / strict ITP
    # (nocookie still triggers blocked analytics XHR in the console; harmless noise).
    embed = f"https://www.youtube.com/embed/{video_id}"
    if t > 0:
        embed += f"?start={t}&autoplay=0"
    else:
        embed += "?autoplay=0"
    return {"watch": watch, "embed": embed, "start_seconds": str(t)}


def load_suspicious_patterns(project: Path | None = None) -> list[dict[str, Any]]:
    project = project or PROJECT_DIR
    path = project / "config" / "transcript_suspicious_patterns.json"
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    return list(doc.get("patterns") or [])


def _compile_pattern(p: dict[str, Any]) -> re.Pattern[str] | None:
    try:
        flags = 0
        for name in p.get("flags") or []:
            flags |= _FLAG.get(str(name).upper(), 0)
        return re.compile(p.get("regex", ""), flags)
    except re.error:
        return None


def scan_text(
    text: str,
    *,
    patterns: list[dict[str, Any]] | None = None,
    max_findings: int = 150,
) -> list[dict[str, Any]]:
    """Return findings with global offsets and caption times."""
    pats = patterns if patterns is not None else load_suspicious_patterns()
    out: list[dict[str, Any]] = []
    for p in pats:
        rx = _compile_pattern(p)
        if not rx:
            continue
        pid = p.get("id", "")
        for m in rx.finditer(text):
            start, end = m.start(), m.end()
            sec, cap = last_caption_before(text, start)
            lo = max(0, start - 100)
            hi = min(len(text), end + 120)
            out.append(
                {
                    "id": pid,
                    "hint": p.get("hint", ""),
                    "suggestion": p.get("suggestion", ""),
                    "match": m.group(0),
                    "start": start,
                    "end": end,
                    "excerpt": text[lo:hi],
                    "caption_seconds": sec,
                    "caption_label": cap,
                }
            )
            if len(out) >= max_findings:
                return sorted(out, key=lambda x: (x["caption_seconds"] is None, x["caption_seconds"] or 0, x["start"]))
    out.sort(key=lambda x: (x["caption_seconds"] is None, x["caption_seconds"] or 0, x["start"]))
    return out


def scan_excerpt(excerpt: str, *, max_findings: int = 20) -> list[dict[str, Any]]:
    """Scan a short excerpt; offsets are relative to excerpt (not full file)."""
    findings = scan_text(excerpt, max_findings=max_findings)
    return findings


def media_bundle_for_position(
    episode: int,
    text: str,
    match_offset: int | None,
    project: Path | None = None,
) -> dict[str, Any]:
    proj = project or PROJECT_DIR
    audio_path = find_episode_audio_file(episode, proj)
    vid = video_id_for_episode(episode, proj)

    def _audio_meta(start_sec: int | None) -> dict[str, Any] | None:
        if not audio_path:
            return None
        t = max(0, int(start_sec)) if start_sec is not None else 0
        return {
            "filename": audio_path.name,
            "url": f"/api/bride/episode/{int(episode)}/audio",
            "start_seconds": t,
        }

    if not vid:
        return {"video_id": None, "youtube": None, "caption": None, "audio": _audio_meta(0)}
    if match_offset is None or match_offset < 0:
        return {
            "video_id": vid,
            "youtube": youtube_urls(vid, 0),
            "caption": None,
            "audio": _audio_meta(0),
        }
    sec, cap = last_caption_before(text, match_offset)
    if sec is None:
        return {
            "video_id": vid,
            "youtube": youtube_urls(vid, 0),
            "caption": None,
            "audio": _audio_meta(0),
        }
    return {
        "video_id": vid,
        "youtube": youtube_urls(vid, sec),
        "caption": {"label": cap, "seconds": sec},
        "audio": _audio_meta(sec),
    }


def enrich_preview(
    project: Path,
    episode: int,
    preview: dict[str, Any],
) -> dict[str, Any]:
    """Add media + suspicious hits to preview dict from apply_transcript_overrides.preview_item."""
    out = {**preview}
    rel = preview.get("file")
    mo = preview.get("match_offset")
    ctx = preview.get("context_excerpt") or preview.get("before_excerpt") or ""
    out["suspicious_in_excerpt"] = scan_excerpt(ctx, max_findings=15) if ctx else []
    if not rel:
        out["media"] = {"video_id": video_id_for_episode(episode, project), "youtube": None, "caption": None}
        return out
    path = project / rel
    if not path.is_file():
        out["media"] = {"video_id": video_id_for_episode(episode, project), "youtube": None, "caption": None}
        return out
    full = path.read_text(encoding="utf-8")
    mo_int = int(mo) if mo is not None else None
    out["media"] = media_bundle_for_position(episode, full, mo_int, project)
    return out


def scan_episode_inscription(episode: int, project: Path | None = None) -> dict[str, Any]:
    project = project or PROJECT_DIR
    path = primary_episode_transcript_path(project, int(episode))
    if path is None or not path.is_file():
        fb = project / "inscription" / f"episode_{int(episode):03d}_transcript.txt"
        return {"error": "missing_episode_transcript", "path": str(path or fb), "findings": []}
    text = path.read_text(encoding="utf-8")
    vid = video_id_for_episode(int(episode), project)
    findings = scan_text(text, max_findings=200)
    # attach watch URL per finding
    enriched = []
    for f in findings:
        sec = f.get("caption_seconds")
        yu = youtube_urls(vid, sec) if vid and sec is not None else None
        row = {**f, "youtube": yu}
        enriched.append(row)
    return {
        "episode": int(episode),
        "video_id": vid,
        "file": str(path.relative_to(project)),
        "findings": enriched,
        "count": len(enriched),
    }
