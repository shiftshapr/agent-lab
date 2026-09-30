#!/usr/bin/env python3
"""Wire Person register orphans to Claim Related Nodes (same episode)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "projects" / "monuments" / "scripts"))
from dia_preflight import (  # noqa: E402
    collect_claim_artifact_related_n_ids,
    collect_register_entries,
    first_introduction_meta,
    load_draft_episodes,
)

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
PERSON_TYPES = frozenset({"person", "investigationtarget"})


def main() -> int:
    episodes = load_draft_episodes(DRAFTS)
    ingest = [e for e in episodes if e[0] >= 11]
    register = collect_register_entries(episodes)
    intro = first_introduction_meta(register)
    cited = collect_claim_artifact_related_n_ids(ingest)
    fixed = 0

    for nid, ent in intro.items():
        is_person = ent.node_type in PERSON_TYPES or (
            ent.nid < 1000 and ent.node_type not in {"topic", "organization", "organisation", "place", "org"}
        )
        if not is_person or nid in cited:
            continue
        path = DRAFTS / ent.episode_file
        text = path.read_text(encoding="utf-8")
        tokens = [t for t in re.split(r"[^\w']+", ent.name) if len(t) > 2][:3]
        if not tokens:
            continue
        pat = re.compile(
            rf"(\*\*C-\d+\*\*[^\n]*\n(?:(?!\*\*C-)[^\n]*\n)*?Related Nodes:\s*)([^\n]+)",
            re.I,
        )
        for cm in pat.finditer(text):
            block = cm.group(0)
            if not any(t.lower() in block.lower() for t in tokens):
                continue
            if f"N-{nid}" in cm.group(2):
                break
            nodes = cm.group(2).rstrip() + f", N-{nid}"
            text = text[: cm.start(2)] + nodes + text[cm.end(2) :]
            path.write_text(text, encoding="utf-8")
            fixed += 1
            cited.add(nid)
            break
        else:
            # artifact *Related:* with C-
            for token in tokens:
                ap = re.compile(
                    rf"(\*\*A-\d+\.\d+\*\*[^\n]*{re.escape(token)}[^\n]*\n(?:(?!\*\*A-)[^\n]*\n)*?)(\*Related:[^\n]*\n)",
                    re.I,
                )
                m = ap.search(text)
                if m and f"N-{nid}" not in m.group(2):
                    rel = m.group(2).strip()
                    if "C-" in rel:
                        inner = rel[1:-1].replace("Related:", "").strip()
                        new = f"*Related: {inner}, N-{nid}*"
                    else:
                        new = f"*Related: N-{nid}*"
                    text = text[: m.start(2)] + new + "\n" + text[m.end(2) :]
                    path.write_text(text, encoding="utf-8")
                    fixed += 1
                    cited.add(nid)
                    break

    print(f"orphan fixes: {fixed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
