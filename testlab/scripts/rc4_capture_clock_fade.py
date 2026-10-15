#!/usr/bin/env python3
"""Recording-only fixes grounded in Com_Frame and CG_Draw2D control flow.
Never changes the accepted production renderer or game source.
"""
from pathlib import Path
import importlib.util,sys,os,shutil
here=Path(__file__).resolve().parent
base=(here/'rc4_noclip_movies.py').read_text()
def replace(text,a,b):
 assert text.count(a)==1,(a[:100],text.count(a));return text.replace(a,b)
# Com_Frame executes Cbuf_Execute twice; wait counts command-buffer ticks.
base=replace(base,"'wait '+str(int(duration*25)+2)","'wait '+str(int(duration*50)+8)")
# HUD may be hidden only AFTER the native fade-complete scenario hook fires.
base=replace(base,"cmd=['set con_notifytime -1'","cmd=['set cg_draw2D 0','set con_notifytime -1'")
# The last RC_VIDEOFRAME is queued before demo EOF. Give it a screen flush
# before closing the AVI instead of losing that final queued frame at quit.
base=replace(base,"'+set','nextdemo','quit'","'+set','nextdemo','wait 4; stopvideo; quit'")
base=replace(base,"start=int(starts[0]);row=", "start=int(starts[0]);route_times=[int(x) for x in re.findall(r'MOVIE_ROUTE route=\\d+ frame=\\d+ time=(\\d+)',text)];assert route_times and max(route_times)-start>=int(duration*1000),('Route did not reach full simulation duration',name,start,max(route_times) if route_times else None);row=")
a=' for number,(name,keys) in enumerate(ROUTES.items(),1):\n'
base=replace(base,a,a+'  if os.environ.get("DW_MOVIE_ONLY") and name!=os.environ["DW_MOVIE_ONLY"]:continue\n')
(here/'rc4_movie_runtime_clock_fade.py').write_text(base)
driver=(here/'rc4_video_capture_driver.py').read_text()
driver=replace(driver,"with_name('rc4_noclip_movies.py')","with_name('rc4_movie_runtime_clock_fade.py')")
driver=replace(driver,"'set cg_draw2D 0'","'set cg_draw2D '+('1' if recording else '0')")
# A network demo records snapshots, not rendered pixels. Suppress backend work
# for recording ONLY. Both delivered movie passes explicitly render normally.
driver=replace(driver,"'set r_autoExposure 0','vid_restart'","'set r_autoExposure 0','set r_skipBackEnd '+('1' if recording else '0'),'vid_restart'")
driver=replace(driver,"if not recording and elapsed>140:","if recording and elapsed>150:\n    files=list(home.rglob('*console*.log'));tail=files[0].read_text(errors='replace') if files else ''\n    if 'MOVIE_ROUTE_START ' not in tail:\n     os.killpg(p.pid,signal.SIGKILL);p.wait();break\n   if not recording and elapsed>140:")
p=here/'rc4_driver_runtime_clock_fade.py';p.write_text(driver)
spec=importlib.util.spec_from_file_location('clock_fade_driver',p);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
if __name__=='__main__':
 if sys.argv[1]=='patch':
  source=Path(sys.argv[2]).resolve();t=(source/'SP/code/qcommon/common.c').read_text();frame=t[t.index('void Com_Frame'):];assert frame.count('Cbuf_Execute(')>=1 and 'Cbuf_Execute ();' in frame
  d.m.patch_source(source)
 elif sys.argv[1]=='run':
  retail=Path(sys.argv[3]).resolve();d.geometry(retail)
  okay=False
  try:
   d.m.movies(Path(sys.argv[2]).resolve(),retail);okay=True
  finally:
   # Persist our own recordings on failure for recovery. Never copy PK3s.
   runtime=Path.cwd()/'movie-private-runtime';out=d.m.OUT/'recording-recovery';out.mkdir(exist_ok=True)
   for p in runtime.rglob('*.dm_*'):
    if p.is_file() and p.parent.name=='demos':shutil.copy2(p,out/p.name)
   if not okay:
    for p in runtime.rglob('*.avi'):
     if p.is_file():shutil.copy2(p,out/(p.parent.parent.name+'-'+p.name))
    for p in runtime.rglob('*console*.log'):
     if p.is_file():shutil.copy2(p,out/(p.parent.parent.name+'-'+p.name))
 else:raise SystemExit('patch SOURCE or run SOURCE RETAIL')
