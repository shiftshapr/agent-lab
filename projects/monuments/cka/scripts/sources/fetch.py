#!/usr/bin/env python3
"""Fetch the source streams (ROADMAP 4.1) and keep the source manifest.

For each item in sources/streams.json not yet in sources/manifest.json (or --refetch), downloads the original into
~/agent-lab-data/cka_sources/<stream>/, records sha256, size and retrieval time, extracts text (PDF via pypdf in
~/agent-lab-data/cka_sources/.venv; HTML stripped to text with the transcript's speaker/time markers kept) to
<stream>/<S-id>.txt, and assigns a stable S-id (by URL). The repo holds only the manifest; originals and extracts stay
private. ADS-B release items download the release's tar parts (large; --skip-large to skip).

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/sources/fetch.py [--stream ID] [--skip-large] [--refetch]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
DATA = Path.home() / "agent-lab-data" / "cka_sources"
PYPDF = DATA / ".venv" / "bin" / "python"
UA = {"User-Agent": "Mozilla/5.0 (CKA archive source fetch)"}


def get(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def html_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h\d>", "\n", raw)
    t = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n\n", t).strip() + "\n"


def pdf_text(p: Path, out: Path) -> None:
    code = ("import sys,pypdf;r=pypdf.PdfReader(sys.argv[1]);"
            "open(sys.argv[2],'w').write('\\n'.join(f'[page {i+1}]\\n'+(pg.extract_text() or '') for i,pg in enumerate(r.pages)))")
    subprocess.run([str(PYPDF), "-c", code, str(p), str(out)], check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stream")
    ap.add_argument("--skip-large", action="store_true")
    ap.add_argument("--refetch", action="store_true")
    a = ap.parse_args()
    streams = json.loads((CKA / "sources" / "streams.json").read_text(encoding="utf-8"))["streams"]
    mpath = CKA / "sources" / "manifest.json"
    man = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {"sources": []}
    by_url = {s["url"]: s for s in man["sources"]}
    next_n = max((int(s["id"][2:]) for s in man["sources"]), default=0) + 1
    for st in streams:
        if a.stream and st["id"] != a.stream:
            continue
        sdir = DATA / st["id"]
        sdir.mkdir(parents=True, exist_ok=True)
        for it in st["items"]:
            rec = by_url.get(it["url"])
            if rec and not a.refetch and rec.get("sha256"):
                continue
            if not rec:
                rec = {"id": f"S-{next_n}", "stream": st["id"], "tier": st["tier"], "title": it["title"], "date": it.get("date"),
                       "publisher": it.get("publisher"), "url": it["url"], "format": it["format"]}
                next_n += 1
                man["sources"].append(rec)
                by_url[it["url"]] = rec
            sid = rec["id"]
            try:
                if it["format"] == "adsb-release":
                    if a.skip_large:
                        print(f"{sid}: skipped (large)")
                        continue
                    tag = it["release_tag"]
                    subprocess.run(["gh", "release", "download", tag, "-R", "adsblol/globe_history_2025", "-D", str(sdir),
                                    "--skip-existing"], check=True)
                    parts = sorted(sdir.glob(f"{tag}.tar.*"))
                    rec.update({"release_tag": tag, "files": [p.name for p in parts],
                                "bytes": sum(p.stat().st_size for p in parts),
                                "sha256": hashlib.sha256("".join(sha256(p) for p in parts).encode()).hexdigest()})
                else:
                    ext = "pdf" if it["format"] == "pdf" else "html"
                    dest = sdir / f"{sid}.{ext}"
                    urls = [it["url"]] + it.get("mirrors", [])
                    for u in urls:
                        try:
                            get(u, dest)
                            rec["fetched_from"] = u
                            break
                        except Exception as e:  # try the next mirror
                            print(f"{sid}: {u} failed ({e})")
                    else:
                        raise RuntimeError("all URLs failed")
                    txt = sdir / f"{sid}.txt"
                    if ext == "pdf":
                        pdf_text(dest, txt)
                    else:
                        txt.write_text(html_text(dest.read_text(encoding="utf-8", errors="ignore")), encoding="utf-8")
                    rec.update({"file": dest.name, "bytes": dest.stat().st_size, "sha256": sha256(dest),
                                "text_file": txt.name, "text_words": len(txt.read_text(encoding="utf-8", errors="ignore").split())})
                rec.pop("error", None)
                rec["retrieved_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                print(f"{sid} {st['id']}: {rec['title']} ({rec.get('bytes', 0):,} bytes)")
            except Exception as e:
                rec["error"] = str(e)[:300]
                print(f"{sid}: FAILED {e}")
            mpath.write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
