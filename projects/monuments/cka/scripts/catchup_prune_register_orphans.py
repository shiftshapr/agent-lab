#!/usr/bin/env python3
"""Drop person register rows with no Claim/Artifact citation (catch-up orphan cleanup)."""

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
FROM_EP = 21
HEADER = re.compile(r"^\*\*N-(\d+)\*\*[^\n]*\n(?:.*?\n)*?(?=^\*\*N-\d+\*\*|\n## |\Z)", re.MULTILINE)


def main() -> int:
    episodes = load_draft_episodes(DRAFTS)
    ingest = [e for e in episodes if e[0] >= FROM_EP]
    register = collect_register_entries(episodes)
    intro = first_introduction_meta(register)
    cited = collect_claim_artifact_related_n_ids(ingest)
    removed = 0
    for nid, ent in list(intro.items()):
        is_person = ent.node_type in PERSON_TYPES or (
            ent.nid < 1000 and ent.node_type not in {"topic", "organization", "organisation", "place", "org"}
        )
        ep_num = int(re.search(r"episode_(\d+)", ent.episode_file).group(1))
        if not is_person or nid in cited or ep_num < FROM_EP:
            continue
        path = DRAFTS / ent.episode_file
        text = path.read_text(encoding="utf-8")
        pat = re.compile(
            rf"^\*\*N-{nid}\*\*[^\n]*\n(?:.*?\n)*?(?=^\*\*N-\d+\*\*|\n## |\Z)",
            re.MULTILINE,
        )
        new_text, n = pat.subn("", text, count=1)
        if n:
            path.write_text(new_text, encoding="utf-8")
            removed += 1
    print(f"register blocks removed: {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
