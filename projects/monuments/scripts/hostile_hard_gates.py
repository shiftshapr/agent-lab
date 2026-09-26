#!/usr/bin/env python3
"""
Monument hostile hard-gates (Transit / Bill D spirit).

Exit 0 when P0=0 and P1=0. P2 findings are reported but do not fail the run.

Usage (from agent-lab root):
  python3 projects/monuments/scripts/hostile_hard_gates.py --monument cka
  python3 projects/monuments/scripts/hostile_hard_gates.py --monument cka --json /tmp/hostile.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MONUMENTS = REPO / "projects" / "monuments"

CLAIM_RANGE_RE = re.compile(r"Claim Range:\s*C-(\d+)-C-(\d+)", re.I)
CLAIM_HEADER_RE = re.compile(r"^\*\*C-(\d+)\*\*", re.MULTILINE)


@dataclass
class Finding:
    severity: str
    code: str
    episode: int | None
    id: str | None
    detail: str


def _load_cka_audit_module():
    path = MONUMENTS / "cka" / "scripts" / "hostile_hard_gates_audit.py"
    spec = importlib.util.spec_from_file_location("cka_hostile_audit", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _claim_first_intro(drafts_dir: Path) -> dict[int, int]:
    first: dict[int, int] = {}
    for path in sorted(drafts_dir.glob("episode_*.md")):
        m = re.search(r"episode_(\d+)", path.name)
        if not m:
            continue
        ep = int(m.group(1))
        if ep == 0:
            continue
        text = path.read_text(encoding="utf-8")
        for hm in CLAIM_HEADER_RE.finditer(text):
            cid = int(hm.group(1))
            first.setdefault(cid, ep)
    return first


def _ledger_claim_extra(drafts_dir: Path, first: dict[int, int]) -> list[Finding]:
    out: list[Finding] = []
    for path in sorted(drafts_dir.glob("episode_*.md")):
        m = re.search(r"episode_(\d+)", path.name)
        if not m:
            continue
        ep = int(m.group(1))
        if ep == 0:
            continue
        text = path.read_text(encoding="utf-8")
        rm = CLAIM_RANGE_RE.search(text)
        if not rm:
            continue
        lo, hi = int(rm.group(1)), int(rm.group(2))
        for cid in range(lo, hi + 1):
            fep = first.get(cid)
            if fep is not None and fep < ep:
                out.append(
                    Finding(
                        "P1",
                        "LEDGER_CLAIM_EXTRA",
                        ep,
                        f"C-{cid}",
                        f"Claim Range includes C-{cid} but first-defined ep{fep}",
                    )
                )
    return out


def _p2_findings(monument_dir: Path) -> list[Finding]:
    out: list[Finding] = []
    drafts = monument_dir / "drafts"
    # ORPHAN_NODE N-1193 — place with register but no Related on claim/artifact
    ep9 = drafts / "episode_009.md"
    if ep9.is_file():
        t = ep9.read_text(encoding="utf-8")
        if "**N-1193**" in t and not re.search(
            r"^Related Nodes:.*\bN-1193\b", t, re.MULTILINE | re.IGNORECASE
        ):
            pre = t.split("## 4. Node Register")[0]
            if not re.search(r"^\*Related:.*\bN-1193\b", pre, re.MULTILINE):
                out.append(
                    Finding("P2", "ORPHAN_NODE", 9, "N-1193", "Poland not on Claim/Artifact Related")
                )

    canon_nodes = monument_dir / "canonical" / "nodes.json"
    if canon_nodes.is_file():
        nodes = json.loads(canon_nodes.read_text(encoding="utf-8")).get("nodes", {})
        n59 = nodes.get("N-59", {}).get("canonical_name", "")
        n100 = nodes.get("N-100", {}).get("canonical_name", "")
        if "husband" in n59.lower() and "husband" in n100.lower():
            out.append(
                Finding(
                    "P2",
                    "HUSBAND_DUPLICATE_SMELL",
                    None,
                    "N-59/N-100",
                    f'N-59="{n59}" N-100="{n100}"',
                )
            )

    memes_canon = monument_dir / "canonical" / "memes.json"
    if memes_canon.is_file():
        canon_ids = set(json.loads(memes_canon.read_text()).get("memes", {}).keys())
        draft_memes: set[str] = set()
        for p in drafts.glob("episode_*.md"):
            if "episode_000" in p.name:
                continue
            draft_memes.update(re.findall(r"\*\*M-(\d+)\*\*", p.read_text(encoding="utf-8")))
        draft_ids = {f"M-{x}" for x in draft_memes}
        extra = sorted(canon_ids - draft_ids)
        if extra:
            out.append(
                Finding(
                    "P2",
                    "MEME_CANON_ONLY_CARRYOVER",
                    None,
                    None,
                    f"Canonical memes not in CKA drafts: {extra}",
                )
            )

    out.append(
        Finding(
            "P2",
            "CA_DEBT_CALLOUT",
            None,
            None,
            "C/A numbering continues BoC remap bands; leading holes expected in Batch 1.",
        )
    )
    return out


def run(monument: str) -> tuple[list[Finding], dict]:
    monument_dir = MONUMENTS / monument
    if not monument_dir.is_dir():
        raise SystemExit(f"Unknown monument: {monument}")

    findings: list[Finding] = []
    if monument == "cka":
        mod = _load_cka_audit_module()
        findings.extend(mod.run_audit())
        first = _claim_first_intro(monument_dir / "drafts")
        findings.extend(_ledger_claim_extra(monument_dir / "drafts", first))
    else:
        raise SystemExit(f"hostile_hard_gates: monument {monument!r} not implemented")

    findings.extend(_p2_findings(monument_dir))
    counts = Counter(f.severity for f in findings)
    by_code = Counter(f.code for f in findings)
    meta = {
        "audit": "hostile-hard-gates",
        "monument": monument,
        "path": str(monument_dir),
        "verdict": "FAIL" if counts.get("P0", 0) + counts.get("P1", 0) else "CLEAR",
        "counts": {
            "P0": counts.get("P0", 0),
            "P1": counts.get("P1", 0),
            "P2": counts.get("P2", 0),
            "total": len(findings),
        },
        "by_code": dict(sorted(by_code.items())),
    }
    return findings, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--monument", required=True, help="e.g. cka")
    ap.add_argument("--json", type=Path, help="Write report JSON")
    args = ap.parse_args()

    findings, meta = run(args.monument)
    report = {**meta, "findings": [asdict(f) for f in findings]}
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": meta["verdict"], "counts": meta["counts"], "by_code": meta["by_code"]}, indent=2))
    hard_fail = meta["counts"]["P0"] + meta["counts"]["P1"] > 0
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
