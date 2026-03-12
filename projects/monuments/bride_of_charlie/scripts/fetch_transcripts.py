"""
Fetch YouTube transcripts (with timestamps).
Uses TranscriptAPI when TRANSCRIPT_API_KEY is set; otherwise youtube-transcript-api.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

AGENT_LAB = Path(__file__).parent.parent.parent.parent.parent
DEERFLOW_BACKEND = AGENT_LAB / "framework" / "deer-flow" / "backend"
PROJECT_DIR = Path(__file__).parent.parent
LINKS_FILE = PROJECT_DIR / "input" / "youtube_links.txt"
TRANSCRIPTS_DIR = PROJECT_DIR / "transcripts"

# Load .env from agent-lab root
try:
    from dotenv import load_dotenv
    load_dotenv(AGENT_LAB / ".env")
except ImportError:
    pass

# Add DeerFlow backend for dependencies
if str(DEERFLOW_BACKEND) not in sys.path:
    sys.path.insert(0, str(DEERFLOW_BACKEND))

try:
    import httpx
except ImportError:
    httpx = None

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None


def extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def format_timestamp(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def fetch_via_transcriptapi(url: str) -> str:
    """Fetch via TranscriptAPI REST API."""
    api_key = os.getenv("TRANSCRIPT_API_KEY") or os.getenv("API_KEY")
    if not api_key:
        raise ValueError("TRANSCRIPT_API_KEY not set")
    if not httpx:
        raise ImportError("httpx not installed")
    r = httpx.get(
        "https://transcriptapi.com/api/v2/youtube/transcript",
        params={"video_url": url, "format": "json"},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    lines = []
    for entry in data.get("transcript", []):
        ts = format_timestamp(entry["start"])
        text = entry.get("text", "").strip()
        lines.append(f"[{ts}] {text}")
    return "\n".join(lines)


def fetch_via_youtube_api(video_id: str) -> str:
    """Fetch via youtube-transcript-api (no key required)."""
    if not YouTubeTranscriptApi:
        raise ImportError("youtube-transcript-api not installed")
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
    lines = []
    for entry in transcript_list:
        ts = format_timestamp(entry["start"])
        text = entry["text"].strip()
        lines.append(f"[{ts}] {text}")
    return "\n".join(lines)


def fetch_transcript(url: str, video_id: str) -> str:
    """Fetch transcript. Prefer TranscriptAPI if key is set."""
    if os.getenv("TRANSCRIPT_API_KEY") or os.getenv("API_KEY"):
        return fetch_via_transcriptapi(url)
    return fetch_via_youtube_api(video_id)


def main() -> None:
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    if not LINKS_FILE.exists():
        print(f"Create {LINKS_FILE} with YouTube links (one per line)")
        sys.exit(1)

    links = [
        line.strip()
        for line in LINKS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not links:
        print("No links found in youtube_links.txt")
        sys.exit(1)

    api_key = os.getenv("TRANSCRIPT_API_KEY") or os.getenv("API_KEY")
    use_api = "TranscriptAPI" if api_key else "youtube-transcript-api"
    print(f"Fetching {len(links)} transcript(s) via {use_api}...")

    for i, url in enumerate(links, 1):
        video_id = extract_video_id(url)
        if not video_id:
            print(f"  [{i}] SKIP — invalid URL: {url[:50]}...")
            continue
        try:
            transcript = fetch_transcript(url, video_id)
            out_path = TRANSCRIPTS_DIR / f"episode_{i:03d}_{video_id}.txt"
            out_path.write_text(transcript, encoding="utf-8")
            print(f"  [{i}] OK — {video_id} -> {out_path.name}")
        except Exception as e:
            print(f"  [{i}] ERR — {video_id}: {e}")
            # Create placeholder for manual paste when captions unavailable
            placeholder = TRANSCRIPTS_DIR / f"episode_{i:03d}_{video_id}.txt"
            placeholder.write_text(
                f"# Paste transcript for {url}\n# Captions may be disabled or restricted.\n# Format: [MM:SS] text per line\n\n",
                encoding="utf-8",
            )
            print(f"       -> Placeholder created: {placeholder.name} (paste transcript manually)")

    print(f"\nTranscripts in {TRANSCRIPTS_DIR}")


if __name__ == "__main__":
    main()
