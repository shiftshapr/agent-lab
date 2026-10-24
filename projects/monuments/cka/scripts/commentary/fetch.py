#!/usr/bin/env python3
"""Fetch commentator captions (ROADMAP 4.1b): original-English auto captions for each video in a commentary manifest.

Usage: fetch.py MANIFEST.json OUT_DIR
MANIFEST is a list of {"kid", "video_id", ...}. For each video it saves OUT_DIR/raw/<id>.info.json and
<id>.en-orig.vtt (or <id>.en.vtt when the video has no en-orig track; on these channels plain `en` is the original
language) and writes OUT_DIR/transcripts/<kid>_<id>.md with vtt_to_cka.py. Transcripts stay private; the repo keeps
the manifest and short quotes only. Retries YouTube's HTTP 429 throttle with backoff.
"""
import json, shutil, subprocess, sys, time
from pathlib import Path

YTDLP = shutil.which("yt-dlp") or str(Path.home() / ".local/bin/yt-dlp")
VTT2CKA = Path(__file__).resolve().parents[1] / "vtt_to_cka.py"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def fetch(yid, raw, tries=6):
    base = [YTDLP, "--skip-download", "--ignore-no-formats-error", "--extractor-args", "youtube:player_client=ios",
            "-P", str(raw), "-o", "%(id)s", f"https://www.youtube.com/watch?v={yid}"]
    for i in range(tries):
        if not (raw / f"{yid}.info.json").exists():
            run(base[:1] + ["--write-info-json"] + base[1:])
        if (raw / f"{yid}.info.json").exists():
            caps = json.loads((raw / f"{yid}.info.json").read_text())["automatic_captions"] or {}
            lang = "en-orig" if "en-orig" in caps else "en" if "en" in caps else None
            if lang is None:
                return None
            if not (raw / f"{yid}.{lang}.vtt").exists():
                run(base[:1] + ["--write-auto-subs", "--sub-langs", lang, "--sub-format", "vtt"] + base[1:])
            if (raw / f"{yid}.{lang}.vtt").exists():
                return raw / f"{yid}.{lang}.vtt"
        time.sleep(min(60 * (i + 1), 300))
    return False


def main():
    man, out = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2])
    raw, tr = out / "raw", out / "transcripts"
    raw.mkdir(parents=True, exist_ok=True); tr.mkdir(parents=True, exist_ok=True)
    for x in man:
        vtt = fetch(x["video_id"], raw)
        if not vtt:
            print(x["kid"], x["video_id"], "NO CAPTIONS" if vtt is None else "FAILED"); continue
        r = run([sys.executable, str(VTT2CKA), str(vtt), str(raw / f"{x['video_id']}.info.json"), x["kid"][2:], "0", str(tr)])
        made = sorted(tr.glob(f"*{x['video_id']}*.md"))
        if r.returncode or not made:
            print(x["kid"], x["video_id"], "CONVERT FAILED", r.stderr[-300:]); continue
        made[-1].rename(tr / f"{x['kid']}_{x['video_id']}.md")
        print(x["kid"], x["video_id"], vtt.name.split(".")[-2], (tr / f"{x['kid']}_{x['video_id']}.md").stat().st_size)


if __name__ == "__main__":
    main()
