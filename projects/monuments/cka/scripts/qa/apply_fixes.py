#!/usr/bin/env python3
"""Apply verification-pass fixes to drafts and inscriptions.

Sources, in order of precedence for a claim:
  1. CONFIRM_DIR/confirmed_*.json: Opus decisions on material findings and name fixes (accept / amend / reject).
  2. VERIFY_DIR/results_*.json: first-pass fixes for claims that are minor only (not material). These are applied
     only if they keep every number, capitalised word and quoted phrase of the original claim, and only the fields
     claim, label and relevance (never mentions or timestamps without confirmation).

Fields: claim, label, timestamp, mentions, relevance. Name fixes are not applied here; they are written to
OUT_NAMES (JSON) for review and then added to config/transcript_name_corrections.json.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/qa/apply_fixes.py VERIFY_DIR CONFIRM_DIR OUT_LOG OUT_NAMES [--dry-run]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "source"))
import cka_source as cs  # noqa: E402  (ROADMAP 3.0: episodes are read and written through the JSON source)

CKA = Path(__file__).resolve().parents[2]
STOP = {"The", "A", "An", "In", "On", "At", "Per", "After", "Before", "During", "This", "That", "It", "He", "She",
        "They", "His", "Her", "Their", "As", "By", "For", "From", "With", "According", "Host", "Says"}


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", t.replace("’", "'").replace("“", '"').replace("”", '"')).lower()


def lost_content(old: str, new: str) -> list[str]:
    n = norm(new)
    nums = {x.rstrip(".,") for x in re.findall(r"\d[\d,.:]*", old)}
    caps = {re.sub(r"'s$", "", w.rstrip(".,;:")) for w in re.findall(r"\b[A-Z][\w'’.-]+", old) if w not in STOP}
    quotes = {norm(q).rstrip(".,") for q in re.findall(r'["“]([^"”]{4,})["”]', old)}
    return sorted({x for x in nums | caps | quotes if x and norm(x) not in n})


def set_line(block: str, label: str, value: str, after: str = "Claim") -> str:
    if re.search(rf"^{label}:", block, re.M):
        return re.sub(rf"^{label}:.*$", lambda _: f"{label}: {value}", block, count=1, flags=re.M)
    return re.sub(rf"^({after}:.*\n)", lambda m: m.group(1) + f"{label}: {value}\n", block, count=1, flags=re.M)


def main() -> int:
    verify, confirm, out_log, out_names = (Path(a) for a in sys.argv[1:5])
    dry = "--dry-run" in sys.argv
    results = {r["claim"]: r for p in sorted(verify.glob("results_*.json")) for r in json.loads(p.read_text())}
    decided = {d["claim"]: d for p in sorted(confirm.glob("confirmed_*.json")) for d in json.loads(p.read_text())}
    fixes, names, skipped = {}, [], []
    for cid, r in results.items():
        if cid in decided:
            d = decided[cid]
            if d.get("decision") in ("accept", "amend") and d.get("fix"):
                fixes[cid] = (int(r["episode"]), d["fix"], "confirmed")
        elif not r.get("material") and r.get("fix"):
            f = {k: v for k, v in r["fix"].items() if k in ("claim", "label", "relevance")}
            if f:
                fixes[cid] = (int(r["episode"]), f, "minor")
    by_ep: dict[int, list] = {}
    for cid, (ep, f, kind) in fixes.items():
        by_ep.setdefault(ep, []).append((cid, f, kind))
    log = []
    for ep, items in sorted(by_ep.items()):
        dp = CKA / "drafts" / f"episode_{ep:03d}.md"
        ip = CKA / "inscription" / f"episode_{ep:03d}.json"
        s, raw = cs.read_draft_text(ep), ip.read_text(encoding="utf-8")
        data = json.loads(raw)
        insc = {c["ref"]: c for c in data["claims"]}
        for cid, f, kind in items:
            m = re.search(rf"^\*\*{cid}\*\*.*?(?=^\*\*C-|^#{{1,3}} |\Z)", s, re.M | re.S)
            if not m or cid not in insc:
                skipped.append((cid, "not found"))
                continue
            b, c = m.group(0), insc[cid]
            old_claim = re.search(r"^Claim:\s*(.+)$", b, re.M).group(1).strip()
            if kind == "minor" and f.get("claim") and lost_content(old_claim, f["claim"]):
                skipped.append((cid, f"minor fix drops {lost_content(old_claim, f['claim'])[:4]}"))
                f = {k: v for k, v in f.items() if k != "claim"}
            changed = []
            if f.get("claim"):
                b = set_line(b, "Claim", f["claim"]); c["claim"] = f["claim"]; changed.append("claim")
            if f.get("label"):
                b = re.sub(rf"^\*\*{cid}\*\* .*$", lambda _: f"**{cid}** {f['label']}", b, count=1, flags=re.M)
                c["label"] = f["label"]; changed.append("label")
            if f.get("timestamp") and re.fullmatch(r"\d{2}:\d{2}:\d{2}", f["timestamp"]):
                b = set_line(b, "Claim Timestamp", f["timestamp"]); c["claim_timestamp"] = f["timestamp"]
                changed.append("timestamp")
            if isinstance(f.get("mentions"), list):
                ids = [x for x in f["mentions"] if re.fullmatch(r"N-\d+", x)]
                b = set_line(b, "Mentions", ", ".join(ids), after="Anchored Artifacts" if "Anchored Artifacts:" in b
                             else "Transcript Snippet" if "Transcript Snippet:" in b else "Claim")
                if ids:
                    c["mentions_person_refs"] = ids
                else:
                    c.pop("mentions_person_refs", None)
                changed.append("mentions")
            if f.get("relevance") in ("core", "context", "tangential"):
                tm = re.search(r"^Tags:\s*(.*)$", b, re.M)
                tags = [t.strip() for t in tm.group(1).split(",") if t.strip()] if tm else []
                tags = [t for t in tags if not t.startswith("relevance:")] + [f"relevance:{f['relevance']}"]
                b = set_line(b, "Tags", ", ".join(tags), after="Investigative Direction"
                             if "Investigative Direction:" in b else "Claim")
                c["tags"] = [t for t in (c.get("tags") or []) if not t.startswith("relevance:")] + [f"relevance:{f['relevance']}"]
                changed.append("relevance")
            if changed:
                s = s[:m.start()] + b + s[m.end():]
                log.append({"claim": cid, "episode": ep, "kind": kind, "fields": changed})
        if not dry:
            cs.write_draft_text(ep, s)
            ip.write_text(json.dumps(data, indent=2, ensure_ascii="\\u" in raw) + "\n", encoding="utf-8")
    for cid, d in decided.items():
        if d.get("decision") in ("accept", "amend"):
            for n in (d.get("fix") or {}).get("names", []):
                names.append({**n, "claim": cid, "episode": int(results.get(cid, {}).get("episode", 0))})
    if not dry:
        out_log.write_text(json.dumps(log, indent=1) + "\n")
        out_names.write_text(json.dumps(names, indent=1, ensure_ascii=False) + "\n")
    kinds = {}
    for x in log:
        kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
    print(f"applied {len(log)} {kinds}; name fixes {len(names)}; skipped {len(skipped)}")
    for x in skipped[:30]:
        print("  SKIP", *x)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
