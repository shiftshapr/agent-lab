#!/usr/bin/env python3
"""
Validate inscription JSON + transcript pairing.

- meta.transcript_sha256 must match bytes of resolved transcript (same rules as sync_transcript_hashes).
- Fail if any string value contains unresolved Phase-1 placeholders: NODE_*, CLAIM_*, ART_* (word boundary).

Usage:
  cd projects/monuments/bride_of_charlie
  python3 scripts/validate_inscription_bundle.py
  python3 scripts/validate_inscription_bundle.py --episodes 1-7
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

PLACEHOLDER_RE = re.compile(r"\b(?:NODE_|CLAIM_|ART_)\d+(?:\.\d+)?\b")

# Transcript / JSON string hygiene: known recurring STT garbage (add patterns here; run editorial pass to fix).
_FORBIDDEN_IN_TRANSCRIPTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bLorie France\b", re.IGNORECASE), "Lorie France → use Lori Frantzve (editorial pass)"),
    (re.compile(r"Kenton Lorie", re.IGNORECASE), "Kenton Lorie → Kent and Lori Frantzve (editorial pass)"),
    (re.compile(r"France,\s*Gwinta", re.IGNORECASE), "France, Gwinta → Frantzve, Guinta in Lori name-chain (ep4; editorial pass)"),
    (re.compile(r"\bGwinta\b", re.IGNORECASE), "Gwinta → Guinta (editorial pass)"),
    (
        re.compile(r"Thanks alumni Erika France for", re.IGNORECASE),
        "Ep6 Cocopah tweet: use @ErikaFrantzve + #CocopahPRIDE (editorial pass)",
    ),
    (
        re.compile(r"Thanks alumni Erica France for", re.IGNORECASE),
        "Ep6 Cocopah tweet STT: use @ErikaFrantzve + #CocopahPRIDE (editorial pass)",
    ),
    (
        re.compile(r"\bFrance Baststein\b", re.IGNORECASE),
        "Ep5 ~01:31: STT mangled Candace pun—use Frantzvestein (editorial pass)",
    ),
]


def resolve_transcript(ep: int) -> Path | None:
    ins = PROJECT_DIR / "inscription" / f"episode_{ep:03d}_transcript.txt"
    if ins.is_file():
        return ins
    corr = sorted((PROJECT_DIR / "transcripts_corrected").glob(f"episode_{ep:03d}_*.txt"))
    if corr:
        return corr[0]
    raw = sorted((PROJECT_DIR / "transcripts").glob(f"episode_{ep:03d}_*.txt"))
    if raw:
        return raw[0]
    return None


def iter_strings(obj, path: str = "$") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(iter_strings(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(iter_strings(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        out.append((path, obj))
    return out


def _scan_text_for_forbidden(label: str, text: str, errors: list[str]) -> None:
    for rx, hint in _FORBIDDEN_IN_TRANSCRIPTS:
        if rx.search(text):
            errors.append(f"{label}: forbidden pattern ({hint})")


def parse_episodes_arg(spec: str | None) -> set[int] | None:
    """``1,3,5`` or ``1-7`` or ``1-3,5,7`` → set of episode numbers. Empty / invalid → None (all)."""
    if not spec or not str(spec).strip():
        return None
    out: set[int] = set()
    for chunk in str(spec).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            parts = chunk.split("-", 1)
            if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                lo, hi = int(parts[0].strip()), int(parts[1].strip())
                a, b = min(lo, hi), max(lo, hi)
                out.update(range(a, b + 1))
                continue
        if chunk.isdigit():
            out.add(int(chunk))
    return out if out else None


def _transcript_episode_num(name: str) -> int | None:
    m = re.match(r"episode_(\d{3})_transcript\.txt$", name, re.I)
    return int(m.group(1)) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate inscription JSON + transcript bundle")
    ap.add_argument(
        "--episodes",
        type=str,
        default=None,
        metavar="SPEC",
        help="Limit checks to episode numbers: e.g. 1-7 or 1,2,3 (default: all inscription files)",
    )
    args = ap.parse_args()
    ep_filter = parse_episodes_arg(args.episodes)

    errors: list[str] = []
    for tpath in sorted((PROJECT_DIR / "inscription").glob("episode_*_transcript.txt")):
        tep = _transcript_episode_num(tpath.name)
        if ep_filter is not None and tep is not None and tep not in ep_filter:
            continue
        _scan_text_for_forbidden(tpath.name, tpath.read_text(encoding="utf-8"), errors)

    for jpath in sorted((PROJECT_DIR / "inscription").glob("episode_*.json")):
        if not re.match(r"episode_\d{3}\.json$", jpath.name):
            continue
        ep = int(jpath.name[8:11])
        if ep_filter is not None and ep not in ep_filter:
            continue
        data = json.loads(jpath.read_text(encoding="utf-8"))
        meta = data.get("meta") or {}
        want = meta.get("transcript_sha256")
        tpath = resolve_transcript(ep)
        if tpath and tpath.is_file():
            got = hashlib.sha256(tpath.read_bytes()).hexdigest()
            if want != got:
                errors.append(
                    f"{jpath.name}: transcript_sha256 mismatch (json={want[:16] if want else '∅'}… vs file={got[:16]}…) source={tpath.name}"
                )
        elif want:
            errors.append(f"{jpath.name}: has transcript_sha256 but no transcript file for ep {ep}")

        for pth, s in iter_strings(data):
            if PLACEHOLDER_RE.search(s):
                errors.append(f"{jpath.name} {pth}: unresolved placeholder in {s[:80]!r}…")
            _scan_text_for_forbidden(f"{jpath.name} {pth}", s, errors)

    if errors:
        print("[validate] FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    scope = f" (episodes {sorted(ep_filter)})" if ep_filter else ""
    print(f"[validate] OK{scope}: hashes, no forbidden name STT, no ART_/CLAIM_/NODE_ placeholders.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
