#!/usr/bin/env python3
"""Check a staged CKA episode draft against its transcript and the reference pack.

Usage: SKELETON_PACK=<pack dir> check_skeleton_staging.py NNN [NNN ...]
(pack dir holds nodes.tsv, memes.tsv, claims_index.tsv and staging/)
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
SECTIONS = ["## 1. Meta-Data", "## 2. Executive Summary", "## 3. Artifact Register", "## 4. Node Register",
            "## 5. Claim Register", "## 6. Meme Register", "## 7. Optional Flags"]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def secs(ts: str) -> int:
    p = [int(x) for x in ts.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def check(ep: int) -> list[str]:
    errs = []
    path = PACK / "staging" / f"episode_{ep:03d}.md"
    if not path.is_file():
        return [f"missing {path}"]
    t = path.read_text(encoding="utf-8")
    tr_path = glob.glob(str(CKA / "transcripts_corrected" / f"episode_{ep:03d}_*"))[0]
    tr = Path(tr_path).read_text(encoding="utf-8")
    trn = norm(tr)
    dur = re.search(r'^duration:\s*"?([\d:]+)"?', tr, re.M)
    dur_s = secs(dur.group(1)) if dur else 10**9
    for s in SECTIONS:
        if s not in t:
            errs.append(f"missing section {s}")
    sec = {}
    for i, s in enumerate(SECTIONS):
        a = t.find(s)
        b = t.find(SECTIONS[i + 1]) if i + 1 < len(SECTIONS) else len(t)
        sec[s] = t[a:b] if a >= 0 else ""
    if "—" in re.sub(r"(Transcript Snippet|Quoted text|Quote):.*", "", t):
        errs.append("em dash in prose")
    node_rows = set(re.findall(r"^\*\*(N-[\w]+)\*\*", sec["## 4. Node Register"], re.M))
    cited = set(re.findall(r"\bN-(?:\d+|[PT]\d+)\b", t)) - node_rows
    cited = {c for c in cited if not re.search(rf"^\*\*{c}\*\*", t, re.M)}
    if cited:
        errs.append(f"cited without node row: {sorted(cited)[:10]}")
    for n in node_rows:
        if re.fullmatch(r"N-\d+", n) and n not in REAL_N:
            errs.append(f"unknown real node {n}")
    for m in set(re.findall(r"^\*\*(M-\d+)\*\*", t, re.M)):
        if m not in REAL_M:
            errs.append(f"unknown meme {m}")
    claims = re.split(r"(?m)^(?=\*\*C-)", sec["## 5. Claim Register"])[1:]
    for c in claims:
        cid = re.match(r"\*\*(C-[\w]+)\*\*", c).group(1)
        ts = re.search(r"^Claim Timestamp:\s*(\S+)", c, re.M)
        if not ts or not re.fullmatch(r"\d{2}:\d{2}:\d{2}", ts.group(1)):
            errs.append(f"{cid} bad timestamp")
        elif secs(ts.group(1)) > dur_s + 5:
            errs.append(f"{cid} timestamp past end")
        sn = re.search(r"^Transcript Snippet:\s*(.+)$", c, re.M)
        if not sn:
            errs.append(f"{cid} no snippet")
        elif norm(sn.group(1)) not in trn:
            errs.append(f"{cid} snippet not verbatim")
        for field in ("Supports", "Contradicts", "Revises", "Qualifies"):
            fm = re.search(rf"^{field}:\s*(.+)$", c, re.M)
            if fm:
                for ref in re.findall(r"C-\d+", fm.group(1)):
                    if ref not in CLAIM_EP:
                        errs.append(f"{cid} {field} unknown {ref}")
                    elif CLAIM_EP[ref] >= ep:
                        errs.append(f"{cid} {field} {ref} is not from an earlier episode")
        if not re.search(r"^Anchored Artifacts:", c, re.M):
            errs.append(f"{cid} no Anchored Artifacts line")
    persons = [n for n in node_rows if n.startswith("N-P")]
    body = t.replace(sec["## 4. Node Register"], "")
    for p in persons:
        if not re.search(rf"\b{p}\b", body):
            errs.append(f"person {p} not cited outside register")
    return errs


if __name__ == "__main__":
    for a in sys.argv[1:]:
        ep = int(a)
        e = check(ep)
        t = (PACK / "staging" / f"episode_{ep:03d}.md")
        txt = t.read_text() if t.is_file() else ""
        counts = {k: len(re.findall(p, txt, re.M)) for k, p in
                  {"claims": r"^\*\*C-", "artifacts": r"^\*\*A-[\w]+\.\d+\*\*", "newP": r"^\*\*N-P\d+\*\*",
                   "newT": r"^\*\*N-T\d+\*\*", "memes": r"^\*\*M-"}.items()}
        print(f"ep {ep}: {'OK' if not e else 'FAIL'} {counts}")
        for x in e:
            print("   -", x)
