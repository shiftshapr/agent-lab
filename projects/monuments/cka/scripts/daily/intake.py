#!/usr/bin/env python3
"""Daily CKA intake (ROADMAP 1.4): find new Candace episodes and prepare them for extraction.

For each video on @RealCandaceO/streams that is not in input/episode_manifest.json (newest first, stopping at the
first known id):
- downloads its info.json and its ORIGINAL-English auto captions (`en-orig`; the plain `en` track on these videos is a
  machine translation of a dubbed audio track and must never be used), retrying through YouTube's HTTP 429 throttle;
- writes transcripts_corrected/episode_<seq>_<id>.md with scripts/vtt_to_cka.py;
- appends the manifest (json and md) and youtube_links.txt;
- writes a skeleton draft and its transcript SHA;
- applies config/transcript_name_corrections.json.
Then it builds the extraction pack (nodes.tsv, memes.tsv, claims_index.tsv, SPEC.md, EXTRACT_PROMPT.md) in WORK_DIR and
writes WORK_DIR/new_episodes.json. It edits the repo working tree only; it never commits.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/daily/intake.py WORK_DIR [--max 6] [--dry-run]
Exit status: 0 with new episodes prepared, 3 when there is nothing new or nothing captioned yet, 1 on error.
A same-day live stream often has no captions for some hours; it is picked up by the next run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "source"))
import cka_source as cs  # noqa: E402  (ROADMAP 3.0: episodes are read and written through the JSON source)

CKA = Path(__file__).resolve().parents[2]
REPO = CKA.parents[2]
CHANNEL = "https://www.youtube.com/@RealCandaceO/streams"
YTDLP = shutil.which("yt-dlp") or str(Path.home() / ".local/bin/yt-dlp")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def latest_streams(n: int = 15) -> list[tuple[str, str]]:
    r = run([YTDLP, "--flat-playlist", "--print", "%(id)s\t%(title)s", CHANNEL, "--playlist-end", str(n)])
    if r.returncode != 0:
        raise SystemExit(f"listing failed: {r.stderr[-400:]}")
    return [tuple(l.split("\t", 1)) for l in r.stdout.splitlines() if "\t" in l]


def fetch(yid: str, out: Path, tries: int = 12) -> bool | None:
    out.mkdir(parents=True, exist_ok=True)
    base = [YTDLP, "--skip-download", "--ignore-no-formats-error", "--extractor-args", "youtube:player_client=ios",
            "-P", str(out), "-o", "%(id)s", f"https://www.youtube.com/watch?v={yid}"]
    if not (out / f"{yid}.info.json").exists():
        run(base[:1] + ["--write-info-json"] + base[1:])
    info = json.loads((out / f"{yid}.info.json").read_text(encoding="utf-8"))
    if "en-orig" not in (info.get("automatic_captions") or {}):
        return None  # captions not generated yet (common for a same-day live stream): try next run
    for i in range(tries):
        if (out / f"{yid}.en-orig.vtt").stat().st_size if (out / f"{yid}.en-orig.vtt").exists() else 0:
            return True
        run(base[:1] + ["--write-auto-subs", "--sub-langs", "en-orig", "--sub-format", "vtt"] + base[1:])
        if (out / f"{yid}.en-orig.vtt").exists():
            return True
        time.sleep(min(60 * (i + 1), 300))
    return False


def ep_number(title: str, prev: int) -> tuple[int, str | None]:
    m = re.search(r"\bEp\.?\s*(\d{3,4})\b", title)
    if m:
        return int(m.group(1)), None
    return prev + 1, f"title omits Ep number; {prev + 1} inferred from sequence after Ep {prev}"


def hms(dur: str) -> tuple[str, int]:
    p = [int(x) for x in dur.split(":")]
    s = p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}", s


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("work", type=Path)
    ap.add_argument("--max", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    mpath = CKA / "input" / "episode_manifest.json"
    man = json.loads(mpath.read_text(encoding="utf-8"))
    known = {e["youtube_id"] for e in man["episodes"]}
    new = []
    for yid, title in latest_streams():
        if yid in known:
            break
        new.append((yid, title))
    new = list(reversed(new))[: a.max]
    if not new:
        print("no new episodes")
        return 3
    print("new:", [t for _, t in new])
    if a.dry_run:
        return 0
    cap = a.work / "captions"
    seq = max(e["seq"] for e in man["episodes"])
    prev_ep = max(e.get("candace_ep_number") or 0 for e in man["episodes"])
    prepared = []
    for yid, _title in new:
        got = fetch(yid, cap)
        if got is None:
            print(f"captions not ready yet for {yid}; it and any later episodes wait for the next run")
            break
        if not got:
            print(f"captions still throttled (HTTP 429) for {yid}; stopping here")
            break
        info = json.loads((cap / f"{yid}.info.json").read_text(encoding="utf-8"))
        seq += 1
        ep, note = ep_number(info["title"], prev_ep)
        prev_ep = ep
        r = run([sys.executable, str(CKA / "scripts" / "vtt_to_cka.py"), str(cap / f"{yid}.en-orig.vtt"),
                 str(cap / f"{yid}.info.json"), str(seq), str(ep), str(CKA / "transcripts_corrected")])
        if r.returncode != 0:
            raise SystemExit(r.stderr)
        d = info["upload_date"]
        date = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        man["episodes"].append({"upload_date": date, "youtube_id": yid, "title": info["title"],
                                "url": f"https://www.youtube.com/watch?v={yid}", "candace_ep_number": ep,
                                "kind": "numbered_show", "notes": note, "seq": seq})
        with open(CKA / "input" / "episode_manifest.md", "a", encoding="utf-8") as f:
            f.write(f"| {seq} | {date} | numbered_show | {ep} | {yid} | {info['title']}{' (' + note + ')' if note else ''} |\n")
        with open(CKA / "input" / "youtube_links.txt", "a", encoding="utf-8") as f:
            f.write(f"https://www.youtube.com/watch?v={yid}\n")
        prepared.append({"seq": seq, "ep": ep, "youtube_id": yid, "date": date, "title": info["title"],
                         "description": info.get("description", "").split("\n")[0].strip(),
                         "duration": info["duration_string"], "ep_inferred": bool(note)})
    if not prepared:
        return 3
    man["counts"]["manifest_entries"] = len(man["episodes"])
    man["counts"]["numbered_show"] = sum(1 for x in man["episodes"] if x["kind"] == "numbered_show")
    man["generated_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    mpath.write_text(json.dumps(man, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    run([sys.executable, str(CKA / "scripts" / "apply_name_corrections.py")], cwd=REPO)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for p in prepared:
        tr = next((CKA / "transcripts_corrected").glob(f"episode_{p['seq']:03d}_*.md"))
        sha = hashlib.sha256(tr.read_bytes()).hexdigest()
        rng, _ = hms(p["duration"])
        inferred = " (inferred; title omits Ep number)" if p["ep_inferred"] else ""
        draft = f"""## 1. Meta-Data

