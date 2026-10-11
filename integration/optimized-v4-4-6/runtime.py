#!/usr/bin/env python3
"""Real Linux/Mesa map smoke. No claims of Windows/GPU FPS or full scene acceptance."""
from pathlib import Path
import subprocess,os,json,sys,shutil,hashlib,time,signal,datetime,re
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
# Derive the existing ordinary Quality profile for a separate compatibility test.
# It is not part of the release preset or a performance comparison.
ui=(src/'SP/code/ui/ui_main.c').read_text()
block=ui.split('static const darkWolfProfileCvar_t s_darkWolfQuality[] = {',1)[1].split('};',1)[0]
quality=(root/'PRODUCTION_HIGH_QUALITY.cfg').read_text()+'\n'+''.join(f'seta {k} "{v}"\n' for k,v in re.findall(r'\{ "([^" ]+)", "([^" ]+)" \}',block))+'seta ui_darkwolfProfile "1"\n'
(runtime/'main/TESTLAB_QUALITY.cfg').write_text(quality)
(out/'TESTLAB_QUALITY.cfg').write_text(quality)
rows=[]
# Existing TestLab automation bypasses briefing/startcam only in this diagnostic copy.
for mapname,profile in [(m,'high') for m in ['escape1','swf','dam','crypt1','assault','forest']]+[('escape1','quality')]:
 tag=mapname if profile=='high' else mapname+'-'+profile
 cfg='PRODUCTION_HIGH_QUALITY.cfg' if profile=='high' else 'TESTLAB_QUALITY.cfg'
 home=runtime/(tag+'-home');home.mkdir(exist_ok=True)
 command=[str(runtime/exe.name),'+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+safe','+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_testAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec',cfg,'+set','r_mode','-1','+set','r_customwidth','640','+set','r_customheight','480','+set','r_fullscreen','0','+set','r_forceSun','1','+set','s_initsound','0','+vid_restart','+set','dw_testlabSmokeCapture',tag,'+spdevmap',mapname]
 started=time.time()
 with (out/(tag+'-stdout.log')).open('w') as log:
  proc=subprocess.Popen(['xvfb-run','-a',*command],env={**os.environ,'LIBGL_ALWAYS_SOFTWARE':'1'},stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:rc=proc.wait(timeout=240)
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGKILL);proc.wait();rc=124
 logs=list(home.rglob('*console*.log'))
 for j,p in enumerate(logs):shutil.copy2(p,out/(tag+f'-console-{j}.log'))
 shots=list(home.rglob('*.tga'));row={'map':mapname,'profile':profile,'exit_code':rc,'elapsed_seconds':time.time()-started,'command':command,'status':'FAIL','scene':'spawn only; not calibrated table/railing route','hardware':'Linux Mesa llvmpipe, software rasterizer','resolution':[640,480],'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'binary_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in build.iterdir() if p.is_file()},'preset_sha256':hashlib.sha256((runtime/'main'/cfg).read_bytes()).hexdigest()}
 if shots:
  im=Image.open(shots[-1]).convert('RGB');im.save(out/(tag+'.png'));pixels=list(im.getdata());n=len(pixels)
  black=sum(max(p)<8 for p in pixels)/n;white=sum(min(p)>247 for p in pixels)/n
  row.update(black_fraction=black,white_fraction=white)
  text='\n'.join(p.read_text(errors='replace') for p in logs)
  ready=(f'TESTLAB_FRAME_STATE stage=READY map={mapname}' in text and bool(re.search(r'TESTLAB_CAPTURE_READY frames=\d+ fadeRate=0',text)) and 'TESTLAB_GAMEPLAY_START requested=1' in text)
  row['gameplay_ready']=ready
  expected=dict(re.findall(r'seta ([^ ]+) "([^" ]+)"',(runtime/'main'/cfg).read_text()));expected['r_forceSun']='1'
  actual=dict(re.findall(r'TESTLAB_CVAR name=(\w+) value=([^\s]+)',text))
  keys=['r_picmip','r_staticPromoteMaxLights','r_dlightShadowMaxLights','r_ext_framebuffer_multisample','r_shadowMapSize','r_forceSun','r_ssgi','r_volumetricLocal','r_volumetricSun','r_volumetricFire','r_pbr']
  row['actual_cvars']=actual;row['cvar_mismatches']={k:{'expected':expected[k],'actual':actual.get(k)} for k in keys if actual.get(k)!=expected[k]}
  if rc==0 and ready and black<0.9 and white<0.9 and not row['cvar_mismatches']:row['status']='SMOKE_PASS' 
 rows.append(row);(out/'runtime-results.json').write_text(json.dumps(rows,indent=2)+'\n')
# A rendered but mostly-white/black scene, shader failure, timeout or missing READY is a real failure.
if any(r['status']!='SMOKE_PASS' for r in rows):raise SystemExit('Runtime smoke failed; see per-map logs')
