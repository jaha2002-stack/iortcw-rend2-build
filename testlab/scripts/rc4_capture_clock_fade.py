#!/usr/bin/env python3
"""Recording-only native clock, startup and evidence corrections.
Never changes the accepted production renderer or game source.
"""
from pathlib import Path
import importlib.util,sys,os,shutil,re
here=Path(__file__).resolve().parent
base=(here/'rc4_noclip_movies.py').read_text()
def replace(text,a,b):
 assert text.count(a)==1,(a[:100],text.count(a));return text.replace(a,b)
# The C variable is com_fixedtime, but its registered console name is fixedtime.
# Setting com_fixedtime merely created an unused cvar and made wait wall-clock
# dependent. The command inside the loaded cheat map sets the real clock.
assert 'com_fixedtime' in base
base=base.replace('com_fixedtime','fixedtime')
# Com_Frame executes Cbuf_Execute twice; wait counts command-buffer ticks.
base=replace(base,"'wait '+str(int(duration*25)+2)","'wait '+str(int(duration*50)+8)")
base=replace(base,"cmd=['set con_notifytime -1'","cmd=['set cg_draw2D 0','set con_notifytime -1'")
# Flush the final queued native video frame before explicitly closing AVI.
base=replace(base,"'+set','nextdemo','quit'","'+set','nextdemo','wait 4; stopvideo; quit'")
base=replace(base,"start=int(starts[0]);row=", "start=int(starts[0]);route_times=[int(x) for x in re.findall(r'MOVIE_ROUTE route=\\d+ frame=\\d+ time=(\\d+)',text)];assert route_times and max(route_times)-start>=int(duration*1000),('Route did not reach full simulation duration',name,start,max(route_times) if route_times else None);row=")
# Existing debug lines can contain literal backslash-n, joining the following
# scene record onto another line. Match records, not only physical line starts.
base=replace(base,'for line in text.splitlines():',"for line in re.findall(r'MOVIE_(?:SCENE|AVI) [^\\r\\n]+',text):")
base=replace(base,'selected=frames[first_index:first_index+count]',"selected=frames[first_index:first_index+count]\n   assert all(f['scene'] is not None and f['scene']['time']==f['time'] for f in selected),'AVI frame scene clock mismatch'\n   assert len({f['scene']['camera'] for f in selected})>count//2,'Camera trajectory is static or truncated'")
a=' for number,(name,keys) in enumerate(ROUTES.items(),1):\n'
base=replace(base,a,a+'  if os.environ.get("DW_MOVIE_ONLY") and name!=os.environ["DW_MOVIE_ONLY"]:continue\n')
(here/'rc4_movie_runtime_clock_fade.py').write_text(base)
driver=(here/'rc4_video_capture_driver.py').read_text()
assert 'com_fixedtime' in driver
driver=driver.replace('com_fixedtime','fixedtime')
driver=replace(driver,"with_name('rc4_noclip_movies.py')","with_name('rc4_movie_runtime_clock_fade.py')")
driver=replace(driver,"'set cg_draw2D 0'","'set cg_draw2D '+('1' if recording else '0')")
# Network demo recording needs snapshots, not a rendered framebuffer.
# Both actual delivered video passes explicitly render with backend enabled.
driver=replace(driver,"'set r_autoExposure 0','vid_restart'","'set r_autoExposure 0','set r_skipBackEnd '+('1' if recording else '0'),'vid_restart'")
driver=replace(driver,"if not recording and elapsed>140:","if recording and elapsed>150:\n    files=list(home.rglob('*console*.log'));tail=files[0].read_text(errors='replace') if files else ''\n    if 'MOVIE_ROUTE_START ' not in tail:\n     os.killpg(p.pid,signal.SIGKILL);p.wait();break\n   if not recording and elapsed>140:")
p=here/'rc4_driver_runtime_clock_fade.py';p.write_text(driver)
spec=importlib.util.spec_from_file_location('clock_fade_driver',p);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
if __name__=='__main__':
 if sys.argv[1]=='patch':
  source=Path(sys.argv[2]).resolve();t=(source/'SP/code/qcommon/common.c').read_text();frame=t[t.index('void Com_Frame'):]
  assert re.search(r'com_fixedtime\s*=\s*Cvar_Get\(\s*"fixedtime"',t),'Native fixedtime registration changed'
  assert frame.count('Cbuf_Execute(')>=1 and 'Cbuf_Execute ();' in frame
  d.m.patch_source(source)
 elif sys.argv[1]=='run':
  retail=Path(sys.argv[3]).resolve();d.geometry(retail)
  okay=False
  try:
   d.m.movies(Path(sys.argv[2]).resolve(),retail);okay=True
  finally:
   # Only our own demo/video recordings are exported, never commercial PK3s.
   runtime=Path.cwd()/'movie-private-runtime';out=d.m.OUT/'recording-recovery';out.mkdir(exist_ok=True)
   for p in runtime.rglob('*.dm_*'):
    if p.is_file() and p.parent.name=='demos':shutil.copy2(p,out/p.name)
   if not okay:
    for p in runtime.rglob('*.avi'):
     if p.is_file():shutil.copy2(p,out/(p.parent.parent.name+'-'+p.name))
    for p in runtime.rglob('*console*.log'):
     if p.is_file():shutil.copy2(p,out/(p.parent.parent.name+'-'+p.name))
 else:raise SystemExit('patch SOURCE or run SOURCE RETAIL')
