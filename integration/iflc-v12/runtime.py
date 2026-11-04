#!/usr/bin/env python3
"""Exact Crypt1 report, regressions, Castle native-lantern causal controls."""
from pathlib import Path
import sys,math,struct,re,json,zipfile,tempfile,shutil,subprocess,os,signal,hashlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'testlab/scripts'))
from rc4_assault_camera import World

def angles(eye,target):
 d=[target[k]-eye[k] for k in range(3)]
 return [-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),math.degrees(math.atan2(d[1],d[0]))%360,0]

def geometry(retail,mapname):
 data=None
 for p in sorted(retail.iterdir()):
  if p.suffix.lower()!='.pk3':continue
  with zipfile.ZipFile(p) as z:
   for n in z.namelist():
    if n.lower()==f'maps/{mapname}.bsp':data=z.read(n)
 assert data is not None,mapname
 return data

def discover(data,mapname):
 world=World(data)
 def lump(i):
  o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
 verts=list(struct.iter_unpack('<10f4B',lump(10)));surfs=list(struct.iter_unpack('<12i12f2i',lump(13)))
 targets={'crypt1':[2933,2929,2935,2992],'crypt2':[2368],'castle':[7730]}[mapname]
 views=[]
 for index in targets:
  s=surfs[index];v=verts[s[3]:s[3]+s[4]];anchor=[sum(a[k] for a in v)/len(v) for k in range(3)]
  shader=world.shaders[s[0]][0].split(b'\0')[0].decode('latin1');assert 'flame' in shader,(mapname,index,shader)
  candidates=[];distances=(320,384,256) if mapname=='castle' else (160,192,128);dz=-164 if mapname=='castle' else -58
  for di,distance in enumerate(distances):
   for step in range(16):
    theta=step*math.pi/8;eye=[anchor[0]+distance*math.cos(theta),anchor[1]+distance*math.sin(theta),anchor[2]+dz]
    if world.solid(eye) or any(world.solid([eye[k]+off[k] for k in range(3)]) for off in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):continue
    hit=world.trace(eye,anchor)
    if hit and hit.get('fraction',0)<.985:continue
    score=di*100+min(step,16-step);low_target=[anchor[0],anchor[1],anchor[2]-(80 if mapname=='castle' else 42)]
    candidates.append((score,{'surface':index,'anchor':anchor,'shader':shader,'eye':eye,'select_angles':angles(eye,anchor),'angles':angles(eye,low_target),'name':f'{mapname}_source_{index}'}))
  assert candidates,('No unobstructed camera',mapname,index)
  view=min(candidates,key=lambda x:x[0])[1];d=[view['eye'][k]-anchor[k] for k in range(3)];length=math.sqrt(sum(v*v for v in d));probe=[anchor[k]+d[k]*32/length for k in range(3)]
  view['probe']=view['eye'] if world.solid(probe) else probe;views.append(view)
 return views

