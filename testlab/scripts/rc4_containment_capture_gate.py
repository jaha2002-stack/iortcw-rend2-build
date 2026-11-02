#!/usr/bin/env python3
"""Validate actual world scenes, not a successful screenshot command alone."""
from pathlib import Path
import json,re,sys
import numpy as np
from PIL import Image
p=Path(sys.argv[1]);text=(p/'console-0.log').read_text(errors='replace')
scenes={};lights={}
for row in re.findall(r'AB_SCENE [^\r\n]+',text):
 d=dict(re.findall(r'(\w+)=([^ ]+)',row));scenes[int(d['step'])]=d
for row in re.findall(r'AB_LIGHT [^\r\n]+',text):
 d=dict(re.findall(r'(\w+)=([^ ]+)',row));lights.setdefault(int(d['step']),[]).append(d)
views=[('fire_outside_far',[-1010,692,-50]),('fire_outside_near',[-1100,692,-50]),('fire_inside',[-1340,760,-10]),('tesla_room',[120,560,-470]),('tesla_above_a',[328,448,-210]),('tesla_above_b',[328,580,-210]),('tesla_stairs',[120,560,-240])]
errors=[];results=[]
for i,(name,eye) in enumerate(views):
 steps=list(range(1+5*i,6+5*i));group=[scenes.get(n,{}) for n in steps]
 def check(ok,message):
  if not ok:errors.append(name+': '+message)
 check(all(group),'missing scene records')
 if not all(group):continue
 check(all(int(s['lights'])>0 for s in group),'zero-light scene is not evidence')
 check(len({s['time'] for s in group})==1,'clock mismatch')
 check(len({s['camera'] for s in group})==1,'camera mismatch')
 actual=[float(v) for v in group[0]['camera'].split(',')]
 check(max(abs(a-b) for a,b in zip(actual,eye))<1.0,'camera does not equal probed eye: '+str(actual))
 records=[lights.get(n,[]) for n in steps]
 signatures=[[(d['origin'],d['radius'],d['color'],d['native'],d['fire'],d['required']) for d in ds] for ds in records]
 check(all(s==signatures[0] for s in signatures),'light submission mismatch')
 required=[d for d in records[0] if int(d['required'])]
 check(bool(required),'no required emitter submitted')
 check(all(int(d['worldSlot'])>=0 for d in required),'required emitter missing world mask')
 target=(-1340,692,-36) if name.startswith('fire_') else (328,448,-532)
 matching=[d for d in required if max(abs(float(v)-t) for v,t in zip(d['origin'].split(','),target))<2]
 check(bool(matching),'specific fire/scripted-Tesla source missing')
 images={}
 for state in ['reference','fixed','source_off','reference_repeat','fixed_repeat','production_effects']:
  path=p/(name+'_'+state+'.png')
  check(path.exists(),'missing '+state)
  if path.exists():images[state]=np.asarray(Image.open(path).convert('RGB')).astype(np.int16)
 if len(images)!=6:continue
 a,b,c=images['reference'],images['fixed'],images['source_off']
 metrics={'reference_fixed_mean_abs':float(abs(a-b).mean()),'reference_source_off_mean_abs':float(abs(a-c).mean()),'fixed_source_off_mean_abs':float(abs(b-c).mean()),'changed_pixels':int(np.count_nonzero(np.max(abs(a-b),axis=2)>1)),'source_signal_pixels':int(np.count_nonzero(np.max(abs(a-c),axis=2)>1)),'reference_repeat_exact':bool(np.array_equal(a,images['reference_repeat'])),'fixed_repeat_exact':bool(np.array_equal(b,images['fixed_repeat']))}
 check(metrics['reference_repeat_exact'] and metrics['fixed_repeat_exact'],'repeat frame not pixel-identical')
 results.append({'view':name,'eye':actual,'time':int(group[0]['time']),'lights':int(group[0]['lights']),'required_lights':len(required),'target_records':matching,'metrics':metrics,'visual_status':'REQUIRES_REVIEW' if metrics['source_signal_pixels'] else 'NO_MEASURABLE_SOURCE_SIGNAL'})
report={'status':'CAPTURE_INTEGRITY_PASS_VISUAL_REVIEW_PENDING' if not errors else 'CAPTURE_INTEGRITY_FAIL','baseline':'same candidate with ONLY geometric mask bypassed; not separate RC4 binary','source_off':'attribution control for required authored emitters; never the fix','errors':errors,'views':results}
(p/'validated-views.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
if errors:raise SystemExit(1)
