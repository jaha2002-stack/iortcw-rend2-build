#!/usr/bin/env python3
from pathlib import Path
import json,re,struct,sys,zipfile

MAPS=('escape1','crypt1','assault','forest','dam')
KEYWORDS=('doctor','doc','guard','security','torch','fire','flame','stove','furnace','lamp','light','candle','start')

def read_bsp(retail,map_name):
    target=f'maps/{map_name}.bsp'.lower()
    for pk3 in sorted(Path(retail).glob('*.pk3')):
        try:
            with zipfile.ZipFile(pk3) as z:
                for n in z.namelist():
                    if n.lower()==target:return z.read(n)
        except zipfile.BadZipFile:
            pass
    raise RuntimeError(f'missing {target}')

def entities(data):
    if data[:4]!=b'IBSP':raise RuntimeError('not IBSP')
    off,n=struct.unpack_from('<ii',data,8)
    text=data[off:off+n].decode('latin1','replace')
    out=[]
    for body in re.findall(r'\{([^{}]*)\}',text,re.S):
        d=dict(re.findall(r'"([^"\n]+)"\s*"([^"\n]*)"',body))
        if d:out.append(d)
    return out

def xyz(s):
    try:
        v=[float(x) for x in s.split()]
        return v[:3] if len(v)>=3 else None
    except:return None

source,retail,release,output,variant=sys.argv[1:6]
output=Path(output);output.mkdir(parents=True,exist_ok=True)
report={}
for m in MAPS:
    es=entities(read_bsp(retail,m));starts=[];named=[];lights=[]
    for i,e in enumerate(es):
        cn=e.get('classname','');o=xyz(e.get('origin',''))
        if cn.startswith('info_player') and o:
            starts.append({'index':i,'classname':cn,'origin':o,'angle':e.get('angle'),'angles':e.get('angles'),'targetname':e.get('targetname'),'scriptName':e.get('scriptName') or e.get('scriptname')})
        blob=' '.join(str(e.get(k,'')) for k in ('classname','targetname','scriptName','scriptname','model','target','message','aiName','ainame')).lower()
        score=sum(1 for k in KEYWORDS if k in blob)
        if o and score:
            named.append({'index':i,'classname':cn,'origin':o,'targetname':e.get('targetname'),'scriptName':e.get('scriptName') or e.get('scriptname'),'model':e.get('model'),'target':e.get('target'),'message':e.get('message'),'score':score})
        elif o and cn=='light':
            lights.append({'index':i,'classname':cn,'origin':o,'targetname':e.get('targetname'),'scriptName':e.get('scriptName') or e.get('scriptname'),'target':e.get('target')})
    anchor=starts[0]['origin'] if starts else [0,0,0]
    lights.sort(key=lambda c:sum((c['origin'][j]-anchor[j])**2 for j in range(3)))
    report[m]={'entity_count':len(es),'starts':starts[:16],'keyword_candidates':named[:120],'nearest_lights':lights[:60]}
(output/f'map-discovery-{variant}.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
