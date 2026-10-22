"""Check every fact's quote appears verbatim (whitespace/quote-mark normalised) in its pack; write facts_all.json."""
import json, re, glob, pathlib
def norm(s): return re.sub(r'\s+', ' ', s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"').replace('—','-').replace('–','-')).strip().lower()
allf, bad = [], []
for f in sorted(glob.glob('facts/pack_*.json')):
    n = pathlib.Path(f).stem
    text = norm(pathlib.Path(f'packs/{n}.txt').read_text())
    try: arr = json.load(open(f))
    except Exception as e: print(f, 'BAD JSON', e); continue
    ok = 0
    for i, x in enumerate(arr):
        q = norm(x.get('quote', ''))
        if q and q in text:
            x['fid'] = f'{n}#{i}'
            if len(q.split()) < 6:  # bare "Yes." etc: keep the preceding question as context
                m = re.search(r'\(\s*' + re.escape(re.sub(r'[()\s]', '', x.get('loc', ''))) + r'\s*\)', text) if x.get('loc', '').startswith('(') else None
                pos = text.find(q, m.start()) if m else -1
                if pos < 0: pos = text.find(q)
                x['context'] = text[max(0, pos - 400):pos + len(q)]
            allf.append(x); ok += 1
        else: bad.append((n, i, x.get('quote', '')[:120]))
    print(n, len(arr), 'ok', ok)
json.dump(allf, open('facts_all.json', 'w'), ensure_ascii=False)
print('total ok', len(allf), 'bad', len(bad)); [print(' ', b) for b in bad[:15]]
