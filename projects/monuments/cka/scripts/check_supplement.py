#!/usr/bin/env python3
"""Check a supplement file (additions only) against transcript, existing draft and reference pack.

Usage: check_supplement.py NNN [--dir staging_supplement]
"""
import csv
import os
import glob
import re
import sys
from pathlib import Path

PACK = Path(os.environ.get("SKELETON_PACK", "."))
CKA = Path(__file__).resolve().parents[1]
REAL_N = {r["id"] for r in csv.DictReader(open(PACK / "nodes.tsv"), delimiter="\t")}
REAL_M = {r["id"] for r in csv.DictReader(open(PACK / "memes.tsv"), delimiter="\t")}
CLAIM_EP = {r["id"]: int(r["episode"]) for r in csv.DictReader(open(PACK / "claims_index.tsv"), delimiter="\t")}


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def secs(ts):
    p = [int(x) for x in ts.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2]


def main():
    ep = int(sys.argv[1])
    sub = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else "staging_supplement"
    path = PACK / sub / f"episode_{ep:03d}.md"
    t = path.read_text(encoding="utf-8")
    draft = (CKA / "drafts" / f"episode_{ep:03d}.md").read_text(encoding="utf-8")
    tr = Path(glob.glob(str(CKA / "transcripts_corrected" / f"episode_{ep:03d}_*"))[0]).read_text(encoding="utf-8")
    trn = norm(tr)
    marks = [secs(f"0:{a}:{b}") if not c else secs(f"{a}:{b}:{c}") for a, b, c in re.findall(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]", tr)]
    end = max(marks) + 120 if marks else 10**9
    errs = []
    rows = set(re.findall(r"^\*\*(N-[\w]+)\*\*", t, re.M)) | set(re.findall(r"^\*\*(N-\d+)\*\*", draft, re.M))
    cited = set(re.findall(r"\bN-(?:\d+|[PT]\d+)\b", t))
    missing = sorted(c for c in cited if c not in rows)
    if missing:
        errs.append(f"cited without a node row (draft or supplement): {missing[:12]}")
    for n in rows:
        if re.fullmatch(r"N-\d+", n) and n not in REAL_N:
            errs.append(f"unknown node {n}")
    for m in set(re.findall(r"^\*\*(M-\d+)\*\*", t, re.M)):
        if m not in REAL_M:
            errs.append(f"unknown meme {m}")
    if "—" in re.sub(r"(Transcript Snippet|Quoted text|Quote):.*", "", t):
        errs.append("em dash in prose")
    draft_claims = set(re.findall(r"^\*\*(C-\d+)\*\*", draft, re.M))
    for blk in re.split(r"(?m)^(?=\*\*C-)", t)[1:]:
        cid = re.match(r"\*\*(C-[\w]+)\*\*", blk).group(1)
        if re.fullmatch(r"C-\d+", cid):
            errs.append(f"{cid}: supplement must not restate an existing claim")
            continue
        ts = re.search(r"^Claim Timestamp:\s*(\d{2}:\d{2}:\d{2})\s*$", blk, re.M)
        if not ts:
            errs.append(f"{cid} bad timestamp")
        elif secs(ts.group(1)) > end:
            errs.append(f"{cid} timestamp past end")
        sn = re.search(r"^Transcript Snippet:\s*(.+)$", blk, re.M)
        if not sn or norm(sn.group(1)) not in trn:
            errs.append(f"{cid} snippet missing or not verbatim")
        for field in ("Supports", "Contradicts", "Revises", "Qualifies"):
            fm = re.search(rf"^{field}:\s*(.+)$", blk, re.M)
            for ref in re.findall(r"C-\d+", fm.group(1)) if fm else []:
                if ref in draft_claims:
                    continue
                if ref not in CLAIM_EP:
                    errs.append(f"{cid} {field} unknown {ref}")
                elif CLAIM_EP[ref] > ep:
                    errs.append(f"{cid} {field} {ref} is from a later episode")
    for blk in re.split(r"(?m)^(?=\*\*M-)", t)[1:]:
        for q in re.findall(r"^Quote:\s*(.+)$", blk, re.M):
            if norm(q).rstrip(".…") not in trn and not q.endswith("..."):
                errs.append(f"meme quote not verbatim: {q[:50]}")
    n_claims = len(re.findall(r"^\*\*C-L\d+\*\*", t, re.M))
    print(f"ep {ep}: {'OK' if not errs else 'FAIL'} new_claims={n_claims} existing={len(draft_claims)}")
    for e in errs:
        print("   -", e)


if __name__ == "__main__":
    main()
