#!/usr/bin/env python3
"""Build the confirmation pack: every material finding (and every name fix) from a verification pass, with the claim,
the finding, the proposed fix and the transcript window, for an Opus reviewer (docs/qa/CONFIRM_PROMPT.md).

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/qa/confirm_pack.py VERIFY_DIR OUT_DIR [--chunk 40]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_pack  # noqa: E402
import verify_pack  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("verify", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--chunk", type=int, default=40)
    args = ap.parse_args()
    rows = [r for p in sorted(args.verify.glob("results_*.json")) for r in json.loads(p.read_text(encoding="utf-8"))]
    todo = [r for r in rows if r.get("material") or (r.get("fix") or {}).get("names")]
    nodes = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"]
    args.out.mkdir(parents=True, exist_ok=True)
    cache: dict[int, tuple[dict[str, str], str, str]] = {}
    parts, k = [], 0
    for i, r in enumerate(todo):
        ep = int(r["episode"])
        if ep not in cache:
            tr = sorted((CKA / "transcripts_corrected").glob(f"episode_{ep:03d}_*"))
            cache = {ep: (qa_pack.claims_of((CKA / "drafts" / f"episode_{ep:03d}.md").read_text(encoding="utf-8")),
                          tr[0].read_text(encoding="utf-8", errors="ignore") if tr else "", tr[0].name if tr else "")}
        blocks, transcript, tname = cache[ep]
        blk = blocks.get(r["claim"], "(claim not found)")
        ts = re.search(r"^Claim Timestamp:\s*(\d{1,2}):(\d{2}):(\d{2})", blk, re.M)
        at = qa_pack.secs(*ts.groups()) if ts else 0
        ids = sorted(set(re.findall(r"\bN-\d+\b", blk + json.dumps(r.get("fix") or {}))), key=lambda x: int(x[2:]))
        named = "; ".join(f"{x} {nodes.get(x, {}).get('canonical_name', '?')}" for x in ids) or "(none)"
        finding = {key: r.get(key) for key in ("attribution", "accuracy", "person", "timestamp", "note")}
        parts.append(f"## {r['claim']} (episode {ep})\n\n{blk}\n\nNode ids: {named}\n\n"
                     f"First reviewer's finding: {json.dumps(finding, ensure_ascii=False)}\n\n"
                     f"Proposed fix: {json.dumps(r.get('fix') or {}, ensure_ascii=False)}\n\n"
                     f"Transcript ({CKA / 'transcripts_corrected' / tname}) around the timestamp:\n\n"
                     f"```\n{verify_pack.window(transcript, at) if transcript else '(no transcript)'}\n```\n")
        if len(parts) == args.chunk or i == len(todo) - 1:
            k += 1
            (args.out / f"confirm_{k:03d}.md").write_text("\n".join(parts), encoding="utf-8")
            parts = []
    print(f"{len(todo)} findings to confirm in {k} chunks (of {len(rows)} claims checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
