#!/usr/bin/env python3
"""Real-game causal controls. Images are evidence, not an automatic visual PASS."""
from pathlib import Path
import sys,math,struct,re,json,zipfile,tempfile,shutil,subprocess,os,signal,hashlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'testlab/scripts'))
from rc4_assault_camera import World

def angles(eye,target):
 d=[target[k]-eye[k] for k in range(3)];return [-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),math.degrees(math.atan2(d[1],d[0]))%360,0]
def geometry(retail,mapname):
 data=None
 for p in sorted(retail.iterdir()):
  if p.suffix.lower()!='.pk3':continue
  with zipfile.ZipFile(p) as z:
   for n in z.namelist():
    if n.lower()==f'maps/{mapname}.bsp':data=z.read(n)
 assert data is not None,mapname
 return data

def discover(data,mapname,kind,survey=''):
 world=World(data)
 def lump(i):o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
 verts=list(struct.iter_unpack('<10f4B',lump(10)));surfs=list(struct.iter_unpack('<12i12f2i',lump(13)))
 ids={'crypt1':[11827,11829],'boss1':[7234,7206],'escape1':[]}[mapname] if kind=='electric' else [10555,2758,2933]
 if mapname=='escape1':
  parsed=[dict(re.findall(r'(\w+)=([^\s]+)',l)) for l in survey.splitlines() if l.startswith('IFLC13_EMITTER ')]
  choices=[];start=next((list(map(float,e['origin'].split())) for e in world.entities if e.get('classname')=='info_player_start'),[0,0,0])
  for x in parsed:
   if any(s in x['shader'].lower() for s in ('flame','ember','red','switch','sign','button')):continue
   lo=list(map(float,x['lo'].split(',')));hi=list(map(float,x['hi'].split(',')));center=[(lo[i]+hi[i])/2 for i in range(3)]
   if max(hi[i]-lo[i] for i in range(3))>96:continue
   choices.append((math.dist(center,start),int(x['id']),x['shader'],center))
  for dist,i,s,c in sorted(choices):
   if any(math.dist(c,z[1])<80 for z in ids):continue
   ids.append((i,c))
   if len(ids)==3:break
  ids=[i for i,c in ids]
  print('ESCAPE_EMITTER_TARGETS',ids,flush=True)
 views=[]
 for index in ids:
  s=surfs[index];v=verts[s[3]:s[3]+s[4]];anchor=[sum(a[k] for a in v)/len(v) for k in range(3)]
  shader=world.shaders[s[0]][0].split(b'\0')[0].decode('latin1');candidates=[]
  for di,distance in enumerate((160,224,112,288)):
   for step in range(16):
    theta=step*math.pi/8
    for dz in (-40,-64,-16):
     eye=[anchor[0]+distance*math.cos(theta),anchor[1]+distance*math.sin(theta),anchor[2]+dz]
     if world.solid(eye) or any(world.solid([eye[k]+off[k] for k in range(3)]) for off in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):continue
     hit=world.trace(eye,anchor)
     if hit and hit.get('fraction',0)<.98:continue
     direction=[anchor[k]-eye[k] for k in range(3)];length=math.sqrt(sum(x*x for x in direction));back=[anchor[k]+direction[k]/length*128 for k in range(3)]
     bh=world.trace(anchor,back);score=di*100+abs(dz+40)+step*.01+(0 if bh else 40)
     candidates.append((score,eye))
  if not candidates:print('NO_CAMERA',index,shader,flush=True);continue
  eye=min(candidates,key=lambda x:x[0])[1];target=[anchor[0],anchor[1],anchor[2]-(22 if kind=='electric' else 35)]
  views.append({'name':f'{kind}_{index}_front','surface':index,'anchor':anchor,'eye':eye,'angles':angles(eye,target),'shader':shader})
  if kind=='fire' and index!=2933:
   ceiling=world.trace(anchor,[anchor[0],anchor[1],anchor[2]+256]);fh=ceiling.get('fraction',1) if ceiling else 1
   if fh<.95:
    z=anchor[2]+256*fh
    above=[]
    for dz in (56,80,112):
     for dist in (64,96,128):
      for step in range(16):
       a=step*math.pi/8;e=[anchor[0]+dist*math.cos(a),anchor[1]+dist*math.sin(a),z+dz]
       if world.solid(e) or any(world.solid([e[k]+o[k] for k in range(3)]) for o in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):continue
       floor=world.trace(e,[e[0],e[1],e[2]-256])
       if not floor or floor.get('fraction',1)>=.95:continue
       above.append((dz+dist*.1+step*.01,e))
    if above:
     eye=min(above,key=lambda x:x[0])[1];target=[anchor[0],anchor[1],z]
     views.append({'name':f'fire_{index}_above','surface':index,'anchor':anchor,'eye':eye,'angles':angles(eye,target),'shader':shader,'source_ceiling_z':z})
 return views

