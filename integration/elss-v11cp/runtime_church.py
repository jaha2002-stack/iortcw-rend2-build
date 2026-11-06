#!/usr/bin/env python3
"""Real-game Church reproduction for the user-reported ELSS V1 surface 10810 case."""
from pathlib import Path
import sys,math,struct,re,json,zipfile,tempfile,shutil,subprocess,os,signal,hashlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'testlab/scripts'))
from rc4_assault_camera import World
from PIL import Image,ImageDraw
import numpy as np

MAP='church'; SURFACE=10810; FIXTURE=107; ANCHOR=[-241.0,-178.0,144.0]

def geometry(retail):
 data=None
 for p in sorted(retail.iterdir()):
  if p.suffix.lower()!='.pk3':continue
  with zipfile.ZipFile(p) as z:
   for n in z.namelist():
    if n.lower()=='maps/church.bsp':data=z.read(n);break
  if data is not None:break
 assert data is not None
 return data

def parsed(data):
 def lump(i):o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
 verts=list(struct.iter_unpack('<10f4B',lump(10)));surfs=list(struct.iter_unpack('<12i12f2i',lump(13)))
 return verts,surfs

def vpos(v):return (float(v[0]),float(v[1]),float(v[2]))
def d2(a,b):return sum((a[i]-b[i])**2 for i in range(3))
def aabb_d2(p,lo,hi):
 return sum((lo[i]-p[i])**2 if p[i]<lo[i] else (p[i]-hi[i])**2 if p[i]>hi[i] else 0 for i in range(3))

def components(verts,surfs,index):
 s=surfs[index];idx=s[5];num=s[6] if False else None
 # Q3 dsurface tuple: shader,fog,type,firstVert,numVerts,firstIndex,numIndexes,...
 firstv=s[3];nv=s[4];firsti=s[5];ni=s[6]
 # indexes lump stores ints relative to firstVert
 return firstv,nv,firsti,ni

