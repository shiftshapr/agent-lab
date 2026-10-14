#!/usr/bin/env python3
"""Merge newly integrated draft items into the existing inscription JSON of the given episodes.

The inscription builder rewrites whole files (series, model_version, object order), so after a supplement or skeleton
integration we build into a temp dir and fold in only what is new: claims and artifact sub-items not yet present,
new nodes, and meme entries (new, or with more occurrences). Existing objects are kept as they are; existing node
names and related lists are refreshed. It reports any existing id the rebuild would have lost (must be 0).

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/supplement/merge_inscriptions.py STAGING_DIR [extra_seq ...]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
BUILDER = CKA.parent / "bride_of_charlie" / "scripts" / "build_inscription_from_drafts.py"


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    staging = Path(sys.argv[1])
    eps = sorted({int(re.search(r"episode_(\d{3})", p.name).group(1)) for p in staging.glob("episode_*.md")}
                 | {int(x) for x in sys.argv[2:]})
    tmp = tempfile.mkdtemp()
    cmd = [sys.executable, str(BUILDER), "--drafts", str(CKA / "drafts"), "--inscription", tmp]
    for e in eps:
        cmd += ["--episode", str(e)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])
    lost_total = meme_changes = 0
    for e in eps:
        path = CKA / "inscription" / f"episode_{e:03d}.json"
        raw = path.read_text(encoding="utf-8")
        old = json.loads(raw)
        new = json.loads(Path(tmp, f"episode_{e:03d}.json").read_text(encoding="utf-8"))
        old_claims = {x["ref"] for x in old["claims"]}
        old_nodes = {x["ref"] for x in old["nodes"]}
        old_fams = {f.get("family_ref") for f in old["artifacts"]}
        old_subs = {s["ref"] for f in old["artifacts"] for s in f.get("sub_items", [])}
        new_claims = {x["ref"] for x in new["claims"]}
        new_subs = {s["ref"] for f in new["artifacts"] for s in f.get("sub_items", [])}
        lost_total += len((old_claims - new_claims) | (old_subs - new_subs))
        old["claims"] += [x for x in new["claims"] if x["ref"] not in old_claims]
        for fam in new["artifacts"]:
            if fam.get("family_ref") not in old_fams:
                old["artifacts"].append(fam)
                continue
            target = next(g for g in old["artifacts"] if g.get("family_ref") == fam.get("family_ref"))
            target["sub_items"] += [s for s in fam.get("sub_items", []) if s["ref"] not in old_subs]
        by_ref = {x["ref"]: x for x in new["nodes"]}
        for x in old["nodes"]:
            if x["ref"] in by_ref:
                for k in ("related_claims", "related_artifacts"):
                    if k in by_ref[x["ref"]]:
                        x[k] = sorted(set(x.get(k, [])) | set(by_ref[x["ref"]][k]))
                x["name"] = by_ref[x["ref"]].get("name", x.get("name"))
        old["nodes"] += [x for x in new["nodes"] if x["ref"] not in old_nodes]
        old.setdefault("memes", [])
        old_memes = {(m.get("ref") or m.get("@id")): m for m in old["memes"]}
        for m in new.get("memes", []):
            key = m.get("ref") or m.get("@id")
            if key not in old_memes:
                old["memes"].append(m)
                meme_changes += 1
            elif len(m.get("occurrences", [])) > len(old_memes[key].get("occurrences", [])):
                old_memes[key]["occurrences"] = m["occurrences"]
                meme_changes += 1
        path.write_text(json.dumps(old, indent=2, ensure_ascii="\\u" in raw) + "\n", encoding="utf-8")
    print(f"merged {len(eps)} episodes; meme entries added or extended {meme_changes}; "
          f"ids the rebuild would have lost: {lost_total}")
    return 1 if lost_total else 0


if __name__ == "__main__":
    raise SystemExit(main())
