import json, re, pathlib
D = pathlib.Path.home()/'agent-lab-data/cka_sources'
man = json.load(open('/Users/shiftshapr/agent-lab-wt-p0b/projects/monuments/cka/sources/manifest.json'))['sources']
TS = re.compile(r'\( ?\d+:\d+(?::\d+)? ?\)')
packs, n = [], 0
for s in man:
    if not s.get('text_file'): continue
    lines = (D/s['stream']/s['text_file']).read_text(errors='ignore').splitlines()
    if s['format'] == 'html':
        a = next(i for i, l in enumerate(lines) if TS.search(l))
        b = next((i for i, l in enumerate(lines) if i > a and 'Luckily for you' in l), len(lines))
        lines = lines[a:b]
    lines = [l.strip() for l in lines if l.strip()]
    cur, w, part = [], 0, 1
    def flush():
        global n, cur, w, part
        if not cur: return
        n += 1
        hdr = f"# {s['id']} part {part}: {s['title']} ({s['date']}, {s['publisher']})\n\n"
        pathlib.Path(f'packs/pack_{n:03d}.txt').write_text(hdr + '\n'.join(cur) + '\n')
        packs.append({'pack': n, 'sid': s['id'], 'part': part, 'words': w}); cur, w = [], 0; part += 1
    for l in lines:
        boundary = TS.search(l) or l.startswith('[page ')
        if w > 11000 and boundary: flush()
        cur.append(l); w += len(l.split())
    flush()
json.dump(packs, open('packs.json', 'w'), indent=0)
print(len(packs), sum(p['words'] for p in packs)); print([(p['pack'], p['sid'], p['words']) for p in packs])
