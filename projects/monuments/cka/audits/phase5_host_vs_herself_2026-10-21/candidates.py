import sys, re, json, math, collections
sys.path.insert(0, '/Users/shiftshapr/agent-lab-wt-p0b/projects/monuments/cka/scripts/source')
import cka_source as cs
CKA = '/Users/shiftshapr/agent-lab-wt-p0b/projects/monuments/cka'
OUT = '/private/tmp/claude-501/-Users-shiftshapr/bbe5566f-7989-480f-a459-5df127d949ba/scratchpad/p5'
TH = float(sys.argv[1]) if len(sys.argv) > 1 else 0.4
TOPK = int(sys.argv[2]) if len(sys.argv) > 2 else 2
man = {e['seq']: e for e in json.load(open(CKA + '/input/episode_manifest.json'))['episodes']}
BROAD = {'N-1', 'N-2', 'N-3', 'N-10000'}
STOP = set('the a an and or of to in on for at by with from that this is was were be been are as it its his her she he they them their host says said say saying alleges claims claim according per which who whom what when where why how not no but if then than so also about into over after before during more most some any all one two'.split())
cue = re.compile(r"\b(misspoke|was wrong|were wrong|mistaken|correct(?:s|ed|ion)?|walk(?:s|ed)? back|retract|clarif(?:y|ies|ied|ication)|earlier (?:she|episode)|previously|update[sd]?|no longer|turns out|actually|now says|changed)\b", re.I)
claims = []
for seq in sorted(man):
    try: d = cs.load(seq)
    except FileNotFoundError: continue
    for it in cs.items(d, 'claim'):
        txt = cs.field(it, 'Claim') or ''
        if not txt.startswith('The host '): continue
        nodes = set(re.findall(r'N-\d+', (cs.field(it, 'Mentions') or '') + ' ' + (cs.field(it, 'Related Nodes') or ''))) - BROAD
        toks = [w for w in re.findall(r"[a-z0-9']+", txt.lower()) if w not in STOP and len(w) > 2]
        claims.append({'id': it['id'], 'ep': seq, 'date': man[seq]['upload_date'], 'yt': man[seq]['youtube_id'],
                       'ts': cs.field(it, 'Claim Timestamp'), 'text': txt, 'nodes': nodes, 'toks': toks,
                       'existing': {k: cs.field(it, k) for k in ('Supports', 'Revises', 'Contradicts', 'Qualifies') if cs.field(it, k)},
                       'cue': bool(cue.search(txt))})
N = len(claims); df = collections.Counter()
for c in claims: df.update(set(c['toks']))
idf = {w: math.log(N / (1 + n)) for w, n in df.items()}
for c in claims:
    tf = collections.Counter(c['toks'])
    v = {w: tf[w] * idf[w] for w in tf}
    nrm = math.sqrt(sum(x * x for x in v.values())) or 1
    c['vec'] = {w: x / nrm for w, x in v.items()}
by_node = collections.defaultdict(list)
for i, c in enumerate(claims):
    for n in c['nodes']: by_node[n].append(i)
pairs = {}
for i, c in enumerate(claims):
    cand = set()
    for n in c['nodes']:
        cand.update(j for j in by_node[n] if claims[j]['ep'] < c['ep'])
    scored = []
    for j in cand:
        o = claims[j]; s = sum(x * o['vec'].get(w, 0) for w, x in c['vec'].items())
        scored.append((s, j))
    scored.sort(reverse=True)
    th = TH * 0.7 if c['cue'] else TH
    k = TOPK + 3 if c['cue'] else TOPK
    for s, j in scored[:k]:
        if s >= th: pairs[(i, j)] = round(s, 3)
print(f'host claims {N}; candidate pairs {len(pairs)} (th {TH}, top {TOPK}); cue-driven {sum(1 for (i,j) in pairs if claims[i]["cue"])}')
out = [{'later': claims[i]['id'], 'earlier': claims[j]['id'], 'score': s} for (i, j), s in sorted(pairs.items(), key=lambda kv: -kv[1])]
json.dump(out, open(OUT + '/pairs.json', 'w'))
json.dump({c['id']: {k: c[k] for k in ('ep', 'date', 'yt', 'ts', 'text', 'existing')} for c in claims}, open(OUT + '/claims.json', 'w'))
