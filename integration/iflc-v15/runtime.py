#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,math,os,re,shutil,signal,struct,subprocess,tempfile,zipfile,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'testlab/scripts'))
from rc4_assault_camera import World
OWNER=[-928.0,-64.0,256.0]

def angles(eye,target):
 d=[target[k]-eye[k] for k in range(3)];return [-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),math.degrees(math.atan2(d[1],d[0]))%360,0]

def bsp(retail):
 for p in sorted(retail.iterdir()):
  if p.suffix.lower()!='.pk3':continue
  with zipfile.ZipFile(p) as z:
   for n in z.namelist():
    if n.lower()=='maps/crypt1.bsp':return z.read(n)
 raise RuntimeError('crypt1.bsp missing')

def discover(retail):
 data=bsp(retail);world=World(data)
 def lump(i):o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
 verts=list(struct.iter_unpack('<10f4B',lump(10)));meshverts=[x[0] for x in struct.iter_unpack('<i',lump(11))];surfs=list(struct.iter_unpack('<12i12f2i',lump(13)))
 def shader(s):return world.shaders[s[0]][0].split(b'\0')[0].decode('latin1')
 def points(index):s=surfs[index];return verts[s[3]:s[3]+s[4]]
 def bounds(index):
  v=points(index);return [min(x[k] for x in v) for k in range(3)],[max(x[k] for x in v) for k in range(3)]
 def tri_target(index):
  s=surfs[index];ids=[]
  for q in range(s[5],min(s[5]+s[6],len(meshverts))):
   vi=s[3]+meshverts[q]
   if s[3]<=vi<s[3]+s[4]:ids.append(vi)
   if len(ids)==3:break
  if len(ids)<3:
   v=points(index);return [sum(x[k] for x in v)/len(v) for k in range(3)]
  return [sum(verts[i][k] for i in ids)/3 for k in range(3)]
 flames=[]
 for i,s in enumerate(surfs):
  if 'flame' not in shader(s).lower() or s[4]<=0:continue
  v=points(i);a=[sum(x[k] for x in v)/len(v) for k in range(3)]
  if math.dist(a,OWNER)<120:flames.append((math.dist(a,OWNER),i,a,shader(s)))
 assert flames, 'no flame surface near native:900'
 flames.sort();flame=flames[0];anchor=flame[2]
 eyes=[]
 for dz in (-48,-24,-72,16):
  for dist in (160,192,128,224):
   for step in range(16):
    th=step*math.pi/8;eye=[anchor[0]+dist*math.cos(th),anchor[1]+dist*math.sin(th),anchor[2]+dz]
    if world.solid(eye) or any(world.solid([eye[k]+o[k] for k in range(3)]) for o in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):continue
    hit=world.trace(eye,anchor)
    if hit and hit.get('fraction',0)<.985:continue
    eyes.append((abs(dz+48)+abs(dist-160)*.1+min(step,16-step)*.01,eye))
 assert eyes,'no camera';eye=min(eyes)[1]
 body=[];architecture=[]
 for i,s in enumerate(surfs):
  if s[4]<=0 or 'flame' in shader(s).lower():continue
  lo,hi=bounds(i);ext=sorted([hi[k]-lo[k] for k in range(3)],reverse=True);target=tri_target(i);d=math.dist(target,OWNER)
  hit=world.trace(eye,target)
  visible=not hit or hit.get('fraction',0)>=.94
  if not visible:continue
  if d<120 and ext[0]<128 and ext[1]<96 and OWNER[2]-110<target[2]<OWNER[2]+32:
   score=d+abs(target[2]-(OWNER[2]-28))*.35+ext[0]*.02;body.append((score,i,target,shader(s),lo,hi))
  if d<220 and ext[0]>128 and ext[1]>64:
   architecture.append((d,i,target,shader(s),lo,hi))
 assert body,'no visible compact body candidate'
 body.sort();b=body[0]
 assert architecture,'no visible architecture control';architecture.sort();a=architecture[0]
 return dict(bsp_sha256=hashlib.sha256(data).hexdigest(),owner=OWNER,flame_surface=flame[1],flame_anchor=anchor,flame_shader=flame[3],eye=eye,body_surface=b[1],body_target=b[2],body_shader=b[3],architecture_surface=a[1],architecture_target=a[2],architecture_shader=a[3])

