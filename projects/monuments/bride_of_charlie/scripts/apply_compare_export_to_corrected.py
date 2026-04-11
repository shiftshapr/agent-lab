#!/usr/bin/env python3
"""
Apply JSON from transcript_raw_vs_corrected_review (Copy JSON / Download JSON)
to transcripts_corrected/ episode files.

Uses corrected line span from hunkKey (__cSTART-END__). Applies patches
per episode in descending line order so indices stay valid.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
CORR = PROJECT / "transcripts_corrected"

HUNK_RE = re.compile(r"__c(\d+)-(\d+)__(replace|delete|insert)__")


def _parse_hunk_key(key: str) -> tuple[int, int, str]:
    m = HUNK_RE.search(key)
    if not m:
        raise ValueError(f"No __cSTART-END__op__ in hunkKey: {key}")
    return int(m.group(1)), int(m.group(2)), m.group(3)


def _sort_key(item: dict) -> tuple[str, int, int]:
    c1, c2, _ = _parse_hunk_key(item["hunkKey"])
    return item["episode"], -c1, -c2


def _normalize_implement_text(it: dict) -> str:
    raw_txt = (it.get("implementText") or "").strip()
    if raw_txt in ("(empty)",):
        raw_txt = ""
    return raw_txt


def _drop_deletes_superseded_by_replace_on_same_span(items: list[dict]) -> list[dict]:
    """If delete and non-empty replace share the same corrected span, keep replace only."""
    replace_spans: set[tuple[str, int, int]] = set()
    for it in items:
        c1, c2, op = _parse_hunk_key(it["hunkKey"])
        if op != "replace":
            continue
        if not _normalize_implement_text(it):
            continue
        replace_spans.add((it["episode"], c1, c2))
    out: list[dict] = []
    for it in items:
        c1, c2, op = _parse_hunk_key(it["hunkKey"])
        if op == "delete" and (it["episode"], c1, c2) in replace_spans:
            continue
        out.append(it)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "json_path",
        type=Path,
        nargs="?",
        default=PROJECT / "reports" / "apply_compare_payload.json",
        help="Export JSON path",
    )
    args = ap.parse_args()
    data = json.loads(args.json_path.read_text(encoding="utf-8"))
    items: list[dict] = data["items"]
    items = _drop_deletes_superseded_by_replace_on_same_span(items)
    items_sorted = sorted(items, key=_sort_key)

    by_ep: dict[str, list[dict]] = {}
    for it in items_sorted:
        by_ep.setdefault(it["episode"], []).append(it)

    for ep, eplist in by_ep.items():
        path = CORR / f"{ep}.txt"
        if not path.is_file():
            print(f"SKIP missing {path.name}", file=sys.stderr)
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for it in eplist:
            c1, c2, op = _parse_hunk_key(it["hunkKey"])
            raw_txt = _normalize_implement_text(it)
            lo = c1 - 1
            hi_excl = c2  # lines c1..c2 inclusive → slice [lo:hi_excl] with hi_excl = c2

            if op == "delete" or (op == "replace" and raw_txt == ""):
                del lines[lo:hi_excl]
                continue

            if op == "replace":
                new_lines = raw_txt.split("\n")
                n_old = hi_excl - lo
                if n_old == len(new_lines):
                    lines[lo:hi_excl] = new_lines
                elif n_old == 1:
                    lines[lo : lo + 1] = new_lines
                else:
                    raise SystemExit(
                        f"{path.name}: replace c{c1}-{c2} needs {n_old} lines, "
                        f"got {len(new_lines)} new lines — {it['hunkKey']}"
                    )
                continue

            if op == "insert":
                for k, nl in enumerate(raw_txt.split("\n")):
                    lines.insert(lo + k, nl)
                continue

            raise SystemExit(f"Unknown opcode {op!r} in {it['hunkKey']}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Updated {path.name} ({len(eplist)} patch(es))")


if __name__ == "__main__":
    main()