def capture(src,retail,out,kind,mapname):
 from PIL import Image,ImageDraw
 import numpy as np
 out.mkdir(parents=True,exist_ok=True);data=geometry(retail,mapname)
 runtime=Path(tempfile.mkdtemp(prefix='iflc13-'+mapname+'-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
 build=src/'SP/build/release-linux-x86_64'
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
 for p in retail.iterdir():
  if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
 setup=['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_bloom 1','set r_bloomMode 2','set r_dwCas 1','set r_dwA2C 1','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1','set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_volumetricFireV07Mode 2','set r_volumetricFireSourceMode 2','set r_volumetricFireMode 2','set r_volumetricFireMaxActive 8','set r_volumetricFireSamples 40','set r_ext_framebuffer_multisample 4','set r_cameraExposure 1','set r_autoExposure 0','set r_forceAutoExposure 0','set r_dwFireLightControl 0','set r_iflc13Electric 3','set r_iflc13DirectMask 0','set r_iflc13FireHardShadow 0','set r_iflc13SynthCapture 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100','set con_notifytime -1']
 (main/'IFLC13_SETUP.cfg').write_text('\n'.join(setup)+'\n');shutil.copy2(main/'IFLC13_SETUP.cfg',out/'IFLC13_SETUP.cfg')
 exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
 def run(scenario,label,timeout=1800):
  args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe','+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','IFLC13_SETUP.cfg','+vid_restart','+set','dw_proofScenario',scenario,'+spdevmap',mapname]
  env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))};env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
  with (out/(label+'_stdout.log')).open('w') as log:
   proc=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
   try:rc=proc.wait(timeout=timeout)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait();rc=124
  texts=[]
  for i,p in enumerate(sorted(home.rglob('*console*.log'))):shutil.copy2(p,out/f'{label}_console-{i}.log');texts.append(p.read_text(errors='replace'))
  return rc,'\n'.join(texts)
 survey=''
 if mapname=='escape1':
  (main/'IFLC13_SURVEY.cfg').write_text('god\nnotarget\nwait 15\ndw_fl13_survey\necho IFLC13_SURVEY_DONE\nquit\n')
  rc,survey=run('IFLC13_SURVEY.cfg','survey',240);assert rc==0 and 'IFLC13_SURVEY_DONE' in survey
 views=discover(data,mapname,kind,survey);assert views,'No valid comparison camera'
 (out/'VIEWS.json').write_text(json.dumps({'bsp_sha256':hashlib.sha256(data).hexdigest(),'views':views},indent=2)+'\n')
 cmd=['set con_notifytime -1','set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_autoExposure 0','set r_forceAutoExposure 0','set r_forceSunPause 1','god','notarget','wait 15','dw_fl13_survey'];shots=[]
 for v in views:
  cmd+=['set dw_proofShot 0','set dw_proofFreeze 0','set r_dwFireLightControl 0','set r_mapLightingLearn 1','set r_mapLightingLearnShow 0','set r_mapLightingProfileEnable 0','maplight_clear_memory confirm','maplight_zone_new IFLC13','proofView '+' '.join(f'{x:.6f}' for x in v['eye']+v['angles']),'wait 14','maplight_add_cluster','maplight_baked 0.2','maplight_status','set dw_proofFreeze 1']
  if kind=='electric':
   cmd+=[f'dw_fl13_electric {v["surface"]} 1','wait 8']
   matrix=[('v12',0,0,0,0,1,1,1,1,1),('world_only',1,0,0,0,1,1,1,1,1),('point_only',2,0,0,0,1,1,1,1,1),('both',3,0,0,0,1,1,1,1,1),('both_repeat',3,0,0,0,1,1,1,1,1),('v12_restore',0,0,0,0,1,1,1,1,1)]
  else:
   cmd+=['set r_dwFireLightControl 1',f'dw_fl13_target {v["surface"]}','dw_fl_set enabled 1','dw_fl_set direct 1.8','dw_fl_set radius 1.3','dw_fl_set volume 1.25','wait 8']
   matrix=[('baseline',3,0,0,0,1,1,1,1,1),('no_fire_volume',3,0,0,0,0,1,1,1,1),('no_fire_direct',3,1,0,0,1,1,1,1,1),('no_fire_both',3,1,0,0,0,1,1,1,1),('all_volume_off',3,0,0,0,0,0,0,1,1),('all_direct_off',3,2,0,0,1,1,1,1,1),('no_ssgi_bloom',3,0,0,0,1,1,1,0,0),('fire_hard_visibility',3,0,1,0,1,1,1,1,1),('fire_capture_twosided',3,0,0,1,1,1,1,1,1),('fire_capture_near',3,0,0,2,1,1,1,1,1),('fire_hard_and_capture',3,0,1,3,1,1,1,1,1),('restored',3,0,0,0,1,1,1,1,1)]
  for label,e,d,h,c,f,l,s,g,b in matrix:
   n=len(shots)+1;name=f'{mapname}_{v["name"]}_{label}'
   cmd+=['set dw_proofShot 0',f'dw_fl13_mode {e} {d} {h} {c}',f'set r_volumetricFire {f}',f'set r_volumetricLocal {l}',f'set r_volumetricSun {s}',f'set r_ssgi {g}',f'set r_bloom {b}','wait 12',f'echo IFLC13_STATE {n} {v["name"]} {label}','dw_fl13_audit','maplight_status',f'set dw_proofShot {n}','wait 3',f'screenshot {name}','wait 2']
   shots.append({'id':n,'name':name,'view':v['name'],'variant':label,'electric':e,'directMask':d,'hardFire':h,'capture':c,'fireVol':f,'localVol':l,'sunVol':s,'ssgi':g,'bloom':b})
  if kind=='electric':cmd+=[f'dw_fl13_electric {v["surface"]} 0']
  else:cmd+=['dw_fl_reset']
 cmd+=['set dw_proofShot 0','echo IFLC13_COMPLETE','set dw_proofFreeze 0','quit']
 (main/'IFLC13_TEST.cfg').write_text('\n'.join(cmd)+'\n');shutil.copy2(main/'IFLC13_TEST.cfg',out/'IFLC13_TEST.cfg')
 rc,text=run('IFLC13_TEST.cfg','runtime',2400)
 images={};states={};proof={};cvars={};current=None
 for line in text.splitlines():
  m=re.search(r'IFLC13_STATE (\d+) (\S+) (\S+)',line)
  if m:current=states.setdefault(int(m[1]),{'view':m[2],'variant':m[3],'lines':[]})
  if current is not None and line.startswith(('IFLC:','IFLC13_','MAPLIGHT')):current['lines'].append(line)
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
  if any(x is None for x in pv) or len({x['time'] for x in pv if x})!=1 or any(math.dist(x['eye'],v['eye'])>.01 for x in pv if x):faults.append(v['name']+': camera/time')
  for s in these:
   cv=cvars.get(s['id'],{})
   for k,x in {'r_iflc13Electric':s['electric'],'r_iflc13DirectMask':s['directMask'],'r_iflc13FireHardShadow':s['hardFire'],'r_iflc13SynthCapture':s['capture'],'r_dlightShadowMaxLights':3}.items():
    if cv.get(k)!=str(x):faults.append(s['name']+': '+k)
  base=these[0]['name']
  for s in these[1:]:
   if base not in images or s['name'] not in images:continue
   delta=np.abs(images[base]-images[s['name']]);comparisons.append({'view':v['name'],'a':these[0]['variant'],'b':s['variant'],'changed_pixels':int(np.any(delta>0,axis=2).sum()),'pixels_above_2':int(np.any(delta>2,axis=2).sum()),'mean_abs_rgb':float(delta.mean()),'max_abs_rgb':int(delta.max())})
  board=Image.new('RGB',(960,292*math.ceil(len(these)/2)),(20,20,24));draw=ImageDraw.Draw(board)
  for j,s in enumerate(these):
   if s['name'] not in images:continue
   im=Image.open(out/(s['name']+'.png'));im.thumbnail((480,270));x=j%2*480;y=j//2*292;draw.text((x+8,y+3),s['variant'],fill='white');board.paste(im,(x,y+22))
  board.save(out/(v['name']+'_comparison.png'))
 report={'base_run':41772470237,'map':mapname,'kind':kind,'exit':rc,'ready':'PROOF_READY' in text,'complete':'IFLC13_COMPLETE' in text,'requested':len(shots),'captured':len(images),'faults':faults,'comparisons':comparisons,'shots':shots,'states':states,'proof':proof,'cvars':cvars,'catalog':[l for l in text.splitlines() if l.startswith(('IFLC13_EMITTER ','IFLC13_ELECTRIC_TARGET','IFLC13_TARGET','IFLC13_VOLUME'))],'visual_status':'PENDING_REVIEW','fire_controls':'Causal hypotheses only, no production fire fix yet; direct mask changes receiver uniforms, not actual light structures.'}
 (out/'IFLC13_RUNTIME_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ('map','kind','exit','ready','complete','requested','captured','faults')},indent=2),flush=True)
 assert rc==0 and report['ready'] and report['complete'] and len(images)==len(shots) and not faults,'Incomplete or invalid causal run'
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('retail',type=Path);p.add_argument('output',type=Path);p.add_argument('kind',choices=['electric','fire']);p.add_argument('map',choices=['crypt1','boss1','escape1']);a=p.parse_args();capture(a.source.resolve(),a.retail.resolve(),a.output.resolve(),a.kind,a.map)
