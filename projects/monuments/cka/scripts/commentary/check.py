#!/usr/bin/env python3
"""Check the commentary series (ROADMAP 4.1b): schema of commentary/{episodes,claims,links}.json, unique CC ids, links
pointing at existing CC and host C claims, and no commentator claim used as verification evidence (POLICY 11)."""
import json, re, sys
from pathlib import Path
CKA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CKA / "scripts" / "source"))
import cka_source as cs  # noqa: E402

D = CKA / "commentary"
eps = {e["kid"]: e for e in json.loads((D / "episodes.json").read_text())["episodes"]}
claims = json.loads((D / "claims.json").read_text())
links = json.loads((D / "links.json").read_text())
err = []
ids = [c["id"] for c in claims]
if len(ids) != len(set(ids)):
    err.append("duplicate CC ids")
for c in claims:
    if not re.fullmatch(r"CC-\d+", c["id"]): err.append(f"{c['id']}: bad id")
    if c["kid"] not in eps: err.append(f"{c['id']}: unknown episode {c['kid']}")
    if c["relevance"] not in ("core", "context", "tangential"): err.append(f"{c['id']}: bad relevance")
    if not c.get("speaker") or not c.get("claim") or not c.get("snippet"): err.append(f"{c['id']}: missing speaker, claim or snippet")
    if not 8 <= len(c["snippet"].split()) <= 40: err.append(f"{c['id']}: snippet must be 8-40 words")
    if not re.fullmatch(r"\d{2}:\d{2}:\d{2}", c["timestamp"]): err.append(f"{c['id']}: bad timestamp")
host = set()
for seq in range(0, 1000):
    if cs.src_path(seq).exists():
        host |= {it["id"] for it in cs.items(cs.load(seq), "claim")}
cc = set(ids)
for l in links:
    if l["cc"] not in cc: err.append(f"link {l['cc']}->{l['c']}: unknown CC")
    if l["c"] not in host: err.append(f"link {l['cc']}->{l['c']}: unknown host claim")
    if l["relation"] not in ("supports", "contradicts", "qualifies"): err.append(f"link {l['cc']}->{l['c']}: bad relation")
rec = CKA / "ledger" / "verification_record.json"
if rec.exists() and "CC-" in rec.read_text():
    err.append("verification_record cites a commentator claim (POLICY 11: commentators are never evidence)")
print(f"commentary check: {len(eps)} episodes, {len(claims)} claims, {len(links)} links, {len(err)} problems")
for e in err[:40]:
    print("  -", e)
sys.exit(1 if err else 0)
