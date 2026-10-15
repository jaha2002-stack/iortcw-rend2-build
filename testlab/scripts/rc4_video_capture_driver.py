#!/usr/bin/env python3
"""Native game recording with short startup argv, verified doorway, exact replay."""
from pathlib import Path
import importlib.util,os,sys,subprocess,signal,shutil,struct,zipfile,json,time
spec=importlib.util.spec_from_file_location('movie_base',Path(__file__).with_name('rc4_noclip_movies.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.ROUTES['tesla'][-6:]=[[16.6,-160,670,-336,24,620],[17.5,-192,728,-336,20,540],[18.6,-292,752,-336,10,540],[20.0,-430,752,-328,7,555],[22.0,-590,690,-324,12,575],[24.0,-620,690,-324,13,590]]
ROUTES=m.ROUTES

def quoted(s):return '"'+str(s).replace('\\','\\\\').replace('"','\\"').replace('\n','').replace('\r','')+'"'
def launch(runtime,home,args,log,limit=1100):
 exe=next(runtime.glob('iowolfsp.*'),None) or next(runtime.glob('ioWolfSP.*'));assert exe
 recording='+spdevmap' in args
 width,height=(320,180) if recording else (960,540)
 lines=['set logfile 2','set dw_testAutomation 1','exec PRODUCTION_HIGH_QUALITY.cfg','set r_mode -1','set r_customwidth '+str(width),'set r_customheight '+str(height),'set r_fullscreen 0','set s_initsound 0','set com_fixedtime 40','set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set con_notifytime -1','set r_autoExposure 0','vid_restart']
 current=[]
 for arg in args:
  if arg.startswith('+'):
   if current:lines.append(current[0]+' '+' '.join(quoted(x) for x in current[1:]))
   current=[arg[1:]]
  else:current.append(arg)
 if current:lines.append(current[0]+' '+' '.join(quoted(x) for x in current[1:]))
 cfg='BOOT_'+home.name+'.cfg';(runtime/'main'/cfg).write_text('\n'.join(lines)+'\n');shutil.copy2(runtime/'main'/cfg,m.OUT/cfg)
 command=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+safe','+set','com_introplayed','1','+set','com_recommendedSet','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+set','r_fullscreen','0','+set','s_initsound','0','+exec',cfg]
 assert sum(a.startswith('+') for a in command)<20
 started=time.time();last_report=0
 with log.open('w') as f:
  p=subprocess.Popen(command,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'LIBGL_ALWAYS_SOFTWARE':'1','LP_NUM_THREADS':'4'},start_new_session=True)
  while p.poll() is None:
   time.sleep(5);elapsed=time.time()-started
   if elapsed-last_report>25:
    files=list(home.rglob('*console*.log'));tail=files[0].read_text(errors='replace') if files else ''
    phase='record' if recording else 'replay'
    print('MOVIE_PROGRESS',home.name,phase,'seconds',int(elapsed),'route_frames',tail.count('MOVIE_ROUTE route='),'avi_frames',tail.count('MOVIE_AVI '),flush=True);last_report=elapsed
   if elapsed>limit:
    os.killpg(p.pid,signal.SIGKILL);p.wait();break
   # Fail quickly on the old menu/argv failure rather than waiting 18 minutes.
   if not recording and elapsed>140:
    files=list(home.rglob('*console*.log'));tail=files[0].read_text(errors='replace') if files else ''
    if 'MOVIE_AVI ' not in tail:
     os.killpg(p.pid,signal.SIGKILL);p.wait();break
 rc=p.returncode
 for file in home.rglob('*console*.log'):shutil.copy2(file,log.with_suffix('.console.log'))
 assert rc==0,('GAME_FAILED',rc,str(log))
 text=log.with_suffix('.console.log').read_text(errors='replace')
 assert 'GLimp_Init() - could not load OpenGL subsystem' not in text
 return text
m.launch=launch

def geometry(retail):
 data=None
 for p in sorted(retail.iterdir()):
  if p.suffix.lower()=='.pk3':
   with zipfile.ZipFile(p) as z:
    for n in z.namelist():
     if n.lower()=='maps/escape1.bsp':data=z.read(n)
 assert data is not None
 def lump(i):
  o,n=struct.unpack_from('<ii',data,8+i*8);return data[o:o+n]
 planes=list(struct.iter_unpack('<4f',lump(2)));nodes=list(struct.iter_unpack('<9i',lump(3)));leaves=list(struct.iter_unpack('<12i',lump(4)))
 def cluster(p):
  n=0
  while n>=0:
   row=nodes[n];pl=planes[row[0]];n=row[1 if sum(pl[k]*p[k] for k in range(3))>=pl[3] else 2]
  return leaves[-1-n][0]
 report={}
 for name,r in ROUTES.items():
  bad=[];j=0
  for i in range(int(r[-1][0]*25)):
   t=i/25
   while j<len(r)-2 and t>r[j+1][0]:j+=1
   a,b=r[j:j+2];u=(t-a[0])/(b[0]-a[0]);p=[a[k]+u*(b[k]-a[k]) for k in range(1,4)]
   if cluster(p)<0:bad.append({'frame':i,'eye':p})
  report[name]={'frames':int(r[-1][0]*25),'invalid':bad}
 (m.OUT/'route-geometry-gate.json').write_text(json.dumps(report,indent=2))
 assert all(not r['invalid'] for r in report.values()),report
 print('MOVIE_ROUTE_GEOMETRY_PASS',flush=True)

if __name__=='__main__':
 if sys.argv[1]=='patch':m.patch_source(Path(sys.argv[2]).resolve())
 elif sys.argv[1]=='run':
  retail=Path(sys.argv[3]).resolve();geometry(retail);m.movies(Path(sys.argv[2]).resolve(),retail)
 else:raise SystemExit('patch SOURCE or run SOURCE RETAIL')
