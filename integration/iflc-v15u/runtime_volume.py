#!/usr/bin/env python3
"""VOLUME_ONLY universal MANUAL self-pick proof on Crypt1 surface:2933.

The build used by this job deliberately disables R_IFLC_SelfBounds(), so AUTO
cannot help. This script searches the retail BSP for a real camera ray whose
first rendered world-surface hit is one of the previously accepted own-body
surfaces 2543..2555. Those ordinals are TEST evidence only; production code has
no map/surface rules.
"""
from pathlib import Path
import sys,math,struct,json,tempfile,shutil,subprocess,os,signal,re,zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'testlab/scripts'))
import importlib.util
spec=importlib.util.spec_from_file_location('r12',ROOT/'integration/iflc-v12/runtime.py');r12=importlib.util.module_from_spec(spec);spec.loader.exec_module(r12)
from rc4_assault_camera import World
from PIL import Image
import numpy as np

OWNER=[273.0,1312.5,122.0]
BODY=set(range(2543,2556))

def angles(eye,target):
 d=[target[k]-eye[k] for k in range(3)]
 return [-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),math.degrees(math.atan2(d[1],d[0]))%360,0]

def sub(a,b):return [a[i]-b[i] for i in range(3)]
def add(a,b):return [a[i]+b[i] for i in range(3)]
def mul(a,s):return [x*s for x in a]
def dot(a,b):return sum(a[i]*b[i] for i in range(3))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a):
 l=math.sqrt(dot(a,a))
 return ([x/l for x in a],l) if l>1e-9 else ([0,0,0],0)

def bsp_parts(data):
 def lump(i):o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
 verts=list(struct.iter_unpack('<10f4B',lump(10)))
 meshverts=[x[0] for x in struct.iter_unpack('<i',lump(11))]
 surfs=list(struct.iter_unpack('<12i12f2i',lump(13)))
 return verts,meshverts,surfs

def surf_points(verts,s):
 return [list(verts[i][:3]) for i in range(s[3],s[3]+s[4])]

def surf_tris(verts,meshverts,s):
 out=[];fv,nv,fi,ni=s[3],s[4],s[5],s[6]
 if ni>=3:
  for q in range(fi,fi+ni-2,3):
   ids=[fv+meshverts[q+j] for j in range(3)]
   if all(fv<=i<fv+nv for i in ids):out.append(tuple(list(verts[i][:3]) for i in ids))
 return out

def ray_tri(eye,d,a,b,c):
 e1=sub(b,a);e2=sub(c,a);p=cross(d,e2);det=dot(e1,p)
 if abs(det)<1e-7:return None
 inv=1.0/det;tvec=sub(eye,a);u=dot(tvec,p)*inv
 if u<-.0001 or u>1.0001:return None
 q=cross(tvec,e1);v=dot(d,q)*inv
 if v<-.0001 or u+v>1.0001:return None
 t=dot(e2,q)*inv
 return t if t>.01 else None

def discover_body_ray(data,select_eye):
 world=World(data);verts,meshverts,surfs=bsp_parts(data)
 cache={};bounds={}
 def tris(i):
  if i not in cache:cache[i]=surf_tris(verts,meshverts,surfs[i])
  return cache[i]
 def box(i):
  if i not in bounds:
   pts=surf_points(verts,surfs[i])
   if not pts:bounds[i]=([0,0,0],[0,0,0])
   else:bounds[i]=([min(p[k] for p in pts) for k in range(3)],[max(p[k] for p in pts) for k in range(3)])
  return bounds[i]
 def boxdist(point,lo,hi):
  return math.sqrt(sum(max(lo[k]-point[k],point[k]-hi[k],0)**2 for k in range(3)))
 nearby=[i for i,s in enumerate(surfs) if s[4]>0 and boxdist(OWNER,*box(i))<330]
 body_targets=[]
 for i in sorted(BODY):
  for tri in tris(i):
   body_targets.append((i,[sum(p[k] for p in tri)/3.0 for k in range(3)]))
 assert body_targets,'accepted own-body triangles missing'
 def first_hit(eye,target):
  d,length=norm(sub(target,eye));best=(1e30,-1)
  if length<1:return best
  for i in nearby:
   for tri in tris(i):
    t=ray_tri(eye,d,*tri)
    if t is not None and t<best[0] and t<=length+2:best=(t,i)
  return best
 eyes=[select_eye]
 for dz in (-96,-64,-32,0,32,64,96):
  for radius in (112,144,176,208,240):
   for step in range(16):
    th=step*math.pi/8
    eye=[OWNER[0]+radius*math.cos(th),OWNER[1]+radius*math.sin(th),OWNER[2]+dz]
    if world.solid(eye):continue
    if any(world.solid([eye[k]+off[k] for k in range(3)]) for off in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):continue
    eyes.append(eye)
 for eye in eyes:
  for expected,target in body_targets:
   t,hit=first_hit(eye,target)
   if hit in BODY:
    return {'eye':eye,'target':target,'first_hit_surface':hit,'target_surface':expected,'distance':t}
 raise RuntimeError('No camera ray found whose first rendered hit is accepted own-body geometry')

