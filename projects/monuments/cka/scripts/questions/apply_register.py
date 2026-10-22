#!/usr/bin/env python3
"""Open-questions register (ROADMAP 4.3).

`ledger/open_questions.json` is the master: one entry per question (Q-1..Q-n, dense), with its topic, the question,
what is known (citing S- and C-ids), what would settle it, a status (`open`, `partly-answered`, `answered`), the
evidence ids, the claims that raise it and the claims that ask for or relay tips on it. This script:
- syncs each claim's `Open Questions:` line in the episode JSON (after `Investigative Direction`) and the
  inscription's `open_questions` from the register;
- fills `first_raised` / `last_raised` (episode dates) on each question;
- renders `ledger/open_questions.md` by topic;
- reports core claims with no question (exit 1 with --strict).

`--add FILE` merges a JSON list into the master before syncing. Each entry is either a new question
(`{"question": ..., "topic": ..., "known": ..., "settle": ..., "status": ..., "evidence": [...], "claims": [...],
"tips": [...]}`, given the next Q-id) or a mapping of a claim to existing questions (`{"claim": "C-…",
"questions": ["Q-…"]}`); the daily pipeline uses the second form for new core claims.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/questions/apply_register.py [--add FILE] [--strict]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CKA / "scripts" / "source"))
import cka_source as cs  # noqa: E402

LEDGER = CKA / "ledger" / "open_questions.json"
STATUS = ("open", "partly-answered", "answered")
KEY = "Open Questions"


def num(x: str) -> int:
    return int(x.split("-")[1])


def set_oq(item: dict, value: str | None) -> bool:
    lines = item["lines"]
    idx = next((i for i, e in enumerate(lines) if e.get("k") == KEY), None)
    if value is None:
        if idx is None:
            return False
        del lines[idx]
        return True
    if idx is not None:
        if lines[idx]["v"] == value:
            return False
        lines[idx]["v"] = value
        return True
    pos = next((i + 1 for i, e in enumerate(lines) if e.get("k") == "Investigative Direction"), len(lines))
    lines.insert(pos, {"k": KEY, "v": value})
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--add", type=Path)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    reg = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
    by_id = {q["id"]: q for q in reg}
    if a.add:
        for e in json.loads(a.add.read_text(encoding="utf-8")):
            if "claim" in e:
                for qid in e["questions"]:
                    if qid not in by_id:
                        sys.exit(f"unknown question {qid} for {e['claim']}")
                    by_id[qid]["claims"] = sorted(set(by_id[qid]["claims"]) | {e["claim"]}, key=num)
            else:
                q = {"id": f"Q-{len(reg) + 1}", **{k: e.get(k, [] if k in ("evidence", "claims", "tips") else "")
                                                   for k in ("topic", "question", "known", "settle", "status",
                                                             "evidence", "claims", "tips")}}
                reg.append(q)
                by_id[q["id"]] = q
    errs = []
    if [q["id"] for q in reg] != [f"Q-{i}" for i in range(1, len(reg) + 1)]:
        errs.append("question ids are not dense Q-1..Q-n in order")
    for q in reg:
        if q["status"] not in STATUS:
            errs.append(f"{q['id']}: bad status {q['status']!r}")
        if not q["claims"]:
            errs.append(f"{q['id']}: no claims")
        if q["status"] != "open" and not any(x.startswith("S-") for x in q["evidence"]):
            errs.append(f"{q['id']}: {q['status']} without an S-id")
    if errs:
        sys.exit("\n".join(errs))
    of_claim = defaultdict(list)
    for q in reg:
        for c in q["claims"]:
            of_claim[c].append(q["id"])
    man = {e["seq"]: e for e in json.loads((CKA / "input" / "episode_manifest.json").read_text(encoding="utf-8"))["episodes"]}
    date, core_missing, seen, dirty = {}, [], set(), 0
    for seq in sorted(man):
        if not cs.src_path(seq).exists():
            continue
        doc = cs.load(seq)
        changed = False
        for it in cs.items(doc, "claim"):
            cid = it["id"]
            seen.add(cid)
            date[cid] = man[seq]["upload_date"]
            qs = sorted(set(of_claim.get(cid, [])), key=num)
            changed |= set_oq(it, ", ".join(qs) if qs else None)
            if not qs and "relevance:core" in (cs.field(it, "Tags") or ""):
                core_missing.append(cid)
        if changed:
            cs.save(doc)
            dirty += 1
        ip = CKA / "inscription" / f"episode_{seq:03d}.json"
        if ip.exists():
            raw = ip.read_text(encoding="utf-8")
            data = json.loads(raw)
            ch = False
            for c in data.get("claims", []):
                qs = sorted(set(of_claim.get(c.get("@id"), [])), key=num)
                if c.get("open_questions", []) != qs:
                    if qs:
                        c["open_questions"] = qs
                    else:
                        c.pop("open_questions", None)
                    ch = True
            if ch:
                ip.write_text(json.dumps(data, indent=2, ensure_ascii="\\u" in raw) + "\n", encoding="utf-8")
    unknown = sorted(set(of_claim) - seen, key=num)
    if unknown:
        sys.exit(f"register claims not in the archive: {', '.join(unknown[:10])}")
    for q in reg:
        ds = sorted(date[c] for c in q["claims"])
        q["first_raised"], q["last_raised"] = ds[0], ds[-1]
    LEDGER.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = defaultdict(int)
    for q in reg:
        counts[q["status"]] += 1
    topics = defaultdict(list)
    for q in reg:
        topics[q["topic"]].append(q)
    md = ["# Open questions (ROADMAP 4.3)", "",
          f"{len(reg)} questions raised by the archive's core claims: "
          + ", ".join(f"{counts[s]} {s}" for s in STATUS)
          + ". Each lists what is known (S-ids are records, C-ids are claims; the host's claims are not evidence), "
          "what would settle it, and the claims that raise it. Generated by `scripts/questions/apply_register.py` "
          "from `open_questions.json`.", ""]
    for t in sorted(topics, key=lambda t: (-sum(len(q["claims"]) for q in topics[t]), t)):
        md += [f"## {t}", ""]
        for q in sorted(topics[t], key=lambda q: -len(q["claims"])):
            cl = q["claims"]
            md += [f"### {q['id']} · {q['status']} · {len(cl)} claims ({q['first_raised']} to {q['last_raised']})",
                   f"**{q['question']}**", f"- **Known:** {q['known']}", f"- **Would settle it:** {q['settle']}",
                   f"- **Claims:** {', '.join(cl[:12])}{' …' if len(cl) > 12 else ''}"]
            if q["tips"]:
                md.append(f"- **Tips:** {', '.join(q['tips'])}")
            md.append("")
    (CKA / "ledger" / "open_questions.md").write_text("\n".join(md), encoding="utf-8")
    print(f"questions: {len(reg)} ({dict(counts)}); claims linked: {len(of_claim)}; episodes rewritten: {dirty}; "
          f"core claims without a question: {len(core_missing)}")
    if core_missing:
        print("  e.g. " + ", ".join(core_missing[:10]))
        if a.strict:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