- **Episode**: {p['seq']}
- **Monument**: cka
- **CKA seq**: {p['seq']}
- **YouTube id**: {p['youtube_id']}
- **Candace Ep**: {p['ep']}{inferred}
- **Source**: Candace Owens YouTube
- **Video Timestamp Range**: 00:00:00-{rng}
- **Extraction Timestamp (UTC)**: {now}
- **Transcript SHA-256**: {sha}

- **Episode Ledger Summary**:
  - (see registers)

# Episode {p['seq']} Analysis


## 2. Executive Summary

Episode {p['ep']} ({p['date']}). Per the episode description: {p['description']}

---

## 3. Artifact Register

## 4. Node Register

## 5. Claim Register

## 6. Meme Register

## 7. Optional Flags
"""
        cs.write_draft_text(p["seq"], draft)
        (CKA / "drafts" / ".transcript_sha" / f"episode_{p['seq']:03d}.sha256").write_text(sha + "\n", encoding="utf-8")
        p["transcript"] = str(tr)
    pack = a.work / "pack"
    r = run([sys.executable, str(CKA / "scripts" / "supplement" / "build_pack.py"), str(pack), "--staging", "staging",
             "--count", "1"], cwd=REPO)
    if r.returncode != 0:
        raise SystemExit(r.stderr)
    shutil.copy(CKA / "docs" / "daily" / "EXTRACT_PROMPT.md", pack / "EXTRACT_PROMPT.md")
    (a.work / "new_episodes.json").write_text(json.dumps(prepared, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([{k: p[k] for k in ("seq", "ep", "youtube_id", "date")} for p in prepared]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
