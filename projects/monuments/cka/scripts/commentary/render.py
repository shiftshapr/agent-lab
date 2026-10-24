#!/usr/bin/env python3
"""Render commentary/claims.md from commentary/{episodes,claims,links}.json (ROADMAP 4.1b): every claim by video, with
its timestamped link and its links to host claims underneath."""
import collections
import json
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CKA / "scripts" / "source"))
import cka_source as cs  # noqa: E402

D = CKA / "commentary"
eps = json.loads((D / "episodes.json").read_text())["episodes"]
claims = json.loads((D / "claims.json").read_text())
links = json.loads((D / "links.json").read_text())
man = {e["seq"]: e for e in json.loads((CKA / "input" / "episode_manifest.json").read_text())["episodes"]}
need = {l["c"] for l in links}
host = {}
for seq in sorted(man):
    if not cs.src_path(seq).exists():
        continue
    for it in cs.items(cs.load(seq), "claim"):
        if it["id"] in need:
            m = re.match(r"(\d+):(\d+):(\d+)", cs.field(it, "Claim Timestamp") or "") or re.match(r"()(\d+):(\d+)", cs.field(it, "Claim Timestamp") or "0:0")
            s = int(m[1] or 0) * 3600 + int(m[2]) * 60 + int(m[3])
            host[it["id"]] = {"date": man[seq]["upload_date"], "text": cs.field(it, "Claim"),
                              "url": f"https://www.youtube.com/watch?v={man[seq]['youtube_id']}&t={s}s"}
L = collections.defaultdict(list)
for l in links:
    L[l["cc"]].append(l)
REL = {"contradicts": "✗ contradicts", "supports": "✓ supports", "qualifies": "≈ qualifies"}
rc = collections.Counter(l["relation"] for l in links)
groups = list(dict.fromkeys(e["group"] for e in eps))
hours = sum(e["duration_min"] for e in eps) / 60
md = ["# Commentator claims (ROADMAP 4.1b)", "",
      f"**{len(claims)} claims** from {len(eps)} videos ({hours:.0f} hours) by commentators on the Charlie Kirk case, with "
      f"**{len(links)} links** to Candace Owens' archived claims: {rc['contradicts']} contradict hers, {rc['supports']} "
      f"support, {rc['qualifies']} qualify.", "",
      "- Claims are recorded **as said**, with a timestamped YouTube link and a verbatim snippet. They are never evidence: "
      "a link records that two speakers agree or disagree, not who is right (POLICY 11).",
      "- Relevance tags: core / context / tangential. ↩ marks a claim the speaker addresses to Owens.",
      "- Method and audits: `audits/commentators_2026-10-23/` (pilot) and later `audits/commentators_*` folders.", "",
      "## Contents"]
for g in groups:
    md.append(f"- **{g}**")
    for e in eps:
        if e["group"] == g:
            cs_ = [c for c in claims if c["kid"] == e["kid"]]
            md.append(f"  - [{e['kid']}](#{e['kid'].lower()}) {e['upload_date']} · {e['title'][:80]} · {len(cs_)} claims, "
                      f"{sum(len(L[c['id']]) for c in cs_)} links")
for g in groups:
    md += ["", f"# {g}"]
    for e in eps:
        if e["group"] != g:
            continue
        md += ["", f"## {e['kid']}", f"**[{e['title']}]({e['url']})** · {e['channel']} · {e['upload_date']} · "
               f"{e['duration_min']} min · scope: {e['scope']}", ""]
        for c in [c for c in claims if c["kid"] == e["kid"]]:
            flag = " ↩" if c["responds_to_host"] else ""
            md.append(f"- **{c['id']}** [{c['timestamp']}]({c['url']}) · {c['relevance']}{flag} · **{c['speaker']}**: {c['claim']}  ")
            md.append(f"  > \"{c['snippet']}\"")
            for l in L[c["id"]]:
                h = host[l["c"]]
                md.append(f"  - {REL[l['relation']]} [{l['c']}]({h['url']}) ({h['date']}): {h['text']}  ")
                md.append(f"    _{l['note']}_")
(D / "claims.md").write_text("\n".join(md) + "\n")
print(f"rendered {len(claims)} claims, {len(links)} links")
