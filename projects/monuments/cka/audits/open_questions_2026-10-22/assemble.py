"""Apply merges, order questions by first claim, number Q-1..Q-n, write the register."""
import json, glob, sys
qs = {q['pid']: q for q in json.load(open('all_questions.json'))}
used, final = set(), []
for p in sorted(glob.glob('merged/m_*.json')):
    for m in json.load(open(p)):
        mem = [x for x in m['members'] if x in qs and x not in used]
        if len(mem) < 2: continue
        used.update(mem)
        claims = sorted({c for x in mem for c in qs[x]['claims']}, key=lambda c: int(c[2:]))
        final.append({k: m[k] for k in ('topic', 'question', 'known', 'settle', 'status', 'evidence', 'tips')} | {'claims': claims, 'from': mem})
for pid, q in qs.items():
    if pid not in used:
        final.append({k: q[k] for k in ('topic', 'question', 'known', 'settle', 'status', 'evidence', 'tips')} | {'claims': q['claims'], 'from': [pid]})
final = [q for q in final if q['claims']]
final.sort(key=lambda q: (int(q['claims'][0][2:]), q['question']))
reg = []
for i, q in enumerate(final, 1):
    q['tips'] = sorted(set(q.get('tips') or []), key=lambda c: int(c[2:]))
    q['evidence'] = list(dict.fromkeys(q.get('evidence') or []))
    if q['status'] != 'open' and not any(x.startswith('S-') for x in q['evidence']): q['status'] = 'open'
    reg.append({'id': f'Q-{i}', **{k: q[k] for k in ('topic', 'question', 'known', 'settle', 'status', 'evidence', 'claims', 'tips')}})
json.dump(reg, open(sys.argv[1], 'w'), indent=1, ensure_ascii=False)
json.dump({r['id']: q['from'] for r, q in zip(reg, final)}, open('provenance.json', 'w'))
print(len(qs), 'drafted ->', len(reg), 'questions')
