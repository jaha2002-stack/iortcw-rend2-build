#!/usr/bin/env python3
"""Read-only coordinate and vanilla-source reproduction. No deployable binary.
Coordinates are user observations, not correction rules. Map association is
verified with BSP geometry and actual images, not inferred from text ordering.
"""
from pathlib import Path
import argparse,hashlib,io,json,math,os,re,shutil,signal,struct,subprocess,sys,tarfile,tempfile,zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'testlab/scripts'))
from rc4_assault_camera import World
import rc4_requested_views as camera
POSITIONS=[('A',[52,-377,58],-2),('B',[1779,-652,186],32),('C',[2178,-684,336],-131),('D',[-144,484,533],-109)]

def prepare():
 ev=Path('evidence');ev.mkdir(exist_ok=True);a=ev/'source13.zip'
 with a.open('wb') as f:subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13303624902/zip'],stdout=f,check=True)
 assert hashlib.sha256(a.read_bytes()).hexdigest()=='9b27f9ec4d4c99339dd2ece895948ac0c19edd8d6398fa72668da53b6dc8e6d4'
 with zipfile.ZipFile(a) as z:z.extractall(ev/'input')
 src=Path('source');subprocess.run(['git','init',str(src)],check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['git','-C',str(src),'fetch','--depth=1','https://github.com/iortcw/iortcw','438e7d413b5f7277187c35b032eb0ef9093ae778'],check=True)
 subprocess.run(['git','-C',str(src),'checkout','--detach','FETCH_HEAD'],check=True,stdout=subprocess.DEVNULL)
 shutil.rmtree(src/'SP/code')
 with tarfile.open(next((ev/'input').rglob('IFLC_V13_EXACT_SOURCE.tar.gz'))) as t:t.extractall(src,filter='data')
 m=json.loads(next((ev/'input').rglob('IFLC13_RELEASE_SOURCE_SHA256.json')).read_text())
 actual={p.relative_to(src).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (src/'SP/code').rglob('*') if p.is_file()}
 assert actual==m and len(actual)==1650
 (ev/'IFLC14_BASE_SHA256.json').write_text(json.dumps(actual,indent=2)+'\n')
 print('EXACT_V13_SOURCE_VERIFIED_1650')

def instrument():
 src=Path('source');camera.instrument(src);code=src/'SP/code/rend2'
 p=code/'tr_backend.c';s=p.read_text();anchor='\tGLSL_BindProgram(&tr.volumetricLocalShader);';assert s.count(anchor)==1
 s=s.replace(anchor,r'''
 {static int lastShot=-1, frame=-1;int shot=ri.Cvar_VariableIntegerValue("dw_proofShot");
  if(shot>0){if(shot!=lastShot){lastShot=shot;frame=tr.frameCount;}
   if(frame==tr.frameCount)ri.Printf(PRINT_ALL,"IFLC14_VOLUME shot=%d mode=%d origin=%.3f,%.3f,%.3f radius=%.3f plume=%.3f,%.3f,%.3f shadow=%d override=%d slot=%d worldGate=%.6f native=%d fixture=%d optin=%d weight=%.4f gain=%.4f\n",shot,mode,source[0],source[1],source[2],source[3],volumeInfo[0],volumeInfo[1],volumeInfo[2],useShadow,shadowCubemapOverride!=NULL,shadowSlot,alarmWorldCapture[3],lamp?lamp->fireVolumetricNativeOrdinal:-1,lamp?lamp->staticPromoteFixtureId:-1,lamp?lamp->iflcOptIn:0,sourceWeight,fireVolumeGain);
  }}
'''+anchor);p.write_text(s)
 p=code/'tr_scene.c';s=p.read_text();anchor='R_IFLC_CaptureShadowSlots(fd);';assert s.count(anchor)==1
 s=s.replace(anchor,anchor+r'''
 {static int lastShot=-1;int shot=ri.Cvar_VariableIntegerValue("dw_proofShot");
  if(shot>0 && shot!=lastShot){int i;lastShot=shot;
   ri.Printf(PRINT_ALL,"IFLC14_SCENE shot=%d map=%s iflc=%d lights=%d entities=%d\n",shot,tr.world?tr.world->baseName:"",r_dwFireLightControl->integer,tr.refdef.num_dlights,tr.refdef.num_entities);
   for(i=0;i<tr.refdef.num_dlights && i<MAX_DLIGHTS;++i){const dlight_t *d=&tr.refdef.dlights[i];
    ri.Printf(PRINT_ALL,"IFLC14_LIGHT shot=%d i=%d origin=%.3f,%.3f,%.3f radius=%.3f rgb=%.4f,%.4f,%.4f native=%d nativeFlag=%d fixture=%d local=%d fire=%d world=%d worldSlot=%d pointSlot=%d optin=%d\n",shot,i,d->origin[0],d->origin[1],d->origin[2],d->radius,d->color[0],d->color[1],d->color[2],d->fireVolumetricNativeOrdinal,d->nativeAuthoredDlight,d->staticPromoteFixtureId,d->localVolumetricLamp,d->fireVolumetricSource,d->worldOcclusion,(int)tr.refdef.dlightWorldSlot[i],(int)tr.refdef.dlightShadowSlot[i],d->iflcOptIn);
   }
  }}
''');p.write_text(s)
 p=src/'SP/code/cgame/cg_view.c';s=p.read_text();anchor='"r_ssgi","r_volumetricSun"';assert s.count(anchor)==1
 p.write_text(s.replace(anchor,'"r_dwFireLightControl","r_dlightWorldContainment","r_dlightIntensity","r_externalGLSL","r_volumetricFireV07Mode","r_volumetricFireSourceMode","r_ssgi","r_volumetricSun"'))