def capture(retail,out):
 out.mkdir(parents=True,exist_ok=True)
 data=r12.geometry(retail,'crypt1');views=r12.discover(data,'crypt1')
 v=next(x for x in views if x['surface']==2933)
 body=discover_body_ray(data,v['eye'])
 (out/'TARGETS.json').write_text(json.dumps({'selected_fixture':v,'owner':OWNER,'accepted_body_surfaces':sorted(BODY),'body_ray':body},indent=2)+'\n')
 runtime=Path(tempfile.mkdtemp(prefix='iflc15u-vol-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
 build=Path('source/SP/build/release-linux-x86_64')
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
 for p in retail.iterdir():
  if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
 setup=['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_bloom 1','set r_bloomMode 2','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1','set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_volumetricFireV07Mode 2','set r_volumetricFireSourceMode 2','set r_volumetricFireMode 2','set r_volumetricFireMaxActive 8','set r_volumetricFireSamples 32','set r_ext_framebuffer_multisample 4','set r_cameraExposure 1','set r_autoExposure 0','set r_forceAutoExposure 0','set r_dwFireLightControl 1','set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100','set con_notifytime -1']
 (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')
 def pv(eye,target):return 'proofView '+' '.join(f'{x:.6f}' for x in eye+angles(eye,target))
 scene=[v['anchor'][0],v['anchor'][1],v['anchor'][2]-42]
 cmds=['set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_forceSunPause 1','god','notarget','wait 16',
       pv(v['eye'],v['anchor']),'wait 20','dw_fl_select','dw_fl_next','dw_fl_info',
       pv(body['eye'],body['target']),'wait 24','dw_fl_self_pick','dw_fl_info',
       'dw_fl_set enabled 1','dw_fl_set direct 1.8','dw_fl_set radius 1.3',
       pv(v['eye'],scene),'wait 20','set dw_proofFreeze 1','wait 12']
 shots=[]
 def shot(label):
  n=len(shots)+1;name='crypt1_surface2933_'+label
  cmds.extend([f'echo IFLC15U_VOL_STATE {n} {label}','dw_fl_info',f'set dw_proofShot {n}','wait 4',f'screenshot {name}','set dw_proofShot 0','wait 2'])
  shots.append((n,label,name))
 cmds+=['dw_fl_set selfshadow 1','wait 24'];shot('on')
 cmds+=['dw_fl_set selfshadow 0','wait 32'];shot('off')
 cmds+=['dw_fl_save','wait 12'];shot('saved')
 cmds+=['dw_fl_set selfshadow 1','wait 16','dw_fl_reload','wait 32'];shot('reloaded')
 cmds+=['dw_fl_reset','set dw_proofFreeze 0','echo IFLC15U_VOL_DONE','quit']
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
  if cur is not None and 'IFLC:' in line:cur.append(line)
 expected=body['first_hit_surface']
 bind=f'IFLC V1.5 Universal: bound exact body surface {expected};'
 if bind not in text:faults.append(f'manual body surface {expected} did not bind')
 for n,label,name in shots:
  found=list(home.rglob(name+'.tga'))
  if len(found)==1:
   im=Image.open(found[0]).convert('RGB');im.save(out/(name+'.png'));images[label]=np.asarray(im).astype(np.int16)
  lines='\n'.join(states.get(n,[]))
  if 'route=VOLUME_ONLY' not in lines:faults.append(label+': VOLUME_ONLY owner not selected')
  if label in ('off','saved','reloaded') and (not re.search(r'selfshadow=OFF\b',lines) or not re.search(r'ownBodySurfaces=[1-9]\d*',lines) or not re.search(r'manualSeeds=[1-8]',lines)):
   faults.append(label+': manual OFF not active')
 if 'IFLC15U_VOL_DONE' not in text:faults.append('scenario incomplete')
 comps=[]
 for a,b in [('on','off'),('off','saved'),('saved','reloaded')]:
  if a in images and b in images:
   d=np.abs(images[a]-images[b]);comps.append({'a':a,'b':b,'pixels':int(np.any(d>0,axis=2).sum()),'above2':int(np.any(d>2,axis=2).sum()),'mae':float(d.mean()),'max':int(d.max())})
 if not any(x['a']=='on' and x['b']=='off' and x['above2']>20 for x in comps):faults.append('selfshadow produced no visible response')
 for a,b in [('off','saved'),('saved','reloaded')]:
  hit=next((x for x in comps if x['a']==a and x['b']==b),None)
  if not hit or hit['pixels']!=0:faults.append(a+'->'+b+': persistence not pixel exact')
 diagnostics=[l for l in text.splitlines() if 'IFLC:' in l or 'IFLC V1.5 Universal:' in l or l.startswith('IFLC15U_VOL_')]
 report={'exit':rc,'target':body,'requested':len(shots),'captured':len(images),'comparisons':comps,'faults':faults,'diagnostics':diagnostics}
 (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 assert rc==0 and len(images)==len(shots) and not faults,faults

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('retail',type=Path);p.add_argument('out',type=Path);a=p.parse_args();capture(a.retail.resolve(),a.out.resolve())
