#!/usr/bin/env python3
"""
Bill D-style hostile hard-gates audit for CKA Batch 1 (seq 1–10).

Mirrors the blocking set in adversarial_raw.json (META_RANGE_LIE, ledger drift,
leftover ads, org/place orphan-with-airtime, meta source, N-2 name sync).

Exit 0 only when P0=0 and P1=0.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/hostile_hard_gates_audit.py
  python3 projects/monuments/cka/scripts/hostile_hard_gates_audit.py --json /tmp/cka-hostile.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
CORR = CKA / "transcripts_corrected"
INS = CKA / "inscription"
CANON = CKA / "canonical" / "nodes.json"

NODE_HEADER = re.compile(r"^\*\*N-(\d+)\*\*\s+(.+)$", re.MULTILINE)
NODE_TYPE = re.compile(r"^Node Type:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
AD_PATTERNS = [
    re.compile(r"(?i)american\s*financing"),
    re.compile(r"(?i)americanfinancing"),
    re.compile(r"(?i)promo\s*code"),
    re.compile(r"(?i)\buse\s+code\b"),
]
TOPIC_ORG_TYPES = frozenset({"organization", "organisation", "org", "place"})


@dataclass
class Finding:
    severity: str
    code: str
    episode: int | None
    id: str | None
    detail: str


def _load_yt_durations() -> dict[str, int]:
    path = CKA / "config" / "yt_durations.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): int(v) for k, v in doc["by_youtube_id"].items()}


def _range_end_seconds(raw: str) -> int | None:
    raw = raw.strip().replace("—", "-").replace("–", "-")
    m = re.search(r"00:00:00-(\d{2}):(\d{2}):(\d{2})", raw)
    if not m:
        m = re.search(r"-(\d{2}):(\d{2}):(\d{2})\s*$", raw)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))


def _transcript_for_ep(ep: int) -> str:
    for p in CORR.glob(f"episode_{ep:03d}_*.txt"):
        return p.read_text(encoding="utf-8")
    return ""


def _airtime_tokens(name: str) -> list[str]:
    tokens: list[str] = []
    for part in re.split(r"[/(),]", name):
        w = part.strip()
        if len(w) >= 4 and w.lower() not in {"utah", "utah"}:
            tokens.append(w)
    if len(name) >= 4:
        tokens.append(name.split("(")[0].strip())
    # dedupe preserving order
    out: list[str] = []
    seen: set[str] = set()
    for t in tokens:
        k = t.lower()
        if k and k not in seen and len(k) >= 3:
            seen.add(k)
            out.append(t)
    return out[:4]


def _wired_on_claim_or_artifact(content: str, nid: str) -> bool:
    if re.search(rf"^Related Nodes:.*\b{re.escape(nid)}\b", content, re.MULTILINE | re.IGNORECASE):
        return True
    pre = content.split("## 4. Node Register")[0]
    return bool(re.search(rf"^\*Related:.*\b{re.escape(nid)}\b", pre, re.MULTILINE))


def _register_first_intro() -> dict[str, int]:
    first: dict[str, int] = {}
    for path in sorted(DRAFTS.glob("episode_*.md")):
        m = re.search(r"episode_(\d+)", path.name)
        if not m:
            continue
        ep = int(m.group(1))
        if ep == 0:
            continue
        for hm in NODE_HEADER.finditer(path.read_text(encoding="utf-8")):
            nid = f"N-{hm.group(1)}"
            first.setdefault(nid, ep)
    return first


def run_audit() -> list[Finding]:
    findings: list[Finding] = []
    yt = _load_yt_durations()
    first_intro = _register_first_intro()

    for ep in range(1, 11):
        draft_path = DRAFTS / f"episode_{ep:03d}.md"
        if not draft_path.is_file():
            continue
        text = draft_path.read_text(encoding="utf-8")
        ytid_m = re.search(r"- \*\*YouTube id\*\*:\s*(\S+)", text, re.I)
        vr_m = re.search(r"- \*\*Video Timestamp Range\*\*:\s*(.+)", text)
        ytid = ytid_m.group(1) if ytid_m else None
        if ytid and vr_m:
            end = _range_end_seconds(vr_m.group(1))
            dur = yt.get(ytid)
            if dur is not None and end is not None and end > dur:
                findings.append(
                    Finding(
                        "P0",
                        "META_RANGE_LIE",
                        ep,
                        None,
                        f"range end {end}s exceeds YT duration {dur}s for {ytid}",
                    )
                )

        if ep == 8 and re.search(r"- \*\*Source\*\*:\s*Unknown\b", text, re.I):
            findings.append(Finding("P1", "META_SOURCE_ODD", ep, None, "Source Unknown"))

        reg_ids = {f"N-{m.group(1)}" for m in NODE_HEADER.finditer(text)}
        ledger: set[str] = set()
        new_line = re.search(r"New Nodes Introduced:\s*(.+)$", text, re.MULTILINE)
        reused_line = re.search(r"Reused Nodes Appearing:\s*(.+)$", text, re.MULTILINE)
        for line in (new_line, reused_line):
            if line:
                ledger.update(x.strip() for x in line.group(1).split(",") if x.strip())
        if new_line:
            for nid in [x.strip() for x in new_line.group(1).split(",") if x.strip()]:
                fep = first_intro.get(nid, ep)
                if fep < ep:
                    findings.append(
                        Finding("P0", "FALSE_NEW", ep, nid, f"listed New in ep{ep} but first in ep{fep}")
                    )
                elif fep > ep:
                    findings.append(
                        Finding("P1", "LEDGER_NODE_MISS", ep, nid, f"first ep{fep} missing from New")
                    )
        for nid in reg_ids - ledger:
            findings.append(
                Finding("P1", "NODE_NOT_IN_LEDGER", ep, nid, "register row not on New/Reused ledger")
            )

        tx = _transcript_for_ep(ep)
        headers = list(NODE_HEADER.finditer(text))
        for i, hm in enumerate(headers):
            nid = f"N-{hm.group(1)}"
            start = hm.start()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            block = text[start:end]
            nt_m = NODE_TYPE.search(block)
            if not nt_m:
                continue
            nt = nt_m.group(1).strip().lower()
            if nt not in TOPIC_ORG_TYPES:
                continue
            name = hm.group(2).strip()
            if not tx:
                continue
            hits = 0
            for tok in _airtime_tokens(name):
                if re.search(re.escape(tok), tx, re.IGNORECASE):
                    hits += 1
                    break
            if hits and not _wired_on_claim_or_artifact(text, nid):
                findings.append(
                    Finding(
                        "P1",
                        "ORPHAN_ORGPLACE_AIRTIME",
                        ep,
                        nid,
                        f"{name} never on Claim/Artifact Related",
                    )
                )

        ins_path = INS / f"episode_{ep:03d}.json"
        if ins_path.is_file() and ytid:
            meta = json.loads(ins_path.read_text(encoding="utf-8")).get("meta", {})
            end = _range_end_seconds(str(meta.get("video_timestamp_range") or ""))
            dur = yt.get(str(meta.get("youtube_id") or ytid))
            if dur is not None and end is not None and end > dur:
                findings.append(
                    Finding(
                        "P0",
                        "META_RANGE_LIE",
                        ep,
                        None,
                        f"inscription meta end {end}s > {dur}s",
                    )
                )

    for p in sorted(CORR.glob("episode_*.txt")):
        ep = int(re.search(r"episode_(\d+)", p.name).group(1))
        body = p.read_text(encoding="utf-8")
        for rx in AD_PATTERNS:
            if rx.search(body):
                findings.append(
                    Finding("P1", "AD_LEFT_IN_CORRECTED_TX", ep, None, f"pattern {rx.pattern}")
                )
                break

    draft_names: dict[int, str] = {}
    for ep in range(1, 11):
        t = (DRAFTS / f"episode_{ep:03d}.md").read_text(encoding="utf-8")
        m = re.search(r"^\*\*N-2\*\*\s+(.+)$", t, re.MULTILINE)
        if m:
            draft_names[ep] = m.group(1).strip()
    if CANON.is_file():
        canon_name = json.loads(CANON.read_text(encoding="utf-8"))["nodes"]["N-2"]["canonical_name"]
        variants = set(draft_names.values())
        if len(variants) > 1 or (variants and canon_name not in variants):
            findings.append(
                Finding(
                    "P0",
                    "remap_sync",
                    None,
                    "N-2",
                    f"variants={sorted(variants)!r} canonical={canon_name!r}",
                )
            )
        for ep, ins_path in ((e, INS / f"episode_{e:03d}.json") for e in range(1, 11)):
            if not ins_path.is_file():
                continue
            nodes = json.loads(ins_path.read_text(encoding="utf-8")).get("nodes") or []
            for node in nodes:
                if node.get("ref") == "N-2" or node.get("@id") == "N-2":
                    iname = (node.get("name") or "").strip()
                    if iname and iname != canon_name:
                        findings.append(
                            Finding(
                                "P0",
                                "remap_sync",
                                ep,
                                "N-2",
                                f"inscription name {iname!r} != canonical {canon_name!r}",
                            )
                        )

    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, help="Write full report JSON")
    args = ap.parse_args()

    findings = run_audit()
    counts = Counter(f.severity for f in findings)
    by_code = Counter(f.code for f in findings)
    hard_fail = counts.get("P0", 0) + counts.get("P1", 0) > 0
    report = {
        "audit": "hostile-hard-gates",
        "path": str(CKA),
        "verdict": "FAIL" if hard_fail else "CLEAR",
        "counts": {
            "P0": counts.get("P0", 0),
            "P1": counts.get("P1", 0),
            "P2": counts.get("P2", 0),
            "total": len(findings),
        },
        "by_code": dict(sorted(by_code.items())),
        "findings": [asdict(f) for f in findings],
    }
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "counts": report["counts"], "by_code": report["by_code"]}, indent=2))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