def bsp(retail,mapname):
 data=None
 for p in sorted(retail.iterdir()):
  if p.suffix.lower()!='.pk3':continue
  with zipfile.ZipFile(p) as z:
   for n in z.namelist():
    if n.lower()==f'maps/{mapname}.bsp':data=z.read(n)
 assert data is not None
 return data

def capture(retail,out,mapname):
 from PIL import Image,ImageDraw
 import numpy as np
 data=bsp(retail,mapname);world=World(data);out.mkdir(parents=True,exist_ok=True)
 def lump(i):o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
 verts=list(struct.iter_unpack('<10f4B',lump(10)));surfs=list(struct.iter_unpack('<12i12f2i',lump(13)))
 _,count=struct.unpack_from('<6f4i',lump(7))[6:8]
 geometry=[];positions=[]
 for label,eye,yaw in POSITIONS:
  solid=bool(world.solid(eye));near=[]
  for i,s in enumerate(surfs[:count]):
   v=verts[s[3]:s[3]+s[4]]
   if not v:continue
   lo=[min(x[k] for x in v) for k in range(3)];hi=[max(x[k] for x in v) for k in range(3)]
   distance=math.sqrt(sum(max(lo[k]-eye[k],eye[k]-hi[k],0)**2 for k in range(3)))
   shader=world.shaders[s[0]][0].split(b'\0')[0].decode('latin1')
   if distance<280 and any(w in shader.lower() for w in ('flame','torch','lamp','light','fire','door')):
    near.append(dict(surface=i,shader=shader,lo=lo,hi=hi,distance=distance))
  nearby_entities=[]
  for i,e in enumerate(world.entities):
   try:o=list(map(float,e.get('origin','').split()))
   except ValueError:continue
   if len(o)==3 and math.dist(o,eye)<400 and (e.get('classname','').startswith(('light','dlight','func_door','target_speaker'))):nearby_entities.append(dict(ordinal=i,entity=e))
  positions.append(dict(label=label,eye=eye,yaw=yaw,solid=solid,nearby=near,entities=nearby_entities))
  if not solid:geometry.append((label,eye,yaw))
 (out/'POSITIONS.json').write_text(json.dumps(dict(map=mapname,bsp_sha256=hashlib.sha256(data).hexdigest(),positions=positions),indent=2)+'\n')
 if not geometry:return
 runtime=Path(tempfile.mkdtemp(prefix='iflc14-'+mapname+'-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
 build=Path('source/SP/build/release-linux-x86_64')
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
 for p in retail.iterdir():
  if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
 setup=['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_bloom 1','set r_bloomMode 2','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1','set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_volumetricFireV07Mode 2','set r_volumetricFireSourceMode 2','set r_volumetricFireMode 2','set r_volumetricFireMaxActive 8','set r_volumetricFireSamples 32','set r_ext_framebuffer_multisample 4','set r_cameraExposure 1','set r_autoExposure 0','set r_forceAutoExposure 0','set r_dwFireLightControl 0','set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100','set con_notifytime -1']
 (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n');shutil.copy2(main/'SETUP.cfg',out/'SETUP.cfg')
 cmd=['set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_forceSunPause 1','god','notarget','wait 10'];shots=[]
 for label,eye,yaw in geometry:
  cmd+=['set dw_proofShot 0','set dw_proofFreeze 0','proofView '+' '.join(map(str,eye+[10,yaw,0])),'wait 24','set dw_proofFreeze 1','wait 16']
  for variant,fire,local,direct in [('baseline',1,1,1),('fire_off',0,1,1),('local_off',1,0,1),('both_volume_off',0,0,1),('all_off',0,0,0),('restored',1,1,1)]:
   idx=len(shots)+1;name=f'{mapname}_{label}_{variant}'
   cmd+=['set dw_proofShot 0',f'set r_volumetricFire {fire}',f'set r_volumetricLocal {local}',f'set r_dlightIntensity {direct}','wait 12',f'echo IFLC14_STATE {idx} {name}',f'set dw_proofShot {idx}','wait 4',f'screenshot {name}','wait 2']
   shots.append(dict(id=idx,name=name,label=label,variant=variant,eye=eye,yaw=yaw))
 cmd+=['set dw_proofShot 0','echo IFLC14_DONE','set dw_proofFreeze 0','quit']
 (main/'PROBE.cfg').write_text('\n'.join(cmd)+'\n');shutil.copy2(main/'PROBE.cfg',out/'PROBE.cfg')
 exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
 args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe','+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','PROBE.cfg','+spdevmap',mapname]
 env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))};env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
 with (out/'stdout.log').open('w') as log:
  p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:rc=p.wait(timeout=1800)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
 logs=[]
 for i,p in enumerate(sorted(home.rglob('*console*.log'))):shutil.copy2(p,out/f'console-{i}.log');logs.append(p.read_text(errors='replace'))
 text='\n'.join(logs);images={}
 for s in shots:
  paths=list(home.rglob(s['name']+'.tga'))
  if len(paths)==1:
   im=Image.open(paths[0]).convert('RGB');im.save(out/(s['name']+'.png'));images[s['name']]=np.array(im).astype('int16')
 comparisons=[]
 for label,eye,yaw in geometry:
  chosen=[s for s in shots if s['label']==label];board=Image.new('RGB',(960,292*3),(20,20,24));draw=ImageDraw.Draw(board)
  for i,s in enumerate(chosen):
   if s['name'] not in images:continue
   im=Image.open(out/(s['name']+'.png'));im.thumbnail((480,270));x=i%2*480;y=i//2*292;draw.text((x+6,y+4),s['name'],fill='white');board.paste(im,(x,y+22))
   baseline=images.get(f'{mapname}_{label}_baseline')
   if baseline is not None:
    diff=np.abs(baseline-images[s['name']]);comparisons.append(dict(name=s['name'],changed=int(np.any(diff>0,axis=2).sum()),mae=float(diff.mean()),max=int(diff.max())))
  board.save(out/(mapname+'_'+label+'_comparison.png'))
 report=dict(map=mapname,exit=rc,complete='IFLC14_DONE' in text,ready='PROOF_READY' in text,requested=len(shots),captured=len(images),shots=shots,comparisons=comparisons,lighting_lines=[l for l in text.splitlines() if l.startswith(('IFLC14_','PROOF_VIEW','PROOF_CVAR'))],scope='IFLC disabled; map-to-coordinate correspondence pending visual review; pitch is 10 degrees because viewpos did not include pitch.')
 (out/'PROBE_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ('map','exit','complete','ready','requested','captured')},indent=2),flush=True)
 assert rc==0 and report['complete'] and report['ready'] and len(images)==len(shots)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','instrument','capture']);p.add_argument('--retail',type=Path);p.add_argument('--map');p.add_argument('--out',type=Path,default=Path('evidence/runtime'));a=p.parse_args()
 if a.mode=='prepare':prepare()
 elif a.mode=='instrument':instrument()
 else:capture(a.retail.resolve(),a.out.resolve(),a.map)