def capture(source,retail,out,mapname):
 import numpy as np
 from PIL import Image,ImageDraw
 out.mkdir(parents=True,exist_ok=True);data=geometry(retail,mapname);views=discover(data,mapname)
 (out/'CAMERAS.json').write_text(json.dumps({'map':mapname,'bsp_sha256':hashlib.sha256(data).hexdigest(),'views':views},indent=2)+'\n')
 runtime=Path(tempfile.mkdtemp(prefix='iflc12-'+mapname+'-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
 build=source/'SP/build/release-linux-x86_64'
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
 for p in retail.iterdir():
  if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
 cmd=['set con_notifytime -1','set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_autoExposure 0','set r_forceAutoExposure 0','set r_forceSunPause 1','god','notarget','wait 16','dw_fl12_mode 0 0','dw_fl12_audit catalog'];shots=[]
 def viewcmd(v,aim=False,probe=False):return 'proofView '+' '.join(f'{x:.6f}' for x in (v['probe'] if probe else v['eye'])+(v['select_angles'] if aim else v['angles']))
 def shot(v,label,legacy=0,mask=0,baked=.2):
  i=len(shots)+1;name=v['name']+'_'+label
  cmd.extend(['set dw_proofShot 0',f'echo IFLC12_STATE {i} {v["name"]} {label}','dw_fl_info','dw_fl12_audit','maplight_list',f'set dw_proofShot {i}','wait 5',f'screenshot {name}','wait 2'])
  shots.append({'id':i,'view':v['name'],'surface':v['surface'],'name':name,'variant':label,'legacy':legacy,'castle_mask':mask,'baked':baked})
 for v in views:
  cmd.extend(['set dw_proofShot 0','set dw_proofFreeze 0','set r_dwFireLightControl 0','dw_fl12_mode 0 0','set r_mapLightingLearn 1','set r_mapLightingLearnShow 0','set r_mapLightingProfileEnable 0','maplight_clear_memory confirm','maplight_zone_new IFLC12',viewcmd(v,True,True),'wait 8','maplight_add_cluster',viewcmd(v,True),'wait 22','maplight_add_cluster','maplight_baked 0.2','dw_fl_select','dw_fl_next','wait 2',viewcmd(v),'wait 16','set dw_proofFreeze 1','wait 10'])
  shot(v,'baseline_off')
  if mapname!='castle':
   cmd.extend(['set r_dwFireLightControl 1','dw_fl_set enabled 1','dw_fl_set direct 1.8','dw_fl_set radius 1.3','dw_fl_set volume 1.25','dw_fl_set color 1 .58 .23','dw_fl12_mode 1 0','wait 16']);shot(v,'v11_shadow',legacy=1)
   cmd.extend(['dw_fl12_mode 0 0','wait 16']);shot(v,'v12_shadow')
   cmd.extend(['wait 8']);shot(v,'v12_repeat')
   cmd.extend(['dw_fl12_mode 1 0','wait 16']);shot(v,'v11_repeat',legacy=1)
   cmd.extend(['dw_fl12_mode 0 0','dw_fl_save','wait 12']);shot(v,'saved')
   cmd.extend(['dw_fl_set direct .4','dw_fl_reload','wait 12']);shot(v,'reloaded')
   cmd.extend(['set r_dwFireLightControl 0','wait 12']);shot(v,'master_off')
   cmd.extend(['dw_fl_reset','dw_fl_save','wait 4'])
  else:
   cmd.extend(['dw_fl12_mode 1 0','wait 16']);shot(v,'v11_native',legacy=1)
   cmd.extend(['dw_fl12_mode 0 0','wait 16']);shot(v,'v12_native')
   for mask,label in ((1,'diagnostic_no_bottom'),(2,'diagnostic_no_bars'),(4,'diagnostic_no_roof'),(7,'diagnostic_no_cage'),(8,'diagnostic_native_direct_zero')):
    cmd.extend([f'dw_fl12_mode 0 {mask}','wait 16']);shot(v,label,mask=mask)
   cmd.extend(['dw_fl12_mode 0 0','wait 16']);shot(v,'restored')
   cmd.extend(['maplight_baked 1','wait 12']);shot(v,'native_baked100',baked=1)
   cmd.extend(['dw_fl12_mode 0 1','wait 16']);shot(v,'no_bottom_baked100',mask=1,baked=1)
   cmd.extend(['dw_fl12_mode 0 0','maplight_baked .2','wait 16']);shot(v,'final_restore')
 cmd.extend(['dw_fl12_mode 0 0','set dw_proofFreeze 0','echo IFLC12_COMPLETE','quit'])
 (main/'IFLC12_TEST.cfg').write_text('\n'.join(cmd)+'\n');shutil.copy2(main/'IFLC12_TEST.cfg',out/'IFLC12_TEST.cfg')
 setup=['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_bloom 1','set r_bloomMode 2','set r_dwCas 1','set r_dwA2C 1','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1','set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_volumetricFireV07Mode 2','set r_volumetricFireSourceMode 2','set r_volumetricFireMode 2','set r_volumetricFireMaxActive 8','set r_volumetricFireSamples 40','set r_ext_framebuffer_multisample 4','set r_cameraExposure 1','set r_autoExposure 0','set r_forceAutoExposure 0','set r_dwFireLightControl 0','set r_iflc12Legacy 0','set r_iflc12CastleMask 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100','set con_notifytime -1']
 (main/'IFLC12_SETUP.cfg').write_text('\n'.join(setup)+'\n');shutil.copy2(main/'IFLC12_SETUP.cfg',out/'IFLC12_SETUP.cfg')
 exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
 args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe','+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','IFLC12_SETUP.cfg','+vid_restart','+set','dw_proofScenario','IFLC12_TEST.cfg','+spdevmap',mapname]
 env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))};env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
 with (out/'stdout.log').open('w') as log:
  proc=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:rc=proc.wait(timeout=1800)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait();rc=124
 texts=[]
 for i,p in enumerate(sorted(home.rglob('*console*.log'))):shutil.copy2(p,out/f'console-{i}.log');texts.append(p.read_text(errors='replace'))
 text='\n'.join(texts);states={};current=None;proof={};cvars={};images={}
 for line in text.splitlines():
  m=re.search(r'IFLC12_STATE (\d+) (\S+) (\S+)',line)
  if m:current=states.setdefault(int(m[1]),{'view':m[2],'variant':m[3],'lines':[],'lights':[]})
  if current is not None and line.startswith(('IFLC:','IFLC12_','MAPLIGHT')):current['lines'].append(line)
  if current is not None and line.startswith('IFLC12_LIGHT '):current['lights'].append(dict(re.findall(r'(\w+)=([^\s]+)',line)))
  m=re.search(r'PROOF_VIEW shot=(\d+) time=(\d+) eye=([\d.,-]+) forward=([\d.,-]+)',line)
  if m:proof[int(m[1])]={'time':int(m[2]),'eye':list(map(float,m[3].split(','))),'forward':list(map(float,m[4].split(',')))};current=None
  m=re.search(r'PROOF_CVAR shot=(\d+) name=(\S+) value=(\S+)',line)
  if m:cvars.setdefault(int(m[1]),{})[m[2]]=m[3]
 for s in shots:
  found=list(home.rglob(s['name']+'.tga'))
  if len(found)==1:
   im=Image.open(found[0]).convert('RGB');im.save(out/(s['name']+'.png'));images[s['name']]=np.asarray(im).astype(np.int16)
 faults=[];comparisons=[]
 for v in views:
  these=[s for s in shots if s['view']==v['name']];pv=[proof.get(s['id']) for s in these]
  if any(x is None for x in pv) or len({x['time'] for x in pv if x})!=1 or any(math.dist(x['eye'],v['eye'])>.01 for x in pv if x):faults.append(v['name']+': camera/time proof')
  for s in these:
   state=states.get(s['id'],{});lines='\n'.join(state.get('lines',[]));cv=cvars.get(s['id'],{})
   if cv.get('r_iflc12Legacy')!=str(s['legacy']) or cv.get('r_iflc12CastleMask')!=str(s['castle_mask']) or cv.get('r_dlightShadowMaxLights')!='3':faults.append(s['name']+': cvar proof')
   if mapname=='crypt1' and v['surface']==2933:
    if 'key=surface:2933:2cbb32f6:41205293' not in lines:faults.append(s['name']+': wrong torch selected')
    expected=0 if s['legacy'] else 13
    if f'fixtureSelfCasters={expected} ' not in lines:faults.append(s['name']+': wrong classified caster count')
    if s['variant'] in ('v12_shadow','saved','reloaded'):
     hit=re.search(r'submittedExclusions=([^\n]+)',lines);pairs=dict((int(a),int(b)) for a,b in re.findall(r'(\d+):(\d+)',hit[1] if hit else ''))
     if set(pairs)!=set(range(2543,2556)) or not all(pairs.values()):faults.append(s['name']+': actual caster exclusion not observed')
   if mapname=='castle' and not any(x.get('native')=='349' for x in state.get('lights',[])):faults.append(s['name']+': native lantern draw not present')
   for light in state.get('lights',[]):
    if light.get('optin')=='1' and light.get('policy')!=light.get('cachePolicy'):faults.append(s['name']+': stale world capture policy')
  pairs=[('v11_shadow','v12_shadow'),('v11_shadow','v11_repeat'),('v12_shadow','v12_repeat'),('saved','reloaded'),('baseline_off','master_off')] if mapname!='castle' else [('v11_native','v12_native'),('v12_native','diagnostic_no_bottom'),('v12_native','diagnostic_no_bars'),('v12_native','diagnostic_no_roof'),('v12_native','diagnostic_no_cage'),('v12_native','diagnostic_native_direct_zero'),('v12_native','restored'),('v12_native','final_restore'),('native_baked100','no_bottom_baked100')]
  for aa,bb in pairs:
   na=v['name']+'_'+aa;nb=v['name']+'_'+bb
   if na not in images or nb not in images:continue
   delta=np.abs(images[na]-images[nb]);comparisons.append({'view':v['name'],'a':aa,'b':bb,'changed_pixels':int(np.any(delta>0,axis=2).sum()),'pixels_above_2':int(np.any(delta>2,axis=2).sum()),'mean_abs_rgb':float(delta.mean()),'max_abs_rgb':int(delta.max())})
  board=Image.new('RGB',(960,292*math.ceil(len(these)/2)),(20,20,24));draw=ImageDraw.Draw(board)
  for j,s in enumerate(these):
   if s['name'] not in images:continue
   im=Image.open(out/(s['name']+'.png'));im.thumbnail((480,270));x=j%2*480;y=j//2*292;draw.text((x+8,y+3),s['variant'],fill='white');board.paste(im,(x,y+22))
  board.save(out/(v['name']+'_comparison.png'))
 if mapname=='crypt1':
  response=next((x for x in comparisons if x['view']=='crypt1_source_2933' and x['a']=='v11_shadow' and x['b']=='v12_shadow'),None)
  if not response or response['pixels_above_2']<100:faults.append('No measurable response on the reported torch')
 report={'base_run':41758201175,'map':mapname,'exit':rc,'ready':'PROOF_READY' in text,'complete':'IFLC12_COMPLETE' in text,'requested':len(shots),'captured':len(images),'faults':faults,'comparisons':comparisons,'shots':shots,'states':states,'proof':proof,'cvars':cvars,'owner_catalog':[l for l in text.splitlines() if l.startswith('IFLC12_OWNER ')],'visual_acceptance':'PENDING_MANUAL_REVIEW','limits':'Linux Mesa native test harness; legacy mode disables only new fallback; Castle masks are causal diagnostics, not a production fix.'}
 (out/'IFLC12_RUNTIME_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ('map','exit','ready','complete','requested','captured','faults')},indent=2),flush=True)
 assert rc==0 and report['ready'] and report['complete'] and len(images)==len(shots) and not faults,'Incomplete or unverified experiment'

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('retail',type=Path);p.add_argument('output',type=Path);p.add_argument('map',choices=['crypt1','crypt2','castle']);a=p.parse_args();capture(a.source.resolve(),a.retail.resolve(),a.output.resolve(),a.map)
