"""Merge out/K-*.json into commentary_claims.json: ids CC-n, name fixes, duplicate-upload removal."""
import json, glob, re
items = {x['kid']: x for x in json.load(open('approved.json'))}
FIX_NEW = {'george farmer': 'N-30', 'tyler bowyer': 'N-11', 'terrell': 'N-261', 'terryl farnsworth': 'N-261'}
FIX_TEXT = [(r'\bAndrew (Cipher|Seifer)\b', 'Andrew Sypher'), (r'\bTerrell\b', 'Terryl Farnsworth')]
DUP = {'K-013': 'K-011', 'K-030': 'K-028'}
tok = lambda s: set(w for w in re.findall(r'[a-z0-9]+', s.lower()) if len(w) > 2)
eps = {}
for p in sorted(glob.glob('out/K-*.json')):
    d = json.load(open(p)); eps[d['kid']] = d
out, n, dropped = [], 0, []
for kid in sorted(eps):
    d = eps[kid]
    ref = [tok(c['snippet']) for c in eps[DUP[kid]]['claims']] if kid in DUP and DUP[kid] in eps else []
    for c in d['claims']:
        t = tok(c['snippet'])
        if any(len(t & r) / max(1, len(t)) >= 0.6 for r in ref):
            dropped.append((kid, c['snippet'][:50])); continue
        for k in list(c.get('mentions_new', [])):
            key = re.sub(r'\s*\(.*', '', k).strip().lower()
            if key in FIX_NEW or 'sypher' in key or 'cipher' in key or 'seifer' in key:
                c['mentions_new'].remove(k); c['mentions'].append(FIX_NEW.get(key, 'N-331'))
        for a, b in FIX_TEXT: c['claim'] = re.sub(a, b, c['claim'])
        c['mentions'] = sorted(set(c['mentions']), key=lambda x: int(x[2:]))
        n += 1
        it = items[kid]
        out.append({'id': f'CC-{n}', 'kid': kid, 'video_id': it['video_id'], 'channel': it['channel'], 'title': it['title'],
                    'date': it['upload_date'], **c,
                    'url': f"https://www.youtube.com/watch?v={it['video_id']}&t={sum(int(x)*m for x, m in zip(c['timestamp'].split(':'), (3600, 60, 1)))}s"})
json.dump(out, open('commentary_claims.json', 'w'), ensure_ascii=False, indent=1)
print(len(eps), 'episodes', len(out), 'claims', len(dropped), 'duplicates dropped')
