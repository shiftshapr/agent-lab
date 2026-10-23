"""Summarise extracted traces into legs: first/last points, takeoff/landing at known airports, times in UTC and MDT."""
import sys, json, math, glob, datetime as dt
D = sys.argv[1]
APT = {'KPVU Provo': (40.2192, -111.7234), 'KSLC Salt Lake City': (40.7884, -111.9778), 'KSDL Scottsdale': (33.6229, -111.9105),
       'KDEN Denver': (39.8561, -104.6737), 'KAPA Centennial': (39.5701, -104.8493), 'KPIR Pierre': (44.3827, -100.2860),
       'KPGA Page': (36.9261, -111.4483), 'KSBA Santa Barbara': (34.4262, -119.8404), 'KILG Wilmington': (39.6787, -75.6065),
       'KTUS Tucson': (32.1161, -110.9410), 'KFHU Sierra Vista/Ft Huachuca': (31.5885, -110.3444), 'KBOI Boise': (43.5644, -116.2228),
       'KLAS Las Vegas': (36.0840, -115.1537), 'KMDW Chicago Midway': (41.7868, -87.7522), 'KORD Chicago OHare': (41.9742, -87.9073),
       'KPWK Chicago Exec': (42.1142, -87.9015), 'KOFF Offutt': (41.1183, -95.9125), 'KLNK Lincoln': (40.8510, -96.7592),
       'KOGD Ogden': (41.1961, -112.0122), 'KHIF Hill AFB': (41.1240, -111.9730), 'KCOS Colorado Springs': (38.8058, -104.7008),
       'KADW Andrews': (38.8108, -76.8669), 'KGJT Grand Junction': (39.1224, -108.5267), 'KSGU St George': (37.0364, -113.5103)}
MDT = dt.timezone(dt.timedelta(hours=-6))
def km(a, b, c, d):
    p = math.pi / 180; return 6371 * math.hypot((d - b) * p * math.cos((a + c) / 2 * p), (c - a) * p)
def near(la, lo):
    best = min(APT.items(), key=lambda kv: km(la, lo, *kv[1])); d = km(la, lo, *best[1])
    return f'{best[0]} ({d:.0f} km)' if d < 25 else f'({la:.3f},{lo:.3f})'
def t(x): u = dt.datetime.fromtimestamp(x, dt.timezone.utc); return f"{u:%H:%M}Z / {u.astimezone(MDT):%H:%M} MDT"
out = {}
for f in sorted(glob.glob(f'{D}/*.json')):
    if f.endswith(('near_provo_uvu.json', 'legs.json', 'stream_provenance.json')): continue
    d = json.load(open(f)); r = (d.get('r') or '').upper(); ts = d['timestamp']
    pts = [p for p in d.get('trace', []) if p[1] is not None]
    if not pts: continue
    legs, cur = [], [pts[0]]
    for a, b in zip(pts, pts[1:]):
        ground = lambda p: p[3] == 'ground' or (isinstance(p[3], (int, float)) and p[3] < 200 and (p[4] or 0) < 60)
        if b[0] - a[0] > 1200 or (ground(a) != ground(b) and ground(b)):
            cur.append(b) if not (b[0] - a[0] > 1200) else None; legs.append(cur); cur = [b]
        else: cur.append(b)
    legs.append(cur)
    desc = []
    for L in legs:
        air = [p for p in L if p[3] != 'ground']
        if not air: desc.append(f"on ground {near(L[0][1], L[0][2])} {t(ts+L[0][0])} .. {t(ts+L[-1][0])}"); continue
        desc.append(f"{near(L[0][1], L[0][2])} {t(ts+L[0][0])} -> {near(L[-1][1], L[-1][2])} {t(ts+L[-1][0])}; max alt {max((p[3] for p in air if isinstance(p[3], (int,float))), default=0)} ft; {len(L)} pts")
    out[d['icao']] = {'r': r, 't': d.get('t'), 'desc': d.get('desc'), 'ownOp': d.get('ownOp'), 'legs': desc}
json.dump(out, open(f'{D}/legs.json', 'w'), indent=1)
for k, v in out.items():
    if v['r'] in sys.argv[2:] or v['r'].startswith('SU-'):
        print(k, v['r'], v['t'], v['ownOp']); [print('   ', l) for l in v['legs']]
