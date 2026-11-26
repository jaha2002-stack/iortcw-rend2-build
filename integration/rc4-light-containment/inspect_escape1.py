#!/usr/bin/env python3
"""Inspect protected map in CI. Export metadata, never retail assets."""
from pathlib import Path
import sys,zipfile,struct,re,json,hashlib
retail=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
b=None
for p in sorted(retail.glob('*')):
 if p.suffix.lower()!='.pk3':continue
 with zipfile.ZipFile(p) as z:
  for n in z.namelist():
   if n.lower()=='maps/escape1.bsp':b=z.read(n)
assert b is not None,'escape1 BSP missing'
def lump(i):
 off,n=struct.unpack_from('<ii',b,8+i*8);assert off>=0 and n>=0 and off+n<=len(b);return b[off:off+n]
entities=[dict(re.findall(r'"([^"\n]+)"\s*"([^"\n]*)"',s)) for s in re.findall(r'\{([^{}]*)\}',lump(0).decode('latin1'))]
shaders=list(struct.iter_unpack('<64sii',lump(1)));planes=list(struct.iter_unpack('<4f',lump(2)));brushes=list(struct.iter_unpack('<3i',lump(8)));sides=list(struct.iter_unpack('<2i',lump(9)))
def solid(p):
 result=[]
 for i,(first,count,shader) in enumerate(brushes):
  if not shaders[shader][2]&1:continue
  if all(sum(planes[sides[j][0]][k]*p[k] for k in range(3))-planes[sides[j][0]][3] < -0.05 for j in range(first,first+count)):result.append(i)
 return result
def pos(e):
 try:return list(map(float,e.get('origin','').split()))
 except ValueError:return []
selected=[]
for i,e in enumerate(entities):
 p=pos(e);cls=e.get('classname','');interesting=cls in ['shooter_tesla','dlight'] or 'fire' in e.get('noise','').lower() or 'furnace' in e.get('model2',e.get('model','')).lower()
 if interesting:
  row={'index':i,**e}
  if len(p)==3:row['inside_solid_brushes']=solid(p)
  if e.get('target'):
   row['targets']=[{'index':j,**t} for j,t in enumerate(entities) if t.get('targetname')==e['target']]
  selected.append(row)
json.dump({'map':'escape1','bsp_sha256':hashlib.sha256(b).hexdigest(),'entity_count':len(entities),'sources':selected},(out/'escape1-source-positions.json').open('w'),indent=2)
print('ESCAPE1_SOURCE_METADATA_EXPORTED',len(selected),flush=True)