def index_lump(data):
 o,n=struct.unpack_from('<ii',data,8+8*11);return list(struct.unpack('<%di'%(n//4),data[o:o+n]))

def build_components(data,verts,surfs,index):
 indexes=index_lump(data);s=surfs[index];fv,nv,fi,ni=s[3],s[4],s[5],s[6]
 assert ni%3==0
 tris=[]
 for i in range(0,ni,3):
  ids=[fv+indexes[fi+i+j] for j in range(3)]
  pts=[vpos(verts[x]) for x in ids]
  tris.append((ids,pts))
 edges={}
 for ti,(ids,pts) in enumerate(tris):
  for a,b in ((0,1),(1,2),(2,0)):
   pa=tuple(round(x,4) for x in pts[a]);pb=tuple(round(x,4) for x in pts[b]);key=tuple(sorted((pa,pb)));edges.setdefault(key,[]).append(ti)
 adj=[set() for _ in tris]
 for xs in edges.values():
  if len(xs)>1:
   for a in xs:
    adj[a].update(x for x in xs if x!=a)
 seen=set();comps=[]
 for start in range(len(tris)):
  if start in seen:continue
  stack=[start];seen.add(start);c=[]
  while stack:
   a=stack.pop();c.append(a)
   for b in adj[a]:
    if b not in seen:seen.add(b);stack.append(b)
  pts=[p for ti in c for p in tris[ti][1]]
  lo=[min(p[k] for p in pts) for k in range(3)];hi=[max(p[k] for p in pts) for k in range(3)]
  ext=sorted([hi[k]-lo[k] for k in range(3)],reverse=True)
  comps.append({'tris':c,'lo':lo,'hi':hi,'ext':ext,'distance2':aabb_d2(ANCHOR,lo,hi)})
 safe=[c for c in comps if c['ext'][0]<=256 and c['ext'][1]<=160 and not(c['ext'][0]>192 and c['ext'][1]>80) and c['distance2']<=224**2]
 assert safe,[(c['ext'],c['distance2'],len(c['tris'])) for c in comps[:20]]
 c=min(safe,key=lambda x:(x['distance2'],x['ext'][0]*x['ext'][1],len(x['tris'])))
 tri=min(c['tris'],key=lambda ti:d2([sum(p[k] for p in tris[ti][1])/3 for k in range(3)],ANCHOR))
 target=[sum(p[k] for p in tris[tri][1])/3 for k in range(3)]
 return tris,comps,c,tri,target

def angles(eye,target):
 d=[target[k]-eye[k] for k in range(3)]
 return [-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),math.degrees(math.atan2(d[1],d[0]))%360,0]

def choose_eye(world,target):
 cand=[]
 for dist in (96,128,160,224):
  for step in range(24):
   a=step*2*math.pi/24
   for dz in (-48,-24,0,24,48):
    eye=[target[0]+dist*math.cos(a),target[1]+dist*math.sin(a),target[2]+dz]
    if world.solid(eye):continue
    if any(world.solid([eye[k]+o[k] for k in range(3)]) for o in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):continue
    hit=world.trace(eye,target)
    frac=hit.get('fraction',1) if hit else 1
    cand.append((abs(frac-1)+dist*.001+abs(dz)*.0001,eye))
 assert cand
 return min(cand,key=lambda x:x[0])[1]

def capture(retail,out):
 out.mkdir(parents=True,exist_ok=True);data=geometry(retail);world=World(data);verts,surfs=parsed(data)
 tris,comps,comp,tri,target=build_components(data,verts,surfs,SURFACE);eye=choose_eye(world,target)
 (out/'TARGET.json').write_text(json.dumps({'map':MAP,'surface':SURFACE,'fixture':FIXTURE,'anchor':ANCHOR,'component':comp,'seed_triangle':tri,'target':target,'eye':eye,'bsp_sha256':hashlib.sha256(data).hexdigest()},indent=2)+'\n')
 runtime=Path(tempfile.mkdtemp(prefix='elss-v11-church-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
 build=Path('source/SP/build/release-linux-x86_64')
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
 for p in retail.iterdir():
  if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
 setup=['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_bloom 1','set r_bloomMode 2','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1','set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_ext_framebuffer_multisample 4','set r_cameraExposure 1','set r_autoExposure 0','set r_forceAutoExposure 0','set r_dwFireLightControl 0','set r_dwElectricLightControl 1','set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100','set con_notifytime -1']
 (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')
 pv='proofView '+' '.join(f'{x:.6f}' for x in eye+angles(eye,target))
 cmd=['set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_forceSunPause 1','god','notarget','wait 18',
      f'dw_el_v11_test_fixture {FIXTURE} 1','wait 28',f'dw_el_v11_test_select {FIXTURE}','dw_el_v11_test_audit',pv,'wait 20','dw_el_self_pick','dw_el_info','wait 12']
 shots=[]
 def shot(label):
  n=len(shots)+1;name='church_fixture107_'+label
  cmd.extend([f'echo ELSS11_STATE {n} {label}','dw_el_info','dw_el_v11_test_audit',f'set dw_proofShot {n}','wait 4',f'screenshot {name}','set dw_proofShot 0','wait 2']);shots.append((n,label,name))
 cmd+=['set dw_proofFreeze 1','dw_el_set selfshadow 1','wait 24'];shot('on')
 cmd+=['dw_el_set selfshadow 0','wait 32'];shot('off')
 cmd+=['dw_el_save','wait 12'];shot('saved')
 cmd+=['dw_el_set selfshadow 1','wait 16','dw_el_reload','wait 32'];shot('reloaded')
 cmd+=['dw_el_set selfshadow auto','wait 24'];shot('auto')
 cmd+=['set dw_proofFreeze 0',f'dw_el_v11_test_fixture {FIXTURE} 0','echo ELSS11_DONE','quit']
 (main/'TEST.cfg').write_text('\n'.join(cmd)+'\n')
 exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
 args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe','+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','TEST.cfg','+spdevmap',MAP]
 env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))};env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
 with (out/'stdout.log').open('w') as log:
  p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:rc=p.wait(timeout=1800)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
 texts=[]
 for i,p in enumerate(sorted(home.rglob('*console*.log'))):shutil.copy2(p,out/f'console-{i}.log');texts.append(p.read_text(errors='replace'))
 text='\n'.join(texts);states={};cur=None;images={};faults=[]
 for line in text.splitlines():
  m=re.search(r'ELSS11_STATE (\d+) (\S+)',line)
  if m:cur=states.setdefault(int(m[1]),[])
  if cur is not None and line.startswith(('ELSS:','ELSS V1.1:','ELSS11_TEST_')):cur.append(line)
 if 'ELSS11_TEST_SELECTED fixture:107' not in text:faults.append('fixture:107 not selected')
 m=re.search(r'ELSS V1\.1: bound connected component surface (\d+) triangle (\d+); ownBodySurfaces=(\d+) ownBodyTriangles=(\d+)',text)
 if not m:faults.append('crosshair component pick did not bind')
 elif int(m.group(1))!=SURFACE:faults.append('crosshair hit wrong surface '+m.group(1))
 for n,label,name in shots:
  found=list(home.rglob(name+'.tga'))
  if len(found)==1:
   im=Image.open(found[0]).convert('RGB');im.save(out/(name+'.png'));images[label]=np.asarray(im).astype(np.int16)
  lines='\n'.join(states.get(n,[]))
  if label in ('off','saved','reloaded'):
   if 'selfshadow=OFF' not in lines:faults.append(label+': OFF not active')
   if not re.search(r'ownBodyTriangles=[1-9]\d*',lines):faults.append(label+': no triangle mask')
   if 'shadowSlot=0' not in lines:faults.append(label+': expected shadowSlot 0 not retained')
 comps=[]
 for a,b in [('on','off'),('off','saved'),('saved','reloaded'),('off','auto')]:
  if a in images and b in images:
   d=np.abs(images[a]-images[b]);comps.append({'a':a,'b':b,'pixels':int(np.any(d>0,axis=2).sum()),'above2':int(np.any(d>2,axis=2).sum()),'mae':float(d.mean()),'max':int(d.max())})
 for a,b in [('off','saved'),('saved','reloaded')]:
  x=next((q for q in comps if q['a']==a and q['b']==b),None)
  if not x or x['pixels']!=0:faults.append(a+'->'+b+' not pixel exact')
 onoff=next((q for q in comps if q['a']=='on' and q['b']=='off'),None)
 if not onoff or onoff['above2']<10:faults.append('component selfshadow produced no visible response')
 if 'ELSS11_DONE' not in text:faults.append('scenario incomplete')
 diag=[l for l in text.splitlines() if l.startswith(('ELSS:','ELSS V1.1:','ELSS11_'))]
 report={'exit':rc,'target_component':comp,'target_triangle':tri,'captured':len(images),'comparisons':comps,'faults':faults,'diagnostics':diag}
 (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
 if images:
  board=Image.new('RGB',(960,292*3),(20,20,24));draw=ImageDraw.Draw(board)
  for i,(_,label,name) in enumerate(shots):
   if label not in images:continue
   im=Image.open(out/(name+'.png'));im.thumbnail((480,270));x=i%2*480;y=i//2*292;draw.text((x+8,y+3),label,fill='white');board.paste(im,(x,y+22))
  board.save(out/'church_fixture107_component_comparison.png')
 print(json.dumps({'exit':rc,'component_tris':len(comp['tris']),'component_ext':comp['ext'],'captured':len(images),'comparisons':comps,'faults':faults},indent=2))
 assert rc==0 and len(images)==len(shots) and not faults,faults

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('retail',type=Path);p.add_argument('out',type=Path);a=p.parse_args();capture(a.retail.resolve(),a.out.resolve())
