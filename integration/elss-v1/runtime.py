#!/usr/bin/env python3
"""Real-game ELSS V1 proof on three different electric fixture families."""
from pathlib import Path
import sys,math,struct,re,json,zipfile,tempfile,shutil,subprocess,os,signal,hashlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'testlab/scripts'))
from rc4_assault_camera import World
from PIL import Image
import numpy as np

TARGETS={
 'crypt1':{'emitter':11827,'body':11826,'label':'worklamp'},
 'boss1': {'emitter':7234, 'body':7232, 'label':'projector'},
 'escape1':{'emitter':13323,'body':13322,'label':'ceiling_lamp'},
}

def geometry(retail,mapname):
 data=None
 for p in sorted(retail.iterdir()):
  if p.suffix.lower()!='.pk3':continue
  with zipfile.ZipFile(p) as z:
   name=f'maps/{mapname}.bsp'
   for n in z.namelist():
    if n.lower()==name:data=z.read(n);break
  if data is not None:break
 assert data is not None,mapname
 return data

def parsed(data):
 def lump(i):o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
 verts=list(struct.iter_unpack('<10f4B',lump(10)));surfs=list(struct.iter_unpack('<12i12f2i',lump(13)))
 return verts,surfs

def bounds_center(verts,surfs,index):
 s=surfs[index];v=verts[s[3]:s[3]+s[4]];assert v
 lo=[min(x[k] for x in v) for k in range(3)];hi=[max(x[k] for x in v) for k in range(3)]
 center=[sum(x[k] for x in v)/len(v) for k in range(3)]
 return lo,hi,center

def angles(eye,target):
 d=[target[k]-eye[k] for k in range(3)]
 return [-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),math.degrees(math.atan2(d[1],d[0]))%360,0]

def camera_for(world,anchor):
 candidates=[]
 for di,distance in enumerate((160,224,112,288)):
  for step in range(16):
   theta=step*math.pi/8
   for dz in (-40,-64,-16,16):
    eye=[anchor[0]+distance*math.cos(theta),anchor[1]+distance*math.sin(theta),anchor[2]+dz]
    if world.solid(eye) or any(world.solid([eye[k]+o[k] for k in range(3)]) for o in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):continue
    hit=world.trace(eye,anchor)
    if hit and hit.get('fraction',0)<.98:continue
    candidates.append((di*100+abs(dz+40)+step*.01,eye))
 assert candidates,'no camera'
 return min(candidates,key=lambda x:x[0])[1]

def architecture_target(data,world,eye,anchor,body_index):
 verts,surfs=parsed(data);best=None
 for i,s in enumerate(surfs):
  if i==body_index:continue
  v=verts[s[3]:s[3]+s[4]]
  if not v:continue
  lo=[min(x[k] for x in v) for k in range(3)];hi=[max(x[k] for x in v) for k in range(3)]
  ext=sorted([hi[k]-lo[k] for k in range(3)],reverse=True)
  if ext[0]<128 or ext[1]<64:continue
  c=[sum(x[k] for x in v)/len(v) for k in range(3)]
  if math.dist(c,anchor)>260:continue
  hit=world.trace(eye,c)
  if hit and hit.get('fraction',0)<.97:continue
  score=math.dist(c,anchor)
  if best is None or score<best[0]:best=(score,i,c)
 return best

