#!/usr/bin/env python3
"""
Editorial transcript pass — apply regex rules from config/editorial_transcript_rules.json.

Targets scholarly cleaned text (not raw STT preservation). Default: transcripts_corrected/
and inscription/episode_*_transcript.txt. Does not modify transcripts/ (raw) unless
--include-raw is set.

Usage:
  cd projects/monuments/bride_of_charlie
  python3 scripts/editorial_transcript_pass.py --dry-run
  python3 scripts/editorial_transcript_pass.py
  python3 scripts/editorial_transcript_pass.py --include-raw
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
RULES_FILE = PROJECT_DIR / "config" / "editorial_transcript_rules.json"


_FLAG = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
}


def load_rules(path: Path) -> list[tuple[re.Pattern[str], str, str]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: list[tuple[re.Pattern[str], str, str]] = []
    for r in doc.get("rules", []):
        pat = r.get("pattern", "")
        repl = r.get("repl", "")
        comment = r.get("comment", "")
        if not pat:
            continue
        flags = 0
        for name in r.get("flags", []) or []:
            flags |= _FLAG.get(str(name).upper(), 0)
        out.append((re.compile(pat, flags), repl, comment))
    return out


def apply_to_text(text: str, rules: list[tuple[re.Pattern[str], str, str]]) -> tuple[str, int]:
    n = 0
    s = text
    for rx, repl, _ in rules:
        s, c = rx.subn(repl, s)
        n += c
    return s, n


def collect_targets(
    *,
    include_raw: bool,
    only_inscription: bool,
) -> list[Path]:
    files: list[Path] = []
    ins = PROJECT_DIR / "inscription"
    for p in sorted(ins.glob("episode_*_transcript.txt")):
        files.append(p)
    if only_inscription:
        return files
    corr = PROJECT_DIR / "transcripts_corrected"
    if corr.is_dir():
        for p in sorted(corr.glob("episode_*.txt")):
            files.append(p)
    if include_raw:
        raw = PROJECT_DIR / "transcripts"
        if raw.is_dir():
            for p in sorted(raw.glob("episode_*.txt")):
                files.append(p)
    # Dedupe by resolved path
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in files:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply editorial regex pass to transcripts")
    ap.add_argument("--dry-run", action="store_true", help="Print counts only, do not write")
    ap.add_argument("--include-raw", action="store_true", help="Also modify transcripts/ (raw)")
    ap.add_argument("--only-inscription", action="store_true", help="Only inscription/*_transcript.txt")
    ap.add_argument("--rules", type=Path, default=RULES_FILE, help="JSON rules file")
    args = ap.parse_args()

    if not args.rules.is_file():
        print(f"[editorial] Rules not found: {args.rules}", file=sys.stderr)
        return 1

    rules = load_rules(args.rules)
    targets = collect_targets(
        include_raw=args.include_raw,
        only_inscription=args.only_inscription,
    )
    if not targets:
        print("[editorial] No transcript files found.")
        return 0

    total_files = 0
    total_subs = 0
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"[editorial] Skip {path}: {e}", file=sys.stderr)
            continue
        new_text, subs = apply_to_text(text, rules)
        if subs:
            total_files += 1
            total_subs += subs
            print(f"[editorial] {path.relative_to(PROJECT_DIR)}: {subs} replacement(s)")
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8")
    print(f"[editorial] Done. Files touched: {total_files}, total replacements: {total_subs}")
    if args.dry_run and total_subs:
        print("[editorial] (dry-run — no files written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
