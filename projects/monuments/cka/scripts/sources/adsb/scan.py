"""Stream an adsb.lol day's tar parts (args: SRC|url OUT [TAG]; "url" streams from GitHub without saving); keep traces for target registrations and any aircraft near Provo/UVU."""
import sys, tarfile, gzip, json, math, io
SRC = sys.argv[1]; OUT = sys.argv[2]; TAG = sys.argv[3] if len(sys.argv) > 3 else "v2025.09.10-planes-readsb-prod-0"
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
class Url(io.RawIOBase):
    """Read the release parts straight from GitHub (no disk), hashing each part as it streams."""
    def __init__(s, tag):
        import urllib.request, hashlib
        s.urls = [f'https://github.com/adsblol/globe_history_2025/releases/download/{tag}/{tag}.tar.{x}' for x in ('aa', 'ab')]
        s.open, s.hl, s.cur, s.h, s.sizes, s.digests = urllib.request.urlopen, hashlib.sha256, None, None, [], []
    def readable(s): return True
    def readinto(s, b):
        while True:
            if s.cur is None:
                if not s.urls: return 0
                s.cur = s.open(s.urls.pop(0), timeout=300); s.h = s.hl(); s.sizes.append(0)
            n = s.cur.readinto(b)
            if n:
                s.h.update(memoryview(b)[:n]); s.sizes[-1] += n; return n
            s.digests.append(s.h.hexdigest()); s.cur = None
if SRC == 'url':
    src = Url(TAG)
else:
    src = Cat([f'{SRC}/{TAG}.tar.aa', f'{SRC}/{TAG}.tar.ab'])
tf = tarfile.open(fileobj=io.BufferedReader(src, 1 << 20), mode='r|')
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
for _ in tf: pass
if SRC == 'url':
    while src.readinto(bytearray(1 << 20)): pass
    json.dump({'tag': TAG, 'part_bytes': src.sizes, 'part_sha256': src.digests}, open(f'{OUT}/stream_provenance.json', 'w'))
print('done', n, 'traces;', kept, 'kept;', len(near), 'near sites')
