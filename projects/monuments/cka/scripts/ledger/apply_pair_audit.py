#!/usr/bin/env python3
"""Apply audited verdicts to the then-vs-now links (ROADMAP 6.2). Usage: apply_pair_audit.py RESULTS.json [--dry-run]

RESULTS is a list of {"earlier", "later", "verdict", "severity", "fix", "issue"} (Phase 6 strata B1/B2). Links live on
the later claim as `Revises:` / `Contradicts:` / `Qualifies:` lines naming the earlier claim. For each pair:
- `ok`: kept; the audit note is recorded in the ledger.
- `material` with fix "drop…": the link is removed. "drop (re-file as host_vs_herself revises…)" and "revises
  (reclassify host_vs_herself…)" instead become `revises`, with both claims marked as the host's own words.
- `minor` with a relation in the fix: relabelled; "swap order" moves the link onto the other claim; "set later/earlier
  host_voice true" records an override in config/host_voice_overrides.json.
Every change is printed; then run export_then_vs_now.py and derive_status.py.
"""
import json, re, sys
from pathlib import Path
CKA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CKA / "scripts" / "source"))
import cka_source as cs  # noqa: E402

KEY = {"revises": "Revises", "contradicts": "Contradicts", "qualifies": "Qualifies"}
rows = json.loads(Path(sys.argv[1]).read_text())
dry = "--dry-run" in sys.argv
where, docs = {}, {}
for seq in range(0, 1000):
    if cs.src_path(seq).exists():
        docs[seq] = cs.load(seq)
        for it in cs.items(docs[seq], "claim"):
            where[it["id"]] = (seq, it)
ovp = CKA / "config" / "host_voice_overrides.json"
override = json.loads(ovp.read_text()) if ovp.exists() else {}
touched, notes, log = set(), {}, []


def ids(it, k):
    return re.findall(r"C-\d+", cs.field(it, k) or "")


def setids(it, k, lst):
    cs.set_field(it, k, ", ".join(sorted(set(lst), key=lambda x: int(x[2:])))) if lst else _drop(it, k)


def _drop(it, k):
    it["lines"] = [l for l in it["lines"] if l.get("k") != k]


def remove(later, earlier):
    seq, it = where[later]
    for k in KEY.values():
        if earlier in ids(it, k):
            setids(it, k, [x for x in ids(it, k) if x != earlier]); touched.add(seq); return k
    return None


def add(later, earlier, rel):
    seq, it = where[later]
    k = KEY[rel]
    if not any(l.get("k") == k for l in it["lines"]):  # insert before Confidence / Tags if present
        pos = next((i for i, l in enumerate(it["lines"]) if l.get("k") in ("Confidence", "Tags", "Verification", "Investigative Direction")), len(it["lines"]))
        it["lines"].insert(pos, {"k": k, "v": earlier})
    else:
        setids(it, k, ids(it, k) + [earlier])
    touched.add(seq)


for r in rows:
    e, l, fix = r["earlier"], r["later"], (r.get("fix") or "").lower()
    if e not in where or l not in where:
        log.append(f"skip {l}->{e}: claim missing"); continue
    if r["verdict"] == "ok":
        rel = next((x for x in KEY if fix.startswith(x)), None)
        if rel:  # ok but the auditor named the relation; make sure it is that one
            old = remove(l, e); add(l, e, rel)
            if old and old.lower() != rel: log.append(f"relabel {l}->{e}: {old} -> {rel}")
        notes[(l, e)] = "Phase 6: ok"
        continue
    if r.get("severity") == "material" and (fix.startswith("drop") and "re-file" not in fix) or fix.startswith("revises (only after"):
        k = remove(l, e); log.append(f"drop {l}->{e} ({k}): {r.get('issue','')[:120]}"); continue
    if "re-file" in fix or "reclassify host_vs_herself" in fix:
        remove(l, e); add(l, e, "revises"); override[l] = override[e] = True
        notes[(l, e)] = "Phase 6: re-filed as host-vs-herself revises"; log.append(f"refile {l}->{e} as revises"); continue
    rel = next((x for x in KEY if fix.startswith(x)), None)
    if not rel:
        log.append(f"unhandled {l}->{e}: {fix}"); continue
    remove(l, e)
    if "swap" in fix:
        add(e, l, rel); log.append(f"swap+{rel} {e}->{l}"); notes[(e, l)] = f"Phase 6: {r.get('issue','')[:160]}"
    else:
        add(l, e, rel); log.append(f"{rel} {l}->{e}"); notes[(l, e)] = f"Phase 6: {r.get('issue','')[:160]}"
    if "set later host_voice true" in fix: override[l] = True
    if "set earlier host_voice true" in fix: override[e] = True
print("\n".join(log))
print(f"{len(rows)} verdicts; {sum(x.startswith('drop') for x in log)} dropped; episodes touched {len(touched)}")
if not dry:
    for seq in touched:
        cs.save(docs[seq])
    ovp.write_text(json.dumps(dict(sorted(override.items(), key=lambda kv: int(kv[0][2:]))), indent=1) + "\n")
    (CKA / "ledger" / "then_vs_now_audit_notes.json").write_text(json.dumps(
        [{"later": a, "earlier": b, "note": n} for (a, b), n in notes.items()], indent=1, ensure_ascii=False) + "\n")
