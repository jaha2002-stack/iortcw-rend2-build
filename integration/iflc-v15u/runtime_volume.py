#!/usr/bin/env python3
"""Real VOLUME_ONLY manual self-pick proof on the known Crypt1 surface:2933 fixture.
Map/surface ids are TEST TARGETS only; production code has no map-specific rules.
"""
from pathlib import Path
import sys,math,struct,json,tempfile,shutil,subprocess,os,signal,re,zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'testlab/scripts'))
import importlib.util
spec=importlib.util.spec_from_file_location('r12',ROOT/'integration/iflc-v12/runtime.py');r12=importlib.util.module_from_spec(spec);spec.loader.exec_module(r12)
from PIL import Image
import numpy as np

def angles(eye,target):
 d=[target[k]-eye[k] for k in range(3)]
 return [-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),math.degrees(math.atan2(d[1],d[0]))%360,0]

def geometry_tables(data):
 def lump(i):o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
 verts=list(struct.iter_unpack('<10f4B',lump(10)))
 mesh=[x[0] for x in struct.iter_unpack('<i',lump(11))]
 surfs=list(struct.iter_unpack('<12i12f2i',lump(13)))
 tris=[]
 for s in surfs:
  out=[]
  if s[2] in (1,3):
   for q in range(s[5],s[5]+s[6],3):
    if q+2>=len(mesh):break
    ids=[s[3]+mesh[q+k] for k in range(3)]
    if all(s[3]<=i<s[3]+s[4] for i in ids):
     out.append([[verts[i][k] for k in range(3)] for i in ids])
  tris.append(out)
 return verts,surfs,tris

def ray_tri(origin,direction,tri):
 eps=1e-6
 e1=[tri[1][k]-tri[0][k] for k in range(3)];e2=[tri[2][k]-tri[0][k] for k in range(3)]
 p=[direction[1]*e2[2]-direction[2]*e2[1],direction[2]*e2[0]-direction[0]*e2[2],direction[0]*e2[1]-direction[1]*e2[0]]
 det=sum(e1[k]*p[k] for k in range(3))
 if abs(det)<eps:return None
 inv=1.0/det;t=[origin[k]-tri[0][k] for k in range(3)]
 u=sum(t[k]*p[k] for k in range(3))*inv
 if u<-1e-5 or u>1.00001:return None
 q=[t[1]*e1[2]-t[2]*e1[1],t[2]*e1[0]-t[0]*e1[2],t[0]*e1[1]-t[1]*e1[0]]
 v=sum(direction[k]*q[k] for k in range(3))*inv
 if v<-1e-5 or u+v>1.00001:return None
 hit=sum(e2[k]*q[k] for k in range(3))*inv
 return hit if hit>1e-4 else None

def first_surface(tris,eye,target,maxdist=512):
 d=[target[k]-eye[k] for k in range(3)];ln=math.sqrt(sum(x*x for x in d))
 if ln<1e-5:return -1
 d=[x/ln for x in d];best=maxdist;bestidx=-1
 for idx,ts in enumerate(tris):
  for tri in ts:
   t=ray_tri(eye,d,tri)
   if t is not None and t<best-1e-4:best=t;bestidx=idx
 return bestidx

def surface_bounds(verts,surfs,index):
 s=surfs[index];v=verts[s[3]:s[3]+s[4]]
 return [min(x[k] for x in v) for k in range(3)],[max(x[k] for x in v) for k in range(3)]

def find_targets(data,flame_anchor):
 from rc4_assault_camera import World
 world=World(data);verts,surfs,tris=geometry_tables(data)
 body_set=set(range(2543,2556));best=None
 for dz in (-48,-24,-72,0,24):
  for distance in (128,160,192,224,96):
   for step in range(32):
    th=step*math.pi/16
    eye=[flame_anchor[0]+distance*math.cos(th),flame_anchor[1]+distance*math.sin(th),flame_anchor[2]+dz]
    if world.solid(eye):continue
    flameTrace=world.trace(eye,flame_anchor)
    if flameTrace and flameTrace.get('fraction',0)<.94:continue
    for bi in body_set:
     for tri in tris[bi]:
      target=[sum(tri[j][k] for j in range(3))/3 for k in range(3)]
      if first_surface(tris,eye,target)==bi:
       score=abs(distance-160)+abs(dz+48)*.2+min(step,32-step)*.01
       if best is None or score<best[0]:best=(score,eye,bi,target)
 if best is None:raise RuntimeError('no exact visible own-body ray')
 _,eye,body_surface,body_target=best
 arch=None
 for idx,s in enumerate(surfs):
  if idx in body_set or not tris[idx]:continue
  lo,hi=surface_bounds(verts,surfs,idx);ext=sorted([hi[k]-lo[k] for k in range(3)],reverse=True)
  if ext[0]<128 or ext[1]<64:continue
  cen=[(lo[k]+hi[k])*.5 for k in range(3)]
  if math.dist(cen,flame_anchor)>260:continue
  for tri in tris[idx]:
   target=[sum(tri[j][k] for j in range(3))/3 for k in range(3)]
   if first_surface(tris,eye,target)==idx:
    dist=math.dist(target,flame_anchor)
    if arch is None or dist<arch[0]:arch=(dist,idx,target)
 if arch is None:raise RuntimeError('no exact visible architecture ray')
 return eye,body_surface,body_target,arch[1],arch[2]

