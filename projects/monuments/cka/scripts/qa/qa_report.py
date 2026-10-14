#!/usr/bin/env python3
"""Summarise QA reviewer results (results_NN.json in a pack) into a qa.md report.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/qa/qa_report.py PACK_DIR OUT_MD [--title TITLE]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

CHECKS = ("attribution", "accuracy", "person", "timestamp", "relevance")
TARGET = 0.02


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pack", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--title", default="QA spot-check")
    args = ap.parse_args()
    meta = json.loads((args.pack / "sample.json").read_text(encoding="utf-8"))
    rows = [r for p in sorted(args.pack.glob("results_*.json")) for r in json.loads(p.read_text(encoding="utf-8"))]
    want = {m["claim"] for m in meta["sample"]}
    got = {r["claim"] for r in rows}
    material = [r for r in rows if r.get("material")]
    rate = len(material) / len(rows) if rows else 0.0
    counts = {c: Counter(r.get(c, "?") for r in rows) for c in CHECKS}
    out = [f"# {args.title}", "",
           f"Sample: {len(rows)} of {meta['pool']} claims (rate {meta['rate']}, seed {meta['seed']}"
           f"{', since ' + meta['since'] if meta.get('since') else ', whole archive'}).",
           f"Missing results: {len(want - got)}." if want - got else "Every sampled claim was reviewed.", "",
           f"**Material-error rate: {rate:.1%}** ({len(material)} claims; target < {TARGET:.0%}: "
           f"{'met' if rate < TARGET else 'NOT met'}).", "", "| Check | Results |", "|---|---|"]
    out += [f"| {c} | {', '.join(f'{k} {v}' for k, v in sorted(counts[c].items()))} |" for c in CHECKS]
    for title, items in (("Material errors", material),
                         ("Minor findings", [r for r in rows if not r.get("material") and
                                             (r.get("accuracy") == "minor" or r.get("relevance") == "disputed")])):
        out += ["", f"## {title}", ""]
        out += [f"- **{r['claim']}** (ep{r['episode']}): {r.get('note', '')}"
                + (f" Proposed: {r['fix']}" if r.get("fix") else "") for r in items] or ["None."]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"reviewed {len(rows)}; material {len(material)} ({rate:.1%}); missing {len(want - got)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
