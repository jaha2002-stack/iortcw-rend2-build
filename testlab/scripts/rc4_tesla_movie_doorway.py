#!/usr/bin/env python3
"""The guardroom entrance is north of the torch wall, not through that wall."""
from pathlib import Path
import importlib.util,sys,struct,zipfile,json
base=Path(__file__).with_name('rc4_noclip_movies.py')
# Recording demos does not need delivery resolution; replay still renders 960x540.
t=base.read_text();a="'+set','r_customwidth','960','+set','r_customheight','540'";b="'+set','r_customwidth',('320' if '+spdevmap' in args else '960'),'+set','r_customheight',('180' if '+spdevmap' in args else '540')";assert t.count(a)==1
copy=base.with_name('rc4_movie_runtime_local.py');copy.write_text(t.replace(a,b))
spec=importlib.util.spec_from_file_location('movie',copy);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
r=m.ROUTES['tesla'];r[-6:]=[[16.6,-160,670,-336,24,620],[17.5,-192,728,-336,20,540],[18.6,-292,752,-336,10,540],[20.0,-430,752,-328,7,555],[22.0,-590,690,-324,12,575],[24.0,-620,690,-324,13,590]]
m.ROUTES={'tesla':r}
if sys.argv[1]=='patch':m.patch_source(Path(sys.argv[2]).resolve())
elif sys.argv[1]=='run':
 retail=Path(sys.argv[3]).resolve();data=None
 for p in sorted(retail.iterdir()):
  if p.suffix.lower()=='.pk3':
   with zipfile.ZipFile(p) as z:
    for n in z.namelist():
     if n.lower()=='maps/escape1.bsp':data=z.read(n)
 assert data is not None
 def lump(i):
  o,n=struct.unpack_from('<ii',data,8+i*8);return data[o:o+n]
 planes=list(struct.iter_unpack('<4f',lump(2)));nodes=list(struct.iter_unpack('<9i',lump(3)));leaves=list(struct.iter_unpack('<12i',lump(4)))
 def cluster(p):
  n=0
  while n>=0:
   row=nodes[n];pl=planes[row[0]];n=row[1 if sum(pl[k]*p[k] for k in range(3))>=pl[3] else 2]
  return leaves[-1-n][0]
 bad=[];j=0
 for i in range(600):
  t=i/25
  while j<len(r)-2 and t>r[j+1][0]:j+=1
  a,b=r[j:j+2];u=(t-a[0])/(b[0]-a[0]);p=[a[k]+u*(b[k]-a[k]) for k in range(1,4)]
  if cluster(p)<0:bad.append({'frame':i,'eye':p})
 (m.OUT/'route-geometry-gate.json').write_text(json.dumps({'frames':600,'invalid':bad,'guardroom_entry':'north doorway at y=752'},indent=2))
 assert not bad,('Camera enters solid world',bad)
 m.movies(Path(sys.argv[2]).resolve(),retail)
else:raise SystemExit('patch SOURCE or run SOURCE RETAIL')
