#!/usr/bin/env python3
"""Real Linux/Mesa map smoke. No claims of Windows/GPU FPS or full scene acceptance."""
from pathlib import Path
import subprocess,os,json,sys,shutil,hashlib,time,signal,datetime
from PIL import Image,ImageStat
src=Path(sys.argv[1]).resolve();retail=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parent;build=src/'SP/build/release-linux-x86_64'
exe=next(build.glob('iowolfsp.*'),None) or next(build.glob('ioWolfSP.*'))
runtime=Path.cwd()/('private-runtime-'+out.name);runtime.mkdir(exist_ok=True);(runtime/'main').mkdir(exist_ok=True)
for p in build.iterdir():
 if p.is_file():shutil.copy2(p,runtime/p.name)
for p in (build/'main').glob('*.so'):shutil.copy2(p,runtime/'main'/p.name)
for p in retail.glob('*'):
 if p.suffix.lower()=='.pk3':(runtime/'main'/p.name.lower()).symlink_to(p)
shutil.copy2(root/'payload/Main/darkwolf_ignition_rc_v0_6.pk3',runtime/'main/darkwolf_ignition_rc_v0_6.pk3')
shutil.copy2(root/'PRODUCTION_HIGH_QUALITY.cfg',runtime/'main/PRODUCTION_HIGH_QUALITY.cfg')
rows=[]
# Existing TestLab automation bypasses briefing/startcam only in this diagnostic copy.
for mapname in ['escape1','swf','dam','crypt1','assault','forest']:
 home=runtime/(mapname+'-home');home.mkdir(exist_ok=True)
 command=[str(runtime/exe.name),'+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+safe','+set','com_introplayed','1','+set','logfile','2','+set','dw_testAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','PRODUCTION_HIGH_QUALITY.cfg','+set','r_mode','-1','+set','r_customwidth','640','+set','r_customheight','480','+set','r_fullscreen','0','+set','r_forceSun','1','+set','s_initsound','0','+vid_restart','+set','dw_testlabSmokeCapture',mapname,'+spdevmap',mapname]
 started=time.time()
 with (out/(mapname+'-stdout.log')).open('w') as log:
  proc=subprocess.Popen(['xvfb-run','-a',*command],env={**os.environ,'LIBGL_ALWAYS_SOFTWARE':'1'},stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:rc=proc.wait(timeout=240)
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGKILL);proc.wait();rc=124
 logs=list(home.rglob('*console*.log'))
 for j,p in enumerate(logs):shutil.copy2(p,out/(mapname+f'-console-{j}.log'))
 shots=list(home.rglob('*.tga'));row={'map':mapname,'exit_code':rc,'elapsed_seconds':time.time()-started,'command':command,'status':'FAIL','scene':'spawn only; not calibrated table/railing route','hardware':'Linux Mesa llvmpipe, software rasterizer','resolution':[640,480],'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'binary_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in build.iterdir() if p.is_file()},'preset_sha256':hashlib.sha256((root/'PRODUCTION_HIGH_QUALITY.cfg').read_bytes()).hexdigest()}
 if shots:
  im=Image.open(shots[-1]).convert('RGB');im.save(out/(mapname+'.png'));pixels=list(im.getdata());n=len(pixels)
  black=sum(max(p)<8 for p in pixels)/n;white=sum(min(p)>247 for p in pixels)/n
  row.update(black_fraction=black,white_fraction=white)
  text='\n'.join(p.read_text(errors='replace') for p in logs)
  ready=(f'TESTLAB_FRAME_STATE stage=READY map={mapname}' in text and 'TESTLAB_CAPTURE_READY frames=32' in text and 'TESTLAB_GAMEPLAY_START requested=1' in text)
  row['gameplay_ready']=ready
  if rc==0 and ready and black<0.9 and white<0.9:row['status']='SMOKE_PASS'
 rows.append(row);(out/'runtime-results.json').write_text(json.dumps(rows,indent=2)+'\n')
# A rendered but mostly-white/black scene, shader failure, timeout or missing READY is a real failure.
if any(r['status']!='SMOKE_PASS' for r in rows):raise SystemExit('Runtime smoke failed; see per-map logs')