def capture(retail,out):
 from PIL import Image,ImageDraw
 import numpy as np
 out.mkdir(parents=True,exist_ok=True);view=discover(retail);(out/'TARGETS.json').write_text(json.dumps(view,indent=2)+'\n')
 runtime=Path(tempfile.mkdtemp(prefix='iflc15-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
 build=Path('source/SP/build/release-linux-x86_64')
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
 for p in retail.iterdir():
  if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
 setup=['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_bloom 1','set r_bloomMode 2','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1','set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_volumetricFireV07Mode 2','set r_volumetricFireSourceMode 2','set r_volumetricFireMode 2','set r_volumetricFireMaxActive 8','set r_volumetricFireSamples 32','set r_ext_framebuffer_multisample 4','set r_cameraExposure 1','set r_autoExposure 0','set r_forceAutoExposure 0','set r_dwFireLightControl 1','set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100','set con_notifytime -1']
 (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')
 def pv(target):return 'proofView '+' '.join(f'{x:.6f}' for x in view['eye']+angles(view['eye'],target))
 scene=[view['owner'][0],view['owner'][1],view['owner'][2]-55]
 cmds=['set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_forceSunPause 1','god','notarget','wait 16',pv(view['flame_anchor']),'wait 20','dw_fl_select','dw_fl_info',pv(view['body_target']),'wait 12','dw_fl_self_pick','dw_fl_info',pv(scene),'wait 20','set dw_proofFreeze 1','wait 12']
 shots=[]
 def shot(label):
  n=len(shots)+1;name='crypt1_native900_'+label;cmds.extend([f'echo IFLC15_STATE {n} {label}','dw_fl_info',f'set dw_proofShot {n}','wait 4',f'screenshot {name}','set dw_proofShot 0','wait 2']);shots.append((n,label,name))
 cmds+=['dw_fl_set selfshadow 1','wait 24'];shot('on')
 cmds+=['dw_fl_set selfshadow 0','wait 32'];shot('off')
 cmds+=['dw_fl_save','wait 12'];shot('saved')
 cmds+=['dw_fl_set selfshadow 1','wait 16','dw_fl_reload','wait 32'];shot('reloaded')
 cmds+=['dw_fl_set selfshadow auto','wait 24'];shot('auto')
 cmds+=[pv(view['architecture_target']),'wait 12','dw_fl_self_pick','dw_fl_info','echo IFLC15_ARCH_CONTROL_DONE','dw_fl_reset','set dw_proofFreeze 0','echo IFLC15_DONE','quit']
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
 text='\n'.join(texts);states={};current=None;images={};faults=[]
 for line in text.splitlines():
  m=re.search(r'IFLC15_STATE (\d+) (\S+)',line)
  if m:current=states.setdefault(int(m[1]),[])
  if current is not None and line.startswith('IFLC:'):current.append(line)
 for n,label,name in shots:
  found=list(home.rglob(name+'.tga'))
  if len(found)==1:
   im=Image.open(found[0]).convert('RGB');im.save(out/(name+'.png'));images[label]=np.asarray(im).astype(np.int16)
  lines='\n'.join(states.get(n,[]))
  if 'key=native:900 ' not in lines:faults.append(label+': native:900 not selected')
  if label in ('off','saved','reloaded'):
   if not re.search(r'selfshadow=OFF\b',lines) or not re.search(r'ownBodySurfaces=[1-9]\d*',lines) or not re.search(r'manualSeeds=[1-8]',lines):faults.append(label+': manual OFF not active')
 if 'bound exact body surface' not in text:faults.append('manual body pick did not bind')
 if 'IFLC15_ARCH_CONTROL_DONE' not in text or not re.search(r'protected architecture|too large|too far',text):faults.append('architecture safety rejection not observed')
 if 'IFLC15_DONE' not in text:faults.append('scenario incomplete')
 comparisons=[]
 for a,b in [('on','off'),('off','saved'),('saved','reloaded')]:
  if a in images and b in images:
   d=np.abs(images[a]-images[b]);comparisons.append(dict(a=a,b=b,pixels=int(np.any(d>0,axis=2).sum()),above2=int(np.any(d>2,axis=2).sum()),mae=float(d.mean()),max=int(d.max())))
 if not any(x['a']=='on' and x['b']=='off' and x['above2']>20 for x in comparisons):faults.append('own shadow toggle produced no measurable image response in test view')
 board=Image.new('RGB',(960,292*3),(20,20,24));draw=ImageDraw.Draw(board)
 for i,label in enumerate(('on','off','reloaded','auto')):
  if label not in images:continue
  im=Image.open(out/f'crypt1_native900_{label}.png');im.thumbnail((480,270));x=i%2*480;y=i//2*292;draw.text((x+8,y+3),label,fill='white');board.paste(im,(x,y+22))
 board.save(out/'crypt1_native900_v15_comparison.png')
 report=dict(exit=rc,complete='IFLC15_DONE' in text,target=view,requested=len(shots),captured=len(images),comparisons=comparisons,faults=faults,visual_status='PENDING_MANUAL_REVIEW')
 (out/'IFLC15_RUNTIME_REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
 assert rc==0 and len(images)==len(shots) and not faults, faults

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('retail',type=Path);p.add_argument('out',type=Path);a=p.parse_args();capture(a.retail.resolve(),a.out.resolve())
