"""TF-IDF match record facts to claims. Writes cands.json: {claim_id: [(score, fid), ...]}."""
import sys, re, json, math, collections
sys.path.insert(0, '/Users/shiftshapr/agent-lab-wt-p0b/projects/monuments/cka/scripts/source')
import cka_source as cs
CKA = '/Users/shiftshapr/agent-lab-wt-p0b/projects/monuments/cka'
TH = float(sys.argv[1]) if len(sys.argv) > 1 else 0.25
K = int(sys.argv[2]) if len(sys.argv) > 2 else 6
STOP = set('the a an and or of to in on for at by with from that this is was were be been are as it its his her she he they them their host says said say saying alleges claims claim according per which who whom what when where why how not no but if then than so also about into over after before during more most some any all one two there had has have did does would could should will just like very really know think going yes okay right well want get got charlie kirk mr ms reads clip'.split())
man = {e['seq']: e for e in json.load(open(CKA + '/input/episode_manifest.json'))['episodes']}
def toks(s): return [w for w in re.findall(r"[a-z0-9']+", s.lower()) if w not in STOP and len(w) > 2]
claims = {}
for seq in sorted(man):
    if not cs.src_path(seq).exists(): continue
    for it in cs.items(cs.load(seq), 'claim'):
        t = cs.field(it, 'Claim') or ''
        claims[it['id']] = {'ep': seq, 'date': man[seq]['upload_date'], 'text': t, 'snippet': cs.field(it, 'Transcript Snippet') or '',
                            'ts': cs.field(it, 'Claim Timestamp'), 'yt': man[seq]['youtube_id'], 'ver': cs.field(it, 'Verification'), 'toks': toks(t)}
facts = json.load(open('facts_all.json'))
for f in facts: f['toks'] = toks(f['fact'] + ' ' + f['quote'] + ' ' + ' '.join(f.get('entities', [])))
docs = [c['toks'] for c in claims.values()] + [f['toks'] for f in facts]
N = len(docs); df = collections.Counter()
for d in docs: df.update(set(d))
idf = {w: math.log(N / (1 + n)) for w, n in df.items()}
def vec(t):
    tf = collections.Counter(t); v = {w: tf[w] * idf[w] for w in tf}; nr = math.sqrt(sum(x*x for x in v.values())) or 1
    return {w: x / nr for w, x in v.items()}
inv = collections.defaultdict(list)
for i, f in enumerate(facts):
    f['vec'] = vec(f['toks'])
    for w, x in f['vec'].items(): inv[w].append((i, x))
cands = {}
for cid, c in claims.items():
    v = vec(c['toks']); sc = collections.defaultdict(float)
    for w, x in v.items():
        for i, y in inv.get(w, ()): sc[i] += x * y
    top = sorted(((s, i) for i, s in sc.items() if s >= TH), reverse=True)[:K]
    if top: cands[cid] = [(round(s, 3), facts[i]['fid']) for s, i in top]
print(f'claims {len(claims)}; facts {len(facts)}; claims with candidates {len(cands)} (th {TH}); pairs {sum(map(len, cands.values()))}')
json.dump(cands, open('cands.json', 'w'))
json.dump({k: {x: v[x] for x in ('ep', 'date', 'text', 'snippet', 'ts', 'yt', 'ver')} for k, v in claims.items()}, open('claims.json', 'w'), ensure_ascii=False)
