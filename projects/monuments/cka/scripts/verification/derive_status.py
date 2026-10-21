#!/usr/bin/env python3
"""Verification status (POLICY 11, ROADMAP 4.4): derive `revised-by-host` and sync statuses into the inscriptions.

- A claim that a later host claim `Revises`, or contradicts host-against-herself, gets
  `Verification: revised-by-host` with `Verification Evidence:` citing the later claim(s). Statuses set from records
  (`corroborated`, `disputed`, `contradicted-by-record`) are never overridden. A derived status whose link has gone
  is removed.
- Every claim's status and evidence are copied into its inscription (`verification_status`,
  `verification_evidence`); claims with no status are `unverified`.
Edits go through the JSON source. Idempotent; part of the daily finalize step.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/verification/derive_status.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CKA / "scripts" / "source"))
import cka_source as cs  # noqa: E402

OTHER_VOICE = re.compile(r"\b(?:clip|reads|per the|according to|quotes?|comment|post|article|document|email|text message|tweet)\b", re.I)
RECORD = {"corroborated", "disputed", "contradicted-by-record"}


def host(text: str) -> bool:
    return text.startswith("The host ") and not OTHER_VOICE.search(text)


def set_line(item: dict, key: str, value: str | None) -> bool:
    lines = item["lines"]
    idx = next((i for i, e in enumerate(lines) if e.get("k") == key), None)
    if value is None:
        if idx is not None:
            del lines[idx]
            return True
        return False
    if idx is not None:
        if lines[idx]["v"] == value:
            return False
        lines[idx]["v"] = value
        return True
    pos = next((i for i, e in enumerate(lines) if e.get("k") == "Investigative Direction"), len(lines))
    if key == "Verification Evidence":
        pos = next((i + 1 for i, e in enumerate(lines) if e.get("k") == "Verification"), pos)
    lines.insert(pos, {"k": key, "v": value})
    return True


def main() -> int:
    seqs = sorted(int(p.stem.split("_")[1]) for p in cs.SRC.glob("episode_*.json") if p.stem != "episode_000")
    docs = {s: cs.load(s) for s in seqs}
    text, where = {}, {}
    for s, d in docs.items():
        for it in cs.items(d, "claim"):
            text[it["id"]] = cs.field(it, "Claim") or ""
            where[it["id"]] = (s, it)
    revisers: dict[str, list[str]] = defaultdict(list)
    for cid, (s, it) in where.items():
        if not host(text[cid]):
            continue
        for key in ("Revises", "Contradicts"):
            for old in re.findall(r"C-\d+", cs.field(it, key) or ""):
                if old in where and host(text[old]):
                    revisers[old].append(cid)
    dirty, counts = set(), defaultdict(int)
    for cid, (s, it) in where.items():
        cur = cs.field(it, "Verification")
        if cur in RECORD:
            counts[cur] += 1
            continue
        if cid in revisers:
            ch = set_line(it, "Verification", "revised-by-host") | set_line(it, "Verification Evidence", ", ".join(sorted(set(revisers[cid]))))
        elif cur == "revised-by-host":
            ch = set_line(it, "Verification", None) | set_line(it, "Verification Evidence", None)
        else:
            ch = False
        if ch:
            dirty.add(s)
        counts[cs.field(it, "Verification") or "unverified"] += 1
    for s in sorted(dirty):
        cs.save(docs[s])
    for s, d in docs.items():
        ip = CKA / "inscription" / f"episode_{s:03d}.json"
        if not ip.exists():
            continue
        raw = ip.read_text(encoding="utf-8")
        data = json.loads(raw)
        by_id = {it["id"]: it for it in cs.items(d, "claim")}
        changed = False
        for c in data.get("claims", []):
            it = by_id.get(c.get("@id"))
            if not it:
                continue
            st = cs.field(it, "Verification") or "unverified"
            ev = [x.strip() for x in (cs.field(it, "Verification Evidence") or "").split(",") if x.strip()]
            if c.get("verification_status") != st or c.get("verification_evidence", []) != ev:
                c["verification_status"], c["verification_evidence"] = st, ev
                changed = True
        if changed:
            ip.write_text(json.dumps(data, indent=2, ensure_ascii="\\u" in raw) + "\n", encoding="utf-8")
    print("verification:", dict(sorted(counts.items())), f"(episodes rewritten: {len(dirty)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
