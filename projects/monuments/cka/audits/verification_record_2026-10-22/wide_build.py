"""Wider-recall candidates: next-ranked facts + evidence propagated from verified near-duplicate claims."""
import json, re, math, collections, sys
sys.argv = ['match.py', '0.12', '16']
exec(open('match.py').read().split("cands = {}")[0])   # reuse claims, facts, vec, inv
ledger = {e['claim']: e for e in json.load(open('/Users/shiftshapr/agent-lab-wt-p0b/projects/monuments/cka/ledger/verification_record.json'))}
old = json.load(open('cands.json'))           # first-pass top 8 (th 0.15)
keep = set(json.load(open('keep.json')))
fid_of = {(f['sid'], re.sub(r'\s+', ' ', f['quote']).strip()): f['fid'] for f in facts}
CASE = re.compile(r"Robinson|Twiggs|Losee|roof|rifle|Mauser|towel|screwdriver|\bDNA\b|Bagley|Chief Long|\bUVU\b|Utah Valley|tent|\bshot\b|bullet|cartridge|Discord|Hull|Faumuina|Zinn|Flood|Harpole|Crofts|security|Timpanogos|hospital|Graf|preliminary hearing|Nester|Grunander|Gray|Mitchell|Dremel|scope|surveillance|Campus Drive|Hall of Flags|courtyard|drone|autopsy|medical examiner|neck|wound|first aid|ambulance|Goforth|Peterson|Ebmeyer|Tuminez|EMT|Converse|maroon|Chick-fil-A|Washington County|St\. George|Brooksby|Davis|Bakker|Oliver|Karner|Noble|Challenger|Fugal|Sorensen", re.I)
OPINION = re.compile(r"^The host (?:argues|believes|thinks|speculates|suspects|wonders|asks|suggests|feels|predicts|hopes|urges|encourages|questions whether|calls on|invites|thanks|jokes|promises|vows|plans)", re.I)
# fact vectors by fid; claim vectors
fv = {f['fid']: f for f in facts}
cvec = {cid: vec(c['toks']) for cid, c in claims.items()}
cinv = collections.defaultdict(list)
for cid in ledger:
    for w, x in cvec[cid].items(): cinv[w].append((cid, x))
items = {}
for cid, c in claims.items():
    if cid in ledger or OPINION.search(c['text']): continue
    v = cvec[cid]
    if not (cid in keep or CASE.search(c['text'])): continue
    # facts ranks
    sc = collections.defaultdict(float)
    for w, x in v.items():
        for i, y in inv.get(w, ()): sc[i] += x * y
    ranked = [facts[i]['fid'] for s, i in sorted(((s, i) for i, s in sc.items() if s >= 0.12), reverse=True)[:16]]
    # verified neighbours
    ns = collections.defaultdict(float)
    for w, x in v.items():
        for o, y in cinv.get(w, ()): ns[o] += x * y
    prop = []
    for s, o in sorted(((s, o) for o, s in ns.items() if s >= 0.3), reverse=True)[:3]:
        for e in ledger[o]['evidence']:
            fid = fid_of.get((e['sid'], e['quote']))
            if fid and fid not in prop: prop.append(fid)
    seen = [f for s, f in old.get(cid, [])]
    new = [f for f in prop + ranked if f not in seen]
    if not new or (not prop and cid not in keep and not ranked): continue
    allf = list(dict.fromkeys(prop + seen + ranked))[:20]
    items[cid] = {'facts': allf, 'prop': bool(prop)}
print(len(items), 'claims;', sum(v['prop'] for v in items.values()), 'with propagated evidence;', sum(len(v['facts']) for v in items.values()), 'pairs')
json.dump(items, open('w2/items.json', 'w'))
