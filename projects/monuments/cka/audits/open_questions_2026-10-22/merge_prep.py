"""Collect stage-1 questions, cluster near-duplicates across packs (TF-IDF + union-find), write merge packs."""
import json, glob, re, math, collections, sys
TH = float(sys.argv[1]) if len(sys.argv) > 1 else 0.4
STOP = set('the a an and or of to in on for at by with from that this is was were be been are as it its his her she he they them their what who whom which when where why how did does do has have had any was were whether there about into after before during more most some all one two its host say says said claim claims kirk charlie'.split())
qs = []
for p in sorted(glob.glob('out/oq_*.json')):
    pk = p.split('_')[1].split('.')[0]
    d = json.load(open(p))
    for q in d['questions']:
        q['pid'] = f'P{pk}-{q["lid"]}'
        q['claims'] = sorted([c for c, ls in d['claims'].items() if q['lid'] in ls], key=lambda c: int(c[2:]))
        qs.append(q)
def toks(s): return [w for w in re.findall(r"[a-z0-9']+", s.lower()) if w not in STOP and len(w) > 2]
docs = [toks(q['question'] + ' ' + q['topic'] + ' ' + q['topic']) for q in qs]
df = collections.Counter(w for d in docs for w in set(d)); N = len(docs)
vec = []
for d in docs:
    tf = collections.Counter(d); v = {w: tf[w] * math.log(N / (1 + df[w])) for w in tf}
    n = math.sqrt(sum(x * x for x in v.values())) or 1; vec.append({w: x / n for w, x in v.items()})
inv = collections.defaultdict(list)
for i, v in enumerate(vec):
    for w, x in v.items(): inv[w].append((i, x))
par = list(range(N))
def f(x):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
for i, v in enumerate(vec):
    sc = collections.defaultdict(float)
    for w, x in v.items():
        for j, y in inv[w]:
            if j > i: sc[j] += x * y
    for j, s in sc.items():
        if s >= TH: par[f(i)] = f(j)
groups = collections.defaultdict(list)
for i in range(N): groups[f(i)].append(i)
multi = [g for g in groups.values() if len(g) > 1]
print(f'{N} questions; {len(multi)} candidate groups covering {sum(map(len, multi))}; largest {max(map(len, multi))}')
json.dump(qs, open('all_questions.json', 'w'), ensure_ascii=False)
# pack groups (largest first) into merge packs of <= 120 questions
multi.sort(key=len, reverse=True); packs, cur = [], []
for g in multi:
    if cur and sum(map(len, cur)) + len(g) > 120: packs.append(cur); cur = []
    cur.append(g)
if cur: packs.append(cur)
for k, pk in enumerate(packs, 1):
    out = [[{x: qs[i][x] for x in ('pid', 'topic', 'question', 'known', 'settle', 'status', 'evidence', 'tips')} | {'n_claims': len(qs[i]['claims'])} for i in g] for g in pk]
    json.dump(out, open(f'mpacks/m_{k:03d}.json', 'w'), ensure_ascii=False, indent=0)
print(len(packs), 'merge packs')
