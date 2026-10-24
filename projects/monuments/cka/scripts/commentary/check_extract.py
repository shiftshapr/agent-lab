"""Check out/<KID>.json against packs/<KID>/transcript.md: fields, verbatim snippets, timestamps, node ids."""
import json, re, sys
from pathlib import Path
H = Path(__file__).parent
kid = sys.argv[1]
d = json.loads((H / "out" / f"{kid}.json").read_text())
tr = (H / "packs" / kid / "transcript.md").read_text()
nodes = {l.split("\t")[0] for l in (H / "people.tsv").read_text().splitlines()[1:]}
norm = lambda s: re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.lower())).strip()
blocks = []
for m in re.finditer(r"^\[(\d+):(\d{2})(?::(\d{2}))?\]\s*(.*)$", tr, re.M):
    a, b, c, text = m.groups()
    t = int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)
    blocks.append((t, norm(text)))
full = " ".join(t for _, t in blocks)
err = []
for i, c in enumerate(d.get("claims", [])):
    for k in ("speaker", "timestamp", "claim", "snippet", "mentions", "relevance", "responds_to_host"):
        if k not in c: err.append(f"claim {i}: missing {k}")
    s = norm(c.get("snippet", ""))
    if not s or s not in full:
        err.append(f"claim {i}: snippet not verbatim in transcript: {c.get('snippet','')[:60]}"); continue
    if not 8 <= len(c["snippet"].split()) <= 40: err.append(f"claim {i}: snippet must be 8-40 words")
    if c.get("relevance") not in ("core", "context", "tangential"): err.append(f"claim {i}: bad relevance")
    for n in c.get("mentions", []) + ([c["speaker_node"]] if c.get("speaker_node") else []):
        if n not in nodes: err.append(f"claim {i}: unknown node {n}")
    m = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})", c.get("timestamp", ""))
    if not m: err.append(f"claim {i}: timestamp must be HH:MM:SS"); continue
    ts = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
    head = s[:60]
    starts = [t for j, (t, _) in enumerate(blocks) if head in " ".join(x for _, x in blocks[j:j + 3])]
    if starts and not any(t - 30 <= ts <= t + 90 for t in starts):
        err.append(f"claim {i}: timestamp {c['timestamp']} far from where the snippet is spoken (~{starts[0]//3600:02d}:{starts[0]%3600//60:02d}:{starts[0]%60:02d})")
print(f"{kid}: {len(d.get('claims', []))} claims, {len(err)} errors")
print("\n".join(err[:60]))
sys.exit(1 if err else 0)