def capture(retail,out):
 out.mkdir(parents=True,exist_ok=True)
 data=r12.geometry(retail,'crypt1');views=r12.discover(data,'crypt1')
 v=next(x for x in views if x['surface']==2933)
 eye,body_surface,body,arch_surface,arch=find_targets(data,v['anchor'])
 v=dict(v);v['eye']=eye
 (out/'TARGETS.json').write_text(json.dumps({'view':v,'body_surface':body_surface,'body':body,'body_first_hit':body_surface,'architecture_surface':arch_surface,'architecture':arch,'architecture_first_hit':arch_surface},indent=2)+'\n')
 runtime=Path(tempfile.mkdtemp(prefix='iflc15u-vol-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
 build=Path('source/SP/build/release-linux-x86_64')
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
 for p in retail.iterdir():
  if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
 setup=['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_bloom 1','set r_bloomMode 2','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1','set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_volumetricFireV07Mode 2','set r_volumetricFireSourceMode 2','set r_volumetricFireMode 2','set r_volumetricFireMaxActive 8','set r_volumetricFireSamples 32','set r_ext_framebuffer_multisample 4','set r_cameraExposure 1','set r_autoExposure 0','set r_forceAutoExposure 0','set r_dwFireLightControl 1','set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100','set con_notifytime -1']
 (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')
 def pv(target):return 'proofView '+' '.join(f'{x:.6f}' for x in v['eye']+angles(v['eye'],target))
 scene=[v['anchor'][0],v['anchor'][1],v['anchor'][2]-42]
 cmds=['set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_forceSunPause 1','god','notarget','wait 16',
       pv(v['anchor']),'wait 20','dw_fl_select','dw_fl_next','dw_fl_info',
       pv(body),'wait 12','dw_fl_self_pick','dw_fl_info',
       'dw_fl_set enabled 1','dw_fl_set direct 1.8','dw_fl_set radius 1.3',
       pv(scene),'wait 20','set dw_proofFreeze 1','wait 12']
 shots=[]
 def shot(label):
  n=len(shots)+1;name='crypt1_surface2933_'+label
  cmds.extend([f'echo IFLC15U_VOL_STATE {n} {label}','dw_fl_info',f'set dw_proofShot {n}','wait 4',f'screenshot {name}','set dw_proofShot 0','wait 2'])
  shots.append((n,label,name))
 cmds+=['dw_fl_set selfshadow 1','wait 24'];shot('on')
 cmds+=['dw_fl_set selfshadow 0','wait 32'];shot('off')
 cmds+=['dw_fl_save','wait 12'];shot('saved')
 cmds+=['dw_fl_set selfshadow 1','wait 16','dw_fl_reload','wait 32'];shot('reloaded')
 cmds+=[pv(arch),'wait 12','dw_fl_self_pick','dw_fl_info','echo IFLC15U_VOL_ARCH_DONE','dw_fl_reset','set dw_proofFreeze 0','echo IFLC15U_VOL_DONE','quit']
 (main/'TEST.cfg').write_text('\n'.join(cmds)+'\n')
 exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
 args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe','+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','TEST.cfg','+spdevmap','crypt1']
 env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))};env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
 with (out/'stdout.log').open('w') as log:
  p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:rc=p.wait(timeout=1800)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
 texts=[]
 for i,p in enumerate(sorted(home.rglob('*console*.log'))):shutil.copy2(p,out/f'console-{i}.log');texts.append(p.read_text(errors='replace'))
 text='\n'.join(texts);states={};cur=None;images={};faults=[]
 for line in text.splitlines():
  m=re.search(r'IFLC15U_VOL_STATE (\d+) (\S+)',line)
  if m:cur=states.setdefault(int(m[1]),[])
  if cur is not None and line.startswith('IFLC:'):cur.append(line)
 for n,label,name in shots:
  f=list(home.rglob(name+'.tga'))
  if len(f)==1:
   im=Image.open(f[0]).convert('RGB');im.save(out/(name+'.png'));images[label]=np.asarray(im).astype(np.int16)
  lines='\n'.join(states.get(n,[]))
  if 'route=VOLUME_ONLY' not in lines:faults.append(label+': VOLUME_ONLY owner not selected')
  if label in ('off','saved','reloaded') and (not re.search(r'selfshadow=OFF\b',lines) or not re.search(r'ownBodySurfaces=[1-9]\d*',lines) or not re.search(r'manualSeeds=[1-8]',lines)):
   faults.append(label+': manual OFF not active')
 if 'IFLC V1.5 Universal: bound exact body surface' not in text:faults.append('manual body pick did not bind')
 if 'IFLC15U_VOL_ARCH_DONE' not in text or not re.search(r'protected architecture|too large|too far',text):faults.append('architecture rejection not observed')
 if 'IFLC15U_VOL_DONE' not in text:faults.append('scenario incomplete')
 comps=[]
 for a,b in [('on','off'),('off','saved'),('saved','reloaded')]:
  if a in images and b in images:
   d=np.abs(images[a]-images[b]);comps.append({'a':a,'b':b,'pixels':int(np.any(d>0,axis=2).sum()),'above2':int(np.any(d>2,axis=2).sum()),'mae':float(d.mean()),'max':int(d.max())})
 if not any(x['a']=='on' and x['b']=='off' and x['above2']>20 for x in comps):faults.append('selfshadow produced no visible response')
 report={'exit':rc,'requested':len(shots),'captured':len(images),'comparisons':comps,'faults':faults}
 (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 assert rc==0 and len(images)==len(shots) and not faults,faults

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('retail',type=Path);p.add_argument('out',type=Path);a=p.parse_args();capture(a.retail.resolve(),a.out.resolve())
