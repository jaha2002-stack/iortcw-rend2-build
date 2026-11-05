#!/usr/bin/env python3
from pathlib import Path
import argparse,zipfile,struct,json,math,hashlib
SURFACE=10810
ANCHOR=(-241.0,-178.0,144.0)

def load(retail):
    for p in sorted(retail.iterdir()):
        if p.suffix.lower()!='.pk3':continue
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.lower()=='maps/church.bsp':return z.read(n)
    raise SystemExit('church.bsp missing')

def lump(data,i):
    o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]

def veq(a,b):
    return sum((a[k]-b[k])**2 for k in range(3))<=0.0004

def main(retail,out):
    data=load(retail);verts=list(struct.iter_unpack('<10f4B',lump(data,10)))
    indexes=list(struct.unpack('<%di'%(len(lump(data,11))//4),lump(data,11)))
    surfs=list(struct.iter_unpack('<12i12f2i',lump(data,13)))
    s=surfs[SURFACE];fv,nv,fi,ni=s[3],s[4],s[5],s[6]
    tris=[]
    for t in range(ni//3):
        ids=[fv+indexes[fi+t*3+j] for j in range(3)]
        pts=[tuple(float(verts[x][k]) for k in range(3)) for x in ids]
        tris.append((ids,pts))
    adj=[set() for _ in tris]
    for a in range(len(tris)):
        for b in range(a+1,len(tris)):
            matches=0
            for pa in tris[a][1]:
                if any(veq(pa,pb) for pb in tris[b][1]):matches+=1
            if matches>=2:adj[a].add(b);adj[b].add(a)
    seen=set();comps=[]
    for start in range(len(tris)):
        if start in seen:continue
        q=[start];seen.add(start);c=[]
        while q:
            a=q.pop();c.append(a)
            for b in adj[a]:
                if b not in seen:seen.add(b);q.append(b)
        pts=[p for t in c for p in tris[t][1]]
        lo=[min(p[k] for p in pts) for k in range(3)];hi=[max(p[k] for p in pts) for k in range(3)]
        ext=[hi[k]-lo[k] for k in range(3)]
        d2=sum((lo[k]-ANCHOR[k])**2 if ANCHOR[k]<lo[k] else (ANCHOR[k]-hi[k])**2 if ANCHOR[k]>hi[k] else 0 for k in range(3))
        center=[(lo[k]+hi[k])*.5 for k in range(3)]
        comps.append({'start_tri':start,'triangles':len(c),'lo':lo,'hi':hi,'extents':ext,'sorted_extents':sorted(ext,reverse=True),'distance_to_owner':math.sqrt(d2),'center':center})
    result={'bsp_sha256':hashlib.sha256(data).hexdigest(),'surface':SURFACE,'numVerts':nv,'numIndexes':ni,'triangles':ni//3,'components':sorted(comps,key=lambda x:(x['distance_to_owner'],x['triangles']))}
    out.mkdir(parents=True,exist_ok=True);(out/'CHURCH_10810_COMPONENTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('retail',type=Path);p.add_argument('out',type=Path);a=p.parse_args();main(a.retail.resolve(),a.out.resolve())