def capture(retail,out,mapname):
 out.mkdir(parents=True,exist_ok=True);data=geometry(retail,mapname);world=World(data);verts,surfs=parsed(data)
 t=TARGETS[mapname];elo,ehi,emitter=bounds_center(verts,surfs,t['emitter']);blo,bhi,body=bounds_center(verts,surfs,t['body'])
 eye=camera_for(world,emitter);arch=architecture_target(data,world,eye,emitter,t['body'])
 meta={'map':mapname,'bsp_sha256':hashlib.sha256(data).hexdigest(),'target':t,'emitter':emitter,'body':body,'eye':eye,'arch':arch}
 (out/'TARGET.json').write_text(json.dumps(meta,indent=2)+'\n')
 runtime=Path(tempfile.mkdtemp(prefix='elss-'+mapname+'-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
 build=Path('source/SP/build/release-linux-x86_64')
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
 for p in retail.iterdir():
  if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
 setup=['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_bloom 1','set r_bloomMode 2','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1','set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_volumetricFireV07Mode 2','set r_volumetricFireSourceMode 2','set r_volumetricFireMode 2','set r_ext_framebuffer_multisample 4','set r_cameraExposure 1','set r_autoExposure 0','set r_forceAutoExposure 0','set r_dwFireLightControl 0','set r_dwElectricLightControl 1','set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100','set con_notifytime -1']
 (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')
 def pv(target):return 'proofView '+' '.join(f'{x:.6f}' for x in eye+angles(eye,target))
 scene=[(emitter[k]+body[k])*.5 for k in range(3)]
 cmd=['set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_forceSunPause 1','god','notarget','wait 16',
      f'dw_el_test_enable {t["emitter"]} 1','wait 24',
      pv(emitter),'wait 16','dw_el_select','dw_el_info','dw_el_test_audit',
      pv(body),'wait 12','dw_el_self_pick','dw_el_info',
      pv(scene),'wait 20','set dw_proofFreeze 1','wait 12']
 shots=[]
 def shot(label):
  n=len(shots)+1;name=f'{mapname}_{t["label"]}_{label}'
  cmd.extend([f'echo ELSS_STATE {n} {label}','dw_el_info','dw_el_test_audit',f'set dw_proofShot {n}','wait 4',f'screenshot {name}','set dw_proofShot 0','wait 2']);shots.append((n,label,name))
 cmd+=['dw_el_set selfshadow 1','wait 24'];shot('on')
 cmd+=['dw_el_set selfshadow 0','wait 32'];shot('off')
 cmd+=['dw_el_save','wait 12'];shot('saved')
 cmd+=['dw_el_set selfshadow 1','wait 16','dw_el_reload','wait 32'];shot('reloaded')
 cmd+=['dw_el_set selfshadow auto','wait 24'];shot('auto')
 if arch:
  cmd += ['set dw_proofFreeze 0',pv(arch[2]),'wait 12','dw_el_self_pick','dw_el_info','echo ELSS_ARCH_TEST_DONE']
 cmd += ['dw_el_test_audit',f'dw_el_test_enable {t["emitter"]} 0','set dw_proofFreeze 0','echo ELSS_TEST_DONE','quit']
 (main/'TEST.cfg').write_text('\n'.join(cmd)+'\n')
 exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
 args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe','+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','TEST.cfg','+spdevmap',mapname]
 env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))};env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
 with (out/'stdout.log').open('w') as log:
  p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:rc=p.wait(timeout=1800)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
 texts=[]
 for i,p in enumerate(sorted(home.rglob('*console*.log'))):shutil.copy2(p,out/f'console-{i}.log');texts.append(p.read_text(errors='replace'))
 text='\n'.join(texts);states={};cur=None;images={};faults=[]
 for line in text.splitlines():
  m=re.search(r'ELSS_STATE (\d+) (\S+)',line)
  if m:cur=states.setdefault(int(m[1]),[])
  if cur is not None and line.startswith(('ELSS:','ELSS_TEST_')):cur.append(line)
 for n,label,name in shots:
  found=list(home.rglob(name+'.tga'))
  if len(found)==1:
   im=Image.open(found[0]).convert('RGB');im.save(out/(name+'.png'));images[label]=np.asarray(im).astype(np.int16)
  lines='\n'.join(states.get(n,[]))
  if label in ('off','saved','reloaded'):
   if not re.search(r'selfshadow=OFF\b',lines,re.I):faults.append(label+': OFF not active')
   if not re.search(r'(ownBodySurfaces|bodySurfaces|surfaces)=[1-9]\d*',lines,re.I):faults.append(label+': no body surfaces')
 if 'ELSS_TEST_DONE' not in text:faults.append('scenario incomplete')
 if not re.search(r'(bound|picked).*surface|manualSeeds=[1-8]',text,re.I):faults.append('manual body pick not observed')
 comps=[]
 for a,b in [('on','off'),('off','saved'),('saved','reloaded'),('off','auto')]:
  if a in images and b in images:
   d=np.abs(images[a]-images[b]);comps.append({'a':a,'b':b,'pixels':int(np.any(d>0,axis=2).sum()),'above2':int(np.any(d>2,axis=2).sum()),'mae':float(d.mean()),'max':int(d.max())})
 # Determine whether the deterministic test lamp actually received one of
 # the production shadow slots. If it did not, there is no own shadow to edit.
 enable=re.search(r'ELSS_TEST_ENABLE emitter='+str(t['emitter'])+r'[^\\n]*entity=(\\d+)',text)
 target_entity=enable.group(1) if enable else None
 target_slot=None
 if target_entity:
  for audit_line in text.splitlines():
   if audit_line.startswith('ELSS_TEST_LIGHT ') and ('key=fixture:'+target_entity+' ') in audit_line:
    mm=re.search(r'pointSlot=(-?\\d+)',audit_line)
    if mm:
     target_slot=int(mm.group(1));break
 selected_any=bool(re.search(r'ELSS: map='+re.escape(mapname)+r'[^\\n]*key=',text))
 no_slot_coverage=(target_slot is not None and target_slot<0 and not selected_any)
 if no_slot_coverage:
  faults=[x for x in faults if not any(k in x for k in ('OFF not active','no body surfaces','manual body pick','selfshadow has no visible response'))]
  if any(x['pixels'] for x in comps):faults.append('no-slot target changed pixels')
  if not re.search(r'saved and verified 0 lamp profiles',text):faults.append('no-slot target created a profile')
  coverage='NO_ACTIVE_SHADOW_SLOT_SAFE_NOOP'
 else:
  coverage='ACTIVE_SHADOW_MANUAL_SELF_SHADOW'
  onoff=next((x for x in comps if x['a']=='on' and x['b']=='off'),None)
  if not onoff or onoff['above2']<20:faults.append('selfshadow has no visible response')
  for aa,bb in [('off','saved'),('saved','reloaded')]:
   x=next((q for q in comps if q['a']==aa and q['b']==bb),None)
   if not x or x['pixels']!=0:faults.append(aa+'->'+bb+' not pixel exact')
 # slot must remain allocated and stable between ON/OFF when present
 def slot(label):
  lines='\\n'.join(states.get(next((n for n,l,_ in shots if l==label),-1),[]))
  m=re.search(r'(?:shadowSlot|pointSlot)=(-?\\d+)',lines);return int(m.group(1)) if m else None
 slots={x:slot(x) for x in ('on','off','saved','reloaded')}
 if slots['on'] is not None and slots['off'] is not None and slots['on']!=slots['off']:faults.append('shadow slot changed ON->OFF')
 diag=[l for l in text.splitlines() if l.startswith(('ELSS:','ELSS_TEST_','ELSS_STATE'))]
 report={'map':mapname,'label':t['label'],'coverage':coverage,'target_point_slot':target_slot,'exit':rc,'requested':len(shots),'captured':len(images),'comparisons':comps,'slots':slots,'arch_target':arch,'faults':faults,'diagnostics':diag}
 (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('map','label','exit','requested','captured','comparisons','slots','faults')},indent=2))
 # create simple comparison board
 if images:
  board=Image.new('RGB',(960,292*3),(20,20,24))
  from PIL import ImageDraw
  draw=ImageDraw.Draw(board)
  for i,(_,label,name) in enumerate(shots):
   if label not in images:continue
   im=Image.open(out/(name+'.png'));im.thumbnail((480,270));x=i%2*480;y=i//2*292;draw.text((x+8,y+3),label,fill='white');board.paste(im,(x,y+22))
  board.save(out/(mapname+'_'+t['label']+'_comparison.png'))
 assert rc==0 and len(images)==len(shots) and not faults,faults

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('retail',type=Path);p.add_argument('out',type=Path);p.add_argument('map',choices=TARGETS);a=p.parse_args();capture(a.retail.resolve(),a.out.resolve(),a.map)
