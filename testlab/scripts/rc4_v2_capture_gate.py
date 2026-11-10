#!/usr/bin/env python3
"""Require valid world leaves and reproducible, attributable light contributions."""
from pathlib import Path
import json,re,sys
import numpy as np
from PIL import Image
p=Path(sys.argv[1]);text=(p/'console-0.log').read_text(errors='replace');scenes={};lights={};leaves={}
def fields(row):return dict(re.findall(r'(\w+)=([^ ]+)',row))
for row in re.findall(r'AB_SCENE [^\r\n]+',text):
 d=fields(row);scenes[int(d['step'])]=d
for row in re.findall(r'AB_LIGHT [^\r\n]+',text):
 d=fields(row);lights.setdefault(int(d['step']),[]).append(d)
for row in re.findall(r'AB_LEAF [^\r\n]+',text):
 d=fields(row);leaves[int(d['step'])]=d
views=[('fire_outside_far',[-1010,692,-50]),('fire_outside_near',[-1100,692,-50]),('fire_inside',[-1340,760,-10]),('tesla_room',[120,560,-470]),('tesla_above_a',[448,448,-210]),('tesla_above_b',[576,448,-210]),('tesla_stairs',[448,320,-210])]
errors=[];results=[]
for i,(name,eye) in enumerate(views):
 steps=list(range(1+5*i,6+5*i));group=[scenes.get(n,{}) for n in steps]
 def check(ok,message):
  if not ok:errors.append(name+': '+message)
 check(all(group),'missing scene records')
 if not all(group):continue
 check(all(int(s['lights'])>0 for s in group),'zero-light scene')
 check(all(int(leaves.get(n,{}).get('cluster',-1))>=0 for n in steps),'camera outside valid world BSP leaf')
 check(len({s['time'] for s in group})==1,'clock mismatch');check(len({s['camera'] for s in group})==1,'camera mismatch')
 actual=[float(v) for v in group[0]['camera'].split(',')];check(max(abs(a-b) for a,b in zip(actual,eye))<1.0,'unexpected camera '+str(actual))
 records=[lights.get(n,[]) for n in steps];signatures=[[(d['origin'],d['radius'],d['color'],d['native'],d['fire'],d['required']) for d in ds] for ds in records]
 check(all(s==signatures[0] for s in signatures),'light submission mismatch')
 required=[d for d in records[0] if int(d['required'])];check(bool(required),'no required emitters');check(all(0<=int(d['worldSlot'])<32 for d in required),'required emitter missing mask')
 def match(d):
  x,y,z=map(float,d['origin'].split(','))
  if name.startswith('fire'):return int(d['native']) and abs(x+1340)<2 and abs(y-692)<2 and abs(z+36)<2
  return (int(d['native']) and abs(x-328)<2 and abs(y-448)<2 and abs(z+532)<2) or (not int(d['native']) and 40<x<210 and abs(y-448)<2 and abs(z+476)<2)
 matching=[d for d in required if match(d)];check(bool(matching),'specific target family absent')
 if name.startswith('fire'):check(any(float(d['radius'])>=250 for d in matching),'authored bright phase missing')
 images={}
 for state in ['reference','fixed','source_off','reference_repeat','fixed_repeat','production_effects']:
  path=p/(name+'_'+state+'.png');check(path.exists(),'missing '+state)
  if path.exists():images[state]=np.asarray(Image.open(path).convert('RGB')).astype(np.int16)
 if len(images)!=6:continue
 a,b,c=images['reference'],images['fixed'],images['source_off'];delta=abs(a-b);signal=abs(a-c);remain=abs(b-c)
 metrics={'reference_fixed_mean_abs':float(delta.mean()),'reference_source_off_mean_abs':float(signal.mean()),'fixed_source_off_mean_abs':float(remain.mean()),'changed_pixels':int(np.count_nonzero(np.max(delta,axis=2)>1)),'source_signal_pixels':int(np.count_nonzero(np.max(signal,axis=2)>1)),'reference_repeat_exact':bool(np.array_equal(a,images['reference_repeat'])),'fixed_repeat_exact':bool(np.array_equal(b,images['fixed_repeat']))}
 check(metrics['reference_repeat_exact'] and metrics['fixed_repeat_exact'],'repeat frame not pixel-identical')
 check(metrics['source_signal_pixels']>16,'no measurable target-family contribution: not proof')
 results.append({'view':name,'eye':actual,'leaf':leaves.get(steps[0]),'time':int(group[0]['time']),'lights':int(group[0]['lights']),'required_lights':len(required),'target_records':matching,'metrics':metrics,'visual_status':'REQUIRES_REVIEW'})
report={'status':'CAPTURE_INTEGRITY_PASS_VISUAL_REVIEW_PENDING' if not errors else 'CAPTURE_INTEGRITY_FAIL','baseline':'same candidate, geometric mask bypass for target family ONLY; not separate RC4 binary','source_off':'target family removed ONLY for attribution; never the fix','phase':'existing maximum authored lightstyle phase, frozen cgame time/random arcs','errors':errors,'views':results}
(p/'validated-views.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if errors:raise SystemExit(1)
