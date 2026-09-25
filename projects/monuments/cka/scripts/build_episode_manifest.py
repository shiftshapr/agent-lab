#!/usr/bin/env python3
"""
Build CKA episode_manifest.json from @RealCandaceO /streams listing + Invidious publish dates.

Re-run from agent-lab root:
  python3 projects/monuments/cka/scripts/build_episode_manifest.py
  python3 projects/monuments/cka/scripts/build_episode_manifest.py --streams-cache /tmp/candace_streams.txt
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CKA_ROOT = REPO_ROOT / "projects" / "monuments" / "cka"
INVIDIOUS = "https://invidious.f5.si"
CUTOFF = "2025-09-11"

BOC_FOLD_IDS = [
    ("ZAsV0fHGBiM", 1),
    ("1IY2oD-_xVA", 2),
    ("cZxHqYsWRYg", 3),
    ("jTj9Ip46r4w", 4),
    ("2tFYJf1klgY", 5),
    ("y8lak3CRwDw", 6),
    ("DdPjoy5W-wY", 7),
    ("_vg7ucP1E0g", 8),
]

# BoC monument eps 9–18 → Candace show mapping (remap-not-reextract).
BOC_REMAP_ANCHORS: dict[str, tuple[int | None, str]] = {
    "_dRaEO47-co": (None, "kirk_special"),
    "czVBmqZP6Ss": (235, "numbered_show"),
    "q7f8r-THr84": (236, "numbered_show"),
    "2WEHTk0Xewg": (237, "numbered_show"),
    "sreYYcID-QY": (238, "numbered_show"),
    "aDlhjfW6hz8": (239, "numbered_show"),
    "ja26iltROkM": (240, "numbered_show"),
    "UBkFkg4UNY8": (241, "numbered_show"),
    "QZWSsq8ZWzw": (242, "numbered_show"),
    "K5GjF53bfN4": (243, "numbered_show"),
}

EP_NUM_RE = re.compile(
    r"(?:Candace\s+Ep(?:isode)?|(?:\|\s*)Ep(?:isode)?)\s*\.?\s*(\d+)",
    re.IGNORECASE,
)
BOC_SERIES_RE = re.compile(r"bride\s+of\s+charlie", re.IGNORECASE)


@dataclass
class StreamRow:
    youtube_id: str
    title: str


def _fetch_streams_via_ytdlp() -> list[StreamRow]:
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--flat-playlist",
        "--print",
        "%(id)s|%(title)s",
        "https://www.youtube.com/@RealCandaceO/streams",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
    rows: list[StreamRow] = []
    for line in out.stdout.splitlines():
        if "|" not in line:
            continue
        vid, title = line.split("|", 1)
        rows.append(StreamRow(vid.strip(), title.strip()))
    return rows


def _load_streams_cache(path: Path) -> list[StreamRow]:
    rows: list[StreamRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if "|" not in line:
            continue
        vid, title = line.split("|", 1)
        rows.append(StreamRow(vid.strip(), title.strip()))
    return rows


def _parse_ep_number(title: str) -> int | None:
    m = EP_NUM_RE.search(title)
    return int(m.group(1)) if m else None


def _invidious_published(vid: str) -> tuple[str | None, str | None]:
    """Return (YYYY-MM-DD, error)."""
    url = f"{INVIDIOUS}/api/v1/videos/{vid}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cka-manifest/1.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
        return None, str(exc)
    if "error" in data:
        return None, data.get("error")
    published = data.get("published")
    if published is None:
        return None, "missing published"
    try:
        ts = int(published)
        day = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        return day, None
    except (TypeError, ValueError):
        return None, f"bad published={published!r}"


def _is_kirk_special(title: str, upload_date: str | None) -> bool:
    if not re.search(r"charlie\s+kirk", title, re.I):
        return False
    if BOC_SERIES_RE.search(title):
        return False
    if upload_date and upload_date < CUTOFF:
        return False
    if upload_date is None:
        # Include likely post-assassination specials; exclude obvious old collab titles.
        return True
    return upload_date >= CUTOFF


def _classify(row: StreamRow, upload_date: str | None) -> str | None:
    if row.youtube_id in {v for v, _ in BOC_FOLD_IDS} or BOC_SERIES_RE.search(row.title):
        return "boc_fold"
    title_lower = row.title.lower()
    if title_lower.startswith("coming soon"):
        return None
    ep = _parse_ep_number(row.title)
    if ep is not None:
        if ep >= 235:
            return "numbered_show"
        return None
    if _is_kirk_special(row.title, upload_date):
        return "kirk_special"
    return None


def build_manifest(rows: list[StreamRow], *, sleep_s: float = 0.15) -> tuple[list[dict], list[dict], dict]:
    date_cache: dict[str, tuple[str | None, str | None]] = {}
    manifest_rows: list[dict] = []
    fold_rows: list[dict] = []
    gaps: dict[str, list[str]] = {"date_fetch_errors": [], "missing_upload_date": []}

    id_to_row = {r.youtube_id: r for r in rows}

    def get_date(vid: str) -> str | None:
        if vid not in date_cache:
            day, err = _invidious_published(vid)
            date_cache[vid] = (day, err)
            time.sleep(sleep_s)
        day, err = date_cache[vid]
        if err and vid not in {g.split()[0] for g in gaps["date_fetch_errors"]}:
            gaps["date_fetch_errors"].append(f"{vid}: {err}")
        return day

    # Bride of Charlie fold-later stubs (always include 8 series eps).
    for vid, boc_ep in BOC_FOLD_IDS:
        row = id_to_row.get(vid)
        title = row.title if row else f"Bride Of Charlie episode {boc_ep} (title from BoC ingest)"
        upload_date = get_date(vid)
        fold_rows.append(
            {
                "boc_monument_ep": boc_ep,
                "upload_date": upload_date,
                "youtube_id": vid,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "membership_tags": ["boc_series_fold_pending", "cka_chronology_fold"],
                "notes": "Exclude from initial CKA ingest; fold when chronology reaches Feb–Mar 2026 BoC series.",
            }
        )

    for row in rows:
        upload_date = get_date(row.youtube_id)
        kind = _classify(row, upload_date)
        if kind == "boc_fold":
            continue
        if kind is None:
            continue
        ep = _parse_ep_number(row.title)
        if row.youtube_id in BOC_REMAP_ANCHORS:
            ep_override, kind_override = BOC_REMAP_ANCHORS[row.youtube_id]
            ep = ep_override
            kind = kind_override
        note = None
        if row.youtube_id in BOC_REMAP_ANCHORS:
            note = "Former BoC monument ingest slot; remap artifacts/claims to CKA seq (do not re-extract)."
        if upload_date is None:
            gaps["missing_upload_date"].append(row.youtube_id)
        manifest_rows.append(
            {
                "upload_date": upload_date or "0000-00-00",
                "youtube_id": row.youtube_id,
                "title": row.title,
                "url": f"https://www.youtube.com/watch?v={row.youtube_id}",
                "candace_ep_number": ep,
                "kind": kind,
                "notes": note,
            }
        )

    # Chronological order; placeholder dates sort after real airdates.
    def _sort_key(row: dict) -> tuple:
        d = row["upload_date"]
        bad = d in (None, "", "0000-00-00")
        ep = row["candace_ep_number"] if row["candace_ep_number"] is not None else 9999
        return (1 if bad else 0, "9999-99-99" if bad else d, ep, row["title"])

    manifest_rows.sort(key=_sort_key)
    for seq, row in enumerate(manifest_rows, start=1):
        row["seq"] = seq

    fold_rows.sort(key=lambda r: (r["upload_date"] or "9999-99-99", r["boc_monument_ep"]))
    return manifest_rows, fold_rows, gaps


def _write_md_table(manifest: list[dict], path: Path) -> None:
    lines = [
        "# CKA episode manifest (summary)",
        "",
        "| seq | upload_date | kind | candace_ep | youtube_id | title |",
        "|-----|-------------|------|------------|------------|-------|",
    ]
    for row in manifest:
        ep = row["candace_ep_number"] if row["candace_ep_number"] is not None else ""
        title = row["title"].replace("|", "\\|")
        lines.append(
            f"| {row['seq']} | {row['upload_date']} | {row['kind']} | {ep} | {row['youtube_id']} | {title} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--streams-cache", type=Path, help="id|title lines from yt-dlp /streams")
    ap.add_argument("--sleep", type=float, default=0.12, help="Delay between Invidious calls")
    args = ap.parse_args()

    if args.streams_cache and args.streams_cache.is_file():
        rows = _load_streams_cache(args.streams_cache)
    else:
        rows = _fetch_streams_via_ytdlp()

    manifest, fold, gaps = build_manifest(rows, sleep_s=args.sleep)

    out_dir = CKA_ROOT / "input"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "monument": "cka",
        "channel": "@RealCandaceO",
        "corpus_cutoff_inclusive": CUTOFF,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "listing": "https://www.youtube.com/@RealCandaceO/streams",
            "publish_dates": INVIDIOUS,
        },
        "counts": {
            "manifest_entries": len(manifest),
            "numbered_show": sum(1 for r in manifest if r["kind"] == "numbered_show"),
            "kirk_special": sum(1 for r in manifest if r["kind"] == "kirk_special"),
        },
        "episodes": manifest,
    }
    (out_dir / "episode_manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (out_dir / "boc_fold_later.json").write_text(
        json.dumps({"monument": "cka", "fold_when_chronology_reaches": "2026-02", "entries": fold}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    _write_md_table(manifest, out_dir / "episode_manifest.md")

    gaps_path = CKA_ROOT / "input" / "MANIFEST_GAPS.md"
    if gaps["date_fetch_errors"] or gaps["missing_upload_date"]:
        lines = [
            "# CKA manifest gaps",
            "",
            "Publish dates come from Invidious (`invidious.f5.si`). Re-run the builder after refreshing dates.",
            "",
            "## Finish full channel listing + dates",
            "",
            "```bash",
            "cd ~/workspace/agent-lab",
            "python3 -m yt_dlp --flat-playlist --print \"%(id)s|%(title)s\" \\",
            "  \"https://www.youtube.com/@RealCandaceO/streams\" \\",
            "  > /tmp/candace_streams.txt",
            "python3 projects/monuments/cka/scripts/build_episode_manifest.py --streams-cache /tmp/candace_streams.txt",
            "```",
            "",
            "If YouTube blocks metadata, export cookies and retry:",
            "",
            "```bash",
            "python3 -m yt_dlp --cookies-from-browser chrome --flat-playlist \\",
            "  --print \"%(upload_date)s|%(id)s|%(title)s\" \"https://www.youtube.com/@RealCandaceO/streams\"",
            "```",
            "",
        ]
        if gaps["missing_upload_date"]:
            lines.append(f"- **missing_upload_date**: {len(gaps['missing_upload_date'])} videos")
        if gaps["date_fetch_errors"]:
            lines.append(f"- **date_fetch_errors**: {len(gaps['date_fetch_errors'])} (see builder log)")
        gaps_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif gaps_path.exists():
        gaps_path.unlink()

    print(
        json.dumps(
            {
                "manifest_entries": len(manifest),
                "numbered_show": payload["counts"]["numbered_show"],
                "kirk_special": payload["counts"]["kirk_special"],
                "boc_fold_later": len(fold),
                "date_errors": len(gaps["date_fetch_errors"]),
                "missing_dates": len(gaps["missing_upload_date"]),
            },
            indent=2,
        )
    )
    if manifest:
        print(f"date_span: {manifest[0]['upload_date']} .. {manifest[-1]['upload_date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
