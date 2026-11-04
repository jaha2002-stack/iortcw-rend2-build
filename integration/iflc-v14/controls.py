#!/usr/bin/env python3
"""Receiver-only target isolation and open-side control; NOT shipped in DLL."""
from pathlib import Path
import argparse,sys,json,re,math,subprocess
KIT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('mode',choices=['instrument','capture']);p.add_argument('--retail',type=Path);p.add_argument('--map');p.add_argument('--out',type=Path);a=p.parse_args()
if a.mode=='instrument':
 subprocess.run([sys.executable,str(KIT/'verify.py'),'instrument'],check=True)
 code=Path('source/SP/code/rend2')
 p=code/'tr_backend.c';s=p.read_text();old='\tif (!srcFbo || !tr.quarterFbo[0] || !tr.renderDepthImage || !tr.volumetricLocalShader.program)';assert s.count(old)==1
 s=s.replace(old,'\tif(mode==3 && lamp && lamp->staticPromoteFixtureId==ri.Cvar_VariableIntegerValue("r_iflc14TargetId") && (ri.Cvar_VariableIntegerValue("r_iflc14TargetMask")&2))sourceWeight=0;\n'+old);p.write_text(s)
 p=code/'tr_shade.c';s=p.read_text();helper='''\nstatic float R_IFLC14_ReceiverGain(const dlight_t *dl) {
 return dl && dl->staticPromoteFixtureId==ri.Cvar_VariableIntegerValue("r_iflc14TargetId") && (ri.Cvar_VariableIntegerValue("r_iflc14TargetMask")&1) ? 0.0f : 1.0f;
}\n'''
 pos=s.index('\n',s.index('#include "tr_local.h"'))+1;s=s[:pos]+helper+s[pos:]
 for i in range(3):
  old=f'\t\tvector[{i}] = dl->color[{i}] * r_dlightIntensity->value;';assert s.count(old)==1;s=s.replace(old,old[:-1]+' * R_IFLC14_ReceiverGain(dl);')
 old='\t\tVectorScale(dl->color, r_dlightIntensity->value, vector);';assert s.count(old)==1;s=s.replace(old,'\t\tVectorScale(dl->color, r_dlightIntensity->value * R_IFLC14_ReceiverGain(dl), vector);');p.write_text(s)
 p=Path('source/SP/code/cgame/cg_view.c');s=p.read_text();anchor='"r_ssgi","r_volumetricSun"';assert s.count(anchor)==1;p.write_text(s.replace(anchor,'"r_iflc14TargetId","r_iflc14TargetMask",'+anchor))
else:
 s=(KIT/'probe.py').read_text()
 s=s.replace("[('baseline',1,1,1),('fire_off',0,1,1),('local_off',1,0,1),('both_volume_off',0,0,1),('all_off',0,0,0),('restored',1,1,1)]","[('baseline',1,1,1),('direct_zero',1,1,1),('volume_zero',1,1,1),('both_zero',1,1,1),('restored',1,1,1)]")
 s=s.replace("f'set r_volumetricLocal {local}'","'set r_volumetricLocalStrength 1',f'set r_iflc14TargetMask {dict(baseline=0,direct_zero=1,volume_zero=2,both_zero=3,restored=0)[variant]}'")
 s=s.replace("'set r_volumetricLocal 1','set r_volumetricFire 1'","'set r_volumetricLocal 1','set r_volumetricLocalStrength 1',f'set r_iflc14TargetId {targetId}','set r_iflc14TargetMask 0','set r_volumetricFire 1'")
 s=s.replace("eye+[10,yaw,0]","eye+[PITCHES[label],yaw,0]")
 ns={'__name__':'probe_module','__file__':str(KIT/'probe.py')};exec(compile(s,str(KIT/'probe.py'),'exec'),ns)
 targetId,target,behind,yaw={'factory':(300,[2168,-824,300],[2178,-684,336],-131),'escape1':(851,[-160,352,607],[-144,484,533],-109)}[a.map]
 ns['targetId']=targetId;data=ns['bsp'](a.retail.resolve(),a.map);world=ns['World'](data)
 front=[]
 for dist in (112,160,208):
  for step in range(16):
   angle=step*math.pi/8;eye=[target[0]+dist*math.cos(angle),target[1]+dist*math.sin(angle),target[2]-74]
   if world.solid(eye) or any(world.solid([eye[k]+off[k] for k in range(3)]) for off in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):continue
   hit=world.trace(eye,target)
   if hit and hit.get('fraction',0)<.90:continue
   if a.map=='escape1' and eye[1]>target[1]-32:continue
   front.append((dist+step*.1,eye))
 assert front,('No open-side camera',a.map)
 eye=min(front,key=lambda x:x[0])[1];delta=[target[i]-eye[i] for i in range(3)];frontyaw=math.degrees(math.atan2(delta[1],delta[0]));pitch=-math.degrees(math.atan2(delta[2],math.hypot(delta[0],delta[1])))
 ns['POSITIONS']=[('behind',behind,yaw),('front',eye,frontyaw)];ns['PITCHES']={'behind':10,'front':pitch}
 ns['capture'](a.retail.resolve(),a.out.resolve(),a.map)
 path=a.out/'PROBE_REPORT.json';r=json.loads(path.read_text());cv={}
 for line in r['lighting_lines']:
  m=re.search(r'PROOF_CVAR shot=(\d+) name=(\S+) value=(\S+)',line)
  if m:cv.setdefault(int(m[1]),{})[m[2]]=m[3]
 faults=[]
 for shot in r['shots']:
  values={'r_dwFireLightControl':0,'r_volumetricLocal':1,'r_volumetricLocalStrength':1,'r_dlightIntensity':1,'r_iflc14TargetId':targetId,'r_iflc14TargetMask':dict(baseline=0,direct_zero=1,volume_zero=2,both_zero=3,restored=0)[shot['variant']]}
  for key,value in values.items():
   if key not in cv.get(shot['id'],{}) or abs(float(cv[shot['id']][key])-value)>.00001:faults.append(f'{shot["name"]}: {key} mismatch')
 r.update(target_id=targetId,target_origin=target,front_camera=eye,actual_cvars=cv,faults=faults,isolation='Receiver RGB and volume weight only, no source/slot deletion',visual_status='PENDING_MANUAL_REVIEW')
 path.write_text(json.dumps(r,indent=2)+'\n');print('TARGET_CONTROL_FAULTS',faults,flush=True);assert not faults
