"""Stream the adsb.lol 2025-09-10 tar parts; keep traces for target registrations and any aircraft near Provo/UVU."""
import sys, tarfile, gzip, json, math, io
SRC = sys.argv[1]; OUT = sys.argv[2]
TARGET = {'SU-BTT','SU-BND','SU-BTU','N582MM','N1098L','N888KG','N102DZ','N8724A','N560TW','N40JD'}
SITES = {'KPVU': (40.2192, -111.7234), 'UVU': (40.2780, -111.7140)}
def km(a, b, c, d):
    p = math.pi / 180; x = (d - b) * p * math.cos((a + c) / 2 * p); y = (c - a) * p
    return 6371 * math.hypot(x, y)
class Cat(io.RawIOBase):
    def __init__(s, paths): s.fs = [open(p, 'rb') for p in paths]; s.i = 0
    def readable(s): return True
    def readinto(s, b):
        while s.i < len(s.fs):
            n = s.fs[s.i].readinto(b)
            if n: return n
            s.i += 1
        return 0
parts = [f'{SRC}/v2025.09.10-planes-readsb-prod-0.tar.aa', f'{SRC}/v2025.09.10-planes-readsb-prod-0.tar.ab']
tf = tarfile.open(fileobj=io.BufferedReader(Cat(parts), 1 << 20), mode='r|')
near, kept, n = [], 0, 0
for m in tf:
    if not m.isfile() or 'trace_full_' not in m.name: continue
    raw = tf.extractfile(m).read(); n += 1
    try:
        d = json.loads(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)
    except Exception: continue
    r = (d.get('r') or '').upper(); ts = d.get('timestamp', 0)
    hit = r in TARGET or r.startswith('SU-') or '99-0044' in r or 'C-37' in (d.get('t') or '') and False
    close = {}
    for p in d.get('trace', []):
        if p[1] is None: continue
        for s, (la, lo) in SITES.items():
            dist = km(p[1], p[2], la, lo)
            if dist < 8 and (s not in close or dist < close[s][0]): close[s] = (round(dist, 2), ts + p[0], p[3])
    if hit or close:
        json.dump(d, open(f"{OUT}/{d.get('icao','x')}.json", 'w')); kept += 1
    if close:
        near.append({'icao': d.get('icao'), 'r': d.get('r'), 't': d.get('t'), 'desc': d.get('desc'), 'ownOp': d.get('ownOp'), 'close': close})
    if n % 50000 == 0: print(n, kept, flush=True)
json.dump(near, open(f'{OUT}/near_provo_uvu.json', 'w'), indent=0)
print('done', n, 'traces;', kept, 'kept;', len(near), 'near sites')
