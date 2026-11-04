#!/usr/bin/env python3
"""Corrected read-only native probe: nonlatched Local strength, asserted states.
Preserve original first-probe evidence: r_volumetricLocal is LATCH and those
old local_off labels did NOT establish suppression of its actual contribution.
"""
from pathlib import Path
import argparse,json,re,sys
KIT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('mode',choices=['instrument','capture']);p.add_argument('--retail',type=Path);p.add_argument('--map');p.add_argument('--out',type=Path);a=p.parse_args()
s=(KIT/'probe.py').read_text()
s=s.replace("f'set r_volumetricLocal {local}'","f'set r_volumetricLocalStrength {local}'")
s=s.replace("'set r_volumetricLocal 1','set r_volumetricFire 1'","'set r_volumetricLocal 1','set r_volumetricLocalStrength 1','set r_volumetricFire 1'")
s=s.replace("label=label,variant=variant,eye=eye,yaw=yaw)","label=label,variant=variant,eye=eye,yaw=yaw,fire=fire,localStrength=local,direct=direct)")
ns={'__name__':'probe_module','__file__':str(KIT/'probe.py')};exec(compile(s,str(KIT/'probe.py'),'exec'),ns)
if a.mode=='instrument':
 ns['instrument']()
 # All controls must be observed after latch processing, not merely echoed.
 p=Path('source/SP/code/cgame/cg_view.c');s=p.read_text()
 assert 'r_volumetricLocalStrength' in s
 # Correct backend ownership evidence; frontend secondary views may have no DLight.
 p=Path('source/SP/code/rend2/tr_backend.c');s=p.read_text();anchor='\tGLSL_BindProgram(&tr.volumetricLocalShader);';assert s.count(anchor)==1
 extra=r'''
 {static int last=-1;int shot=ri.Cvar_VariableIntegerValue("dw_proofShot");
  if(shot>0&&shot!=last){int i;last=shot;
   for(i=0;i<backEnd.refdef.num_dlights&&i<MAX_DLIGHTS;++i){const dlight_t *d=&backEnd.refdef.dlights[i];
    ri.Printf(PRINT_ALL,"IFLC14_BACKEND shot=%d i=%d origin=%.2f,%.2f,%.2f native=%d fixture=%d class=%d world=%d worldSlot=%d point=%d rgb=%.4f,%.4f,%.4f optin=%d\n",shot,i,d->origin[0],d->origin[1],d->origin[2],d->nativeAuthoredDlight,d->staticPromoteFixtureId,d->shadowSourceClass,d->worldOcclusion,(int)backEnd.refdef.dlightWorldSlot[i],(int)backEnd.refdef.dlightShadowSlot[i],d->color[0],d->color[1],d->color[2],d->iflcOptIn);
   }
  }}
'''
 p.write_text(s.replace(anchor,extra+anchor))
else:
 wanted={'crypt1':{'A'},'factory':{'B','C'},'escape1':{'D'}}[a.map]
 ns['POSITIONS']=[v for v in ns['POSITIONS'] if v[0] in wanted]
 ns['capture'](a.retail.resolve(),a.out.resolve(),a.map)
 path=a.out/'PROBE_REPORT.json';r=json.loads(path.read_text());cv={};proof={}
 for l in r['lighting_lines']:
  m=re.search(r'PROOF_CVAR shot=(\d+) name=(\S+) value=(\S+)',l)
  if m:cv.setdefault(int(m[1]),{})[m[2]]=m[3]
  m=re.search(r'PROOF_VIEW shot=(\d+) time=(\d+) eye=([\d.,-]+)',l)
  if m:proof[int(m[1])]={'time':int(m[2]),'eye':list(map(float,m[3].split(',')))}
 faults=[]
 for shot in r['shots']:
  expected={'r_dwFireLightControl':0,'r_volumetricLocal':1,'r_volumetricLocalStrength':shot['localStrength'],'r_volumetricFire':shot['fire'],'r_dlightIntensity':shot['direct'],'r_dlightWorldContainment':2,'r_externalGLSL':0}
  for key,value in expected.items():
   if key not in cv.get(shot['id'],{}) or abs(float(cv[shot['id']][key])-value)>.00001:faults.append(f'{shot["name"]}: {key} actual={cv.get(shot["id"],{}).get(key)} expected={value}')
  point=proof.get(shot['id'])
  if not point or any(abs(point['eye'][i]-shot['eye'][i])>.01 for i in range(3)):faults.append(shot['name']+': camera')
 for label in wanted:
  times={proof[x['id']]['time'] for x in r['shots'] if x['label']==label and x['id'] in proof}
  if len(times)!=1:faults.append(label+': time mismatch')
 r['actual_cvars']=cv;r['proof']=proof;r['faults']=faults;r['local_off_method']='r_volumetricLocalStrength 0, master remains 1';r['visual_status']='PENDING_MANUAL_REVIEW'
 path.write_text(json.dumps(r,indent=2)+'\n');print('IFLC14_ACTUAL_STATE_FAULTS',faults,flush=True);assert not faults
