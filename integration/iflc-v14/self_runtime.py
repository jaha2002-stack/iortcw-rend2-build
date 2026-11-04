#!/usr/bin/env python3
"""Actual commands, save/reload, visible body and native/synthetic self-shadow.
Only camera instrumentation; no force-disable visibility or test-only selector.
"""
from pathlib import Path
import argparse,importlib.util,sys,tempfile,shutil,subprocess,os,signal,json,re,math
KIT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('runtime12',KIT.parent/'iflc-v12/runtime.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
def capture(retail,out,mapname):
 from PIL import Image,ImageDraw
 import numpy as np
 out.mkdir(parents=True,exist_ok=True);data=old.geometry(retail,mapname);views=old.discover(data,mapname)
 if mapname=='crypt1':views=[v for v in views if v['surface'] in (2933,2992)]
 (out/'VIEWS.json').write_text(json.dumps(views,indent=2)+'\n')
 runtime=Path(tempfile.mkdtemp(prefix='self14-'+mapname+'-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
 build=Path('source/SP/build/release-linux-x86_64')
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
 for p in retail.iterdir():
  if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
 setup=['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_bloom 1','set r_bloomMode 2','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1','set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_volumetricFireV07Mode 2','set r_volumetricFireSourceMode 2','set r_volumetricFireMode 2','set r_volumetricFireMaxActive 8','set r_volumetricFireSamples 32','set r_ext_framebuffer_multisample 4','set r_cameraExposure 1','set r_autoExposure 0','set r_forceAutoExposure 0','set r_dwFireLightControl 0','set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100','set con_notifytime -1']
 (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n');shutil.copy2(main/'SETUP.cfg',out/'SETUP.cfg')
 cmd=['set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_forceSunPause 1','god','notarget','wait 16'];shots=[]
 def view(v,aim=False):return 'proofView '+' '.join(map(str,v['eye']+(v['select_angles'] if aim else v['angles'])))
 def shot(v,label):
  n=len(shots)+1;name=v['name']+'_'+label
  cmd.extend(['set dw_proofShot 0',f'echo IFLC14_SELF {n} {name}','dw_fl_info',f'set dw_proofShot {n}','wait 4',f'screenshot {name}','wait 2']);shots.append(dict(id=n,name=name,surface=v['surface'],view=v['name'],variant=label,eye=v['eye']))
 for v in views:
  cmd+=['set dw_proofShot 0','set dw_proofFreeze 0','set r_dwFireLightControl 0',view(v,True),'wait 20','dw_fl_select','dw_fl_next',view(v),'wait 24','set dw_proofFreeze 1','wait 12']
  shot(v,'master_off_before')
  cmd+=['set r_dwFireLightControl 1','dw_fl_set selfshadow auto']
  if mapname!='castle':cmd+=['dw_fl_set enabled 1','dw_fl_set direct 1.8','dw_fl_set radius 1.3','dw_fl_set volume 1.25']
  cmd+=['wait 32'];shot(v,'auto')
  cmd+=['dw_fl_set selfshadow 1','wait 32'];shot(v,'on')
  cmd+=['dw_fl_set selfshadow 0','wait 48'];shot(v,'off')
  cmd+=['dw_fl_save','wait 16'];shot(v,'saved')
  cmd+=['dw_fl_set selfshadow 1','wait 24','dw_fl_reload','wait 48'];shot(v,'reloaded')
  cmd+=['dw_fl_set selfshadow 1','wait 32'];shot(v,'on_restored')
  cmd+=['dw_fl_set selfshadow auto','wait 32'];shot(v,'auto_restored')
  cmd+=['set r_dwFireLightControl 0','wait 32'];shot(v,'master_off_after')
  cmd+=['dw_fl_reset','dw_fl_save','wait 8']
 cmd+=['echo IFLC14_SELF_DONE','set dw_proofFreeze 0','quit']
 (main/'SELF.cfg').write_text('\n'.join(cmd)+'\n');shutil.copy2(main/'SELF.cfg',out/'SELF.cfg')
 exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
 args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe','+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','SELF.cfg','+spdevmap',mapname]
 env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))};env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
 with (out/'stdout.log').open('w') as log:
  p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:rc=p.wait(timeout=1800)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
 texts=[]
 for i,p in enumerate(sorted(home.rglob('*console*.log'))):shutil.copy2(p,out/f'console-{i}.log');texts.append(p.read_text(errors='replace'))
 text='\n'.join(texts);states={};proof={};current=None;images={};faults=[]
 for line in text.splitlines():
  m=re.search(r'IFLC14_SELF (\d+) (\S+)',line)
  if m:current=states.setdefault(int(m[1]),[])
  if current is not None and line.startswith('IFLC:'):current.append(line)
  m=re.search(r'PROOF_VIEW shot=(\d+) time=(\d+) eye=([\d.,-]+)',line)
  if m:proof[int(m[1])]=dict(time=int(m[2]),eye=list(map(float,m[3].split(','))));current=None
 for shot in shots:
  found=list(home.rglob(shot['name']+'.tga'))
  if len(found)==1:
   im=Image.open(found[0]).convert('RGB');im.save(out/(shot['name']+'.png'));images[shot['name']]=np.array(im).astype('int16')
  lines='\n'.join(states.get(shot['id'],[]))
  if shot['variant'] in ('off','saved','reloaded'):
   if not re.search(r'selfshadow=OFF\b',lines,re.I) or not re.search(r'ownBodySurfaces=[1-9]\d*',lines):faults.append(shot['name']+': own body OFF not confirmed')
  pv=proof.get(shot['id'])
  if not pv or math.dist(pv['eye'],shot['eye'])>.01:faults.append(shot['name']+': camera')
 comparisons=[]
 for v in views:
  these=[s for s in shots if s['view']==v['name']]
  if len({proof[s['id']]['time'] for s in these if s['id'] in proof})!=1:faults.append(v['name']+': time')
  for aa,bb in [('on','off'),('on','on_restored'),('off','saved'),('saved','reloaded'),('auto','auto_restored'),('master_off_before','master_off_after')]:
   if v['name']+'_'+aa not in images or v['name']+'_'+bb not in images:continue
   d=np.abs(images[v['name']+'_'+aa]-images[v['name']+'_'+bb]);comparisons.append(dict(view=v['name'],a=aa,b=bb,pixels=int(np.any(d>0,axis=2).sum()),above2=int(np.any(d>2,axis=2).sum()),mae=float(d.mean()),max=int(d.max())))
  board=Image.new('RGB',(960,292*math.ceil(len(these)/2)),(20,20,24));draw=ImageDraw.Draw(board)
  for i,s in enumerate(these):
   if s['name'] not in images:continue
   im=Image.open(out/(s['name']+'.png'));im.thumbnail((480,270));x=i%2*480;y=i//2*292;draw.text((x+8,y+3),s['variant'],fill='white');board.paste(im,(x,y+22))
  board.save(out/(v['name']+'_self_comparison.png'))
 report=dict(map=mapname,exit=rc,complete='IFLC14_SELF_DONE' in text,requested=len(shots),captured=len(images),shots=shots,states=states,proof=proof,comparisons=comparisons,faults=faults,visual_status='PENDING_MANUAL_REVIEW')
 (out/'SELF_REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('map','exit','complete','requested','captured','faults')},indent=2),flush=True)
 assert rc==0 and report['complete'] and len(images)==len(shots) and not faults
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('retail',type=Path);p.add_argument('output',type=Path);p.add_argument('map',choices=['crypt1','crypt2','castle']);a=p.parse_args();capture(a.retail.resolve(),a.output.resolve(),a.map)
