"""Usage: norm_results.py PACK_DIR. Normalise Opus verify results: fix episode from item headings; drop Mentions changes that only add/remove N-3."""
import json,re,sys,glob
from pathlib import Path
S=Path(sys.argv[1]); Cka=Path('projects/monuments/cka')
for p in sorted(S.glob('results_*.json')):
    n=p.stem.split('_')[1]; items=(S/f'items_{n}.md').read_text()
    eps={c:int(e) for c,e in re.findall(r'^## (C-\d+) \(episode (\d+)\)',items,re.M)}
    blocks={c:b for c,b in re.findall(r'^## (C-\d+) \(episode \d+\)\n\n(.*?)\n\nNode ids named',items,re.M|re.S)}
    rs=json.loads(p.read_text()); ch=0
    for r in rs:
        if r['claim'] in eps: r['episode']=eps[r['claim']]
        f=r.get('fix') or {}
        if isinstance(f.get('mentions'),list):
            m=re.search(r'^Mentions:\s*(.*)$',blocks.get(r['claim'],''),re.M)
            old=set(re.findall(r'N-\d+',m.group(1))) if m else set()
            if (set(f['mentions'])^old)<= {'N-3'}:
                f.pop('mentions'); ch+=1
                if not any(k in f for k in ('claim','label','timestamp','names')) and r.get('person')=='error' \
                   and r.get('attribution')!='error' and r.get('accuracy')!='material' and r.get('timestamp')!='error':
                    r['person']='ok'; r['material']=False
    miss=set(eps)-{r['claim'] for r in rs}
    p.write_text(json.dumps(rs,indent=1,ensure_ascii=False)+'\n')
    print(n,len(rs),'material',sum(bool(r.get('material')) for r in rs),'n3-dropped',ch,'missing',len(miss))
