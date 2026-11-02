#!/usr/bin/env python3
"""Private-map input -> derived camera/floor metadata only, never BSP payload."""
from pathlib import Path
import zipfile,struct,json,sys,re,math
b=None
for p in sorted(Path(sys.argv[1]).iterdir()):
 if p.suffix.lower()=='.pk3':
  with zipfile.ZipFile(p) as z:
   for n in z.namelist():
    if n.lower()=='maps/escape1.bsp':b=z.read(n)
assert b is not None
def lump(i):
 o,n=struct.unpack_from('<ii',b,8+i*8);assert 0<=o<=o+n<=len(b);return b[o:o+n]
shaders=list(struct.iter_unpack('<64sii',lump(1)));planes=list(struct.iter_unpack('<4f',lump(2)));nodes=list(struct.iter_unpack('<9i',lump(3)));leaves=list(struct.iter_unpack('<12i',lump(4)))
verts=list(struct.iter_unpack('<10f4B',lump(10)));surfaces=list(struct.iter_unpack('<12i12f2i',lump(13)))
model=struct.unpack_from('<6f4i',lump(7));brushes=list(struct.iter_unpack('<3i',lump(8)));sides=list(struct.iter_unpack('<2i',lump(9)));solid=[]
for bi in range(model[8],model[8]+model[9]):
 first,count,sh=brushes[bi]
 if shaders[sh][2]&1:solid.append([planes[sides[j][0]] for j in range(first,first+count)])
def leaf(p):
 n=0
 while n>=0:
  row=nodes[n];pl=planes[row[0]];n=row[1 if sum(pl[k]*p[k] for k in range(3))>=pl[3] else 2]
 return leaves[-1-n][0:2]
def ray(p,d,limit):
 best=limit;inside=False
 for ps in solid:
  lo,hi=0.,limit;strict=True
  for pl in ps:
   a=sum(pl[k]*p[k] for k in range(3))-pl[3];v=sum(pl[k]*d[k] for k in range(3))
   if a>=-0.01:strict=False
   if abs(v)<1e-8:
    if a>0.01:hi=-1;break
   elif v>0:hi=min(hi,-a/v)
   else:lo=max(lo,-a/v)
   if lo>hi+0.01:break
  if strict:inside=True
  if hi>=lo and hi>=0:best=min(best,max(0,lo))
 return best,inside
floors=[]
for sid in range(model[6],model[6]+model[7]):
 s=surfaces[sid];v=verts[s[3]:s[3]+s[4]]
 if s[2]!=1 or len(v)<3:continue
 if min(q[9] for q in v)<0.9:continue
 mn=[min(q[k] for q in v) for k in range(3)];mx=[max(q[k] for q in v) for k in range(3)]
 if mx[2]-mn[2]>0.5 or not(-570<mn[2]<100):continue
 center=[sum(q[k] for q in v)/len(v) for k in range(3)]
 if not(-256<center[0]<1056 and 0<center[1]<1200):continue
 shader=shaders[s[0]][0].split(b'\0')[0].decode(errors='replace')
 eye=[center[0],center[1],center[2]+64];cluster,area=leaf(eye);down,inside=ray(eye,[0,0,-1],128);up,inside2=ray(eye,[0,0,1],512)
 # Eye must be above this rendered upward face, not across another ceiling.
 valid=cluster>=0 and not inside and not inside2 and abs(down-64)<1 and up>=16
 floors.append({'surface':sid,'shader':shader,'center':center,'bounds':[mn,mx],'eye':eye,'cluster':cluster,'area':area,'down':down,'up':up,'valid_camera':valid})
entities=[]
for i,raw in enumerate(re.findall(r'\{([^{}]*)\}',lump(0).decode(errors='replace'),re.S)):
 e=dict(re.findall(r'"([^"]*)"\s*"([^"]*)"',raw))
 try:p=list(map(float,e.get('origin','').split()))
 except ValueError:continue
 if len(p)!=3 or not(-256<p[0]<1056 and 0<p[1]<1200 and -600<p[2]<100):continue
 if e.get('classname','').startswith(('ai_','info_player','script_','misc_model')):entities.append({'ordinal':i,**{k:e[k] for k in ['classname','origin','angle','targetname','scriptName','model'] if k in e}})
out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'map':'escape1','floors':floors,'nearby_entities':entities,'scope':'Derived upward-rendered floor centers and test camera metadata only'},indent=2));print('UPWARD_RENDERED_FLOORS',len(floors),'valid',sum(f['valid_camera'] for f in floors))
