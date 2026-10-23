import sys, json, math, datetime as dt
D = sys.argv[1]
SHOT = dt.datetime(2025, 9, 10, 18, 23, 28, tzinfo=dt.timezone.utc).timestamp()
UVU = (40.2780, -111.7140)
def km(a, b, c, d):
    p = math.pi / 180; return 6371 * math.hypot((d - b) * p * math.cos((a + c) / 2 * p), (c - a) * p)
def T(x): u = dt.datetime.fromtimestamp(x, dt.timezone.utc); return f"{u:%H:%M:%S}Z ({u.astimezone(dt.timezone(dt.timedelta(hours=-6))):%H:%M} MDT, {u.astimezone(dt.timezone(dt.timedelta(hours=-7))):%H:%M} MST)"
for icao in sys.argv[2:]:
    d = json.load(open(f'{D}/{icao}.json')); ts = d['timestamp']
    P = [(ts + p[0], p[1], p[2], p[3], p[4]) for p in d['trace'] if p[1] is not None]
    print(f"== {icao} {d.get('r')} {d.get('t')} {d.get('ownOp')}; {len(P)} points {T(P[0][0])} .. {T(P[-1][0])}")
    prev_air = None
    for i, (t, la, lo, alt, gs) in enumerate(P):
        air = alt != 'ground' and (gs or 0) > 80
        if prev_air is not None and air != prev_air:
            print(f"   {'TAKEOFF' if air else 'LANDING'} ~{T(t)} at ({la:.4f},{lo:.4f}) alt {alt} gs {gs}")
        prev_air = air
    for a, b in zip(P, P[1:]):
        if b[0] - a[0] > 600: print(f"   GAP {T(a[0])} -> {T(b[0])} ({(b[0]-a[0])/60:.0f} min) from ({a[1]:.3f},{a[2]:.3f}) to ({b[1]:.3f},{b[2]:.3f})")
    at = min(P, key=lambda p: abs(p[0] - SHOT))
    print(f"   at shot 18:23:28Z: nearest point {T(at[0])} ({at[1]:.3f},{at[2]:.3f}) alt {at[3]}; {km(at[1], at[2], *UVU):.0f} km from UVU")
    c = min(P, key=lambda p: km(p[1], p[2], *UVU))
    print(f"   closest to UVU: {km(c[1], c[2], *UVU):.1f} km at {T(c[0])} alt {c[3]}")
