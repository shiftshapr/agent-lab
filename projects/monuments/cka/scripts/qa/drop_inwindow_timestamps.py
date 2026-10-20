"""Usage: drop_inwindow_timestamps.py PACK_DIR. Drop timestamp findings that are within the archive rule (content <=75s after ts): fix ts moves later by <=70s."""
import json,sys,glob,re
def sec(t):
    p=[int(x) for x in t.split(':')]; return p[0]*3600+p[1]*60+p[2] if len(p)==3 else p[0]*60+p[1]
cur={}
for f in glob.glob(str(__import__('pathlib').Path(__file__).resolve().parents[2]/'drafts'/'episode_*.md')):
    for m in re.finditer(r'\*\*(C-\d+)\*\*.*?\nClaim Timestamp: (\S+)',open(f).read(),re.S): cur[m.group(1)]=m.group(2)
tot=0
for f in sorted(glob.glob(sys.argv[1]+'/results_*.json')):
    R=json.load(open(f)); n=0
    for r in R:
        fx=r.get('fix') or {}
        if r.get('timestamp')=='error' and isinstance(fx,dict) and fx.get('timestamp') and r['claim'] in cur:
            try: d=sec(fx['timestamp'])-sec(cur[r['claim']])
            except ValueError: continue
            if 0<=d<=70:
                fx.pop('timestamp'); r['timestamp']='ok'; n+=1
                r['material']=r.get('attribution')=='error' or r.get('accuracy')=='material' or r.get('person')=='error'
                if not fx and not r['material'] and r.get('accuracy')!='minor': r['fix']={}
    json.dump(R,open(f,'w'),indent=1); tot+=n
print('dropped in-rule timestamp findings:',tot)
