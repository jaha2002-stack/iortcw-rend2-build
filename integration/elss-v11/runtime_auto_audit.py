#!/usr/bin/env python3
from pathlib import Path
import argparse,tempfile,shutil,subprocess,os,signal,json,re
def run(retail,out):
    out.mkdir(parents=True,exist_ok=True);runtime=Path(tempfile.mkdtemp(prefix='elss11-audit-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
    build=Path('source/SP/build/release-linux-x86_64')
    for p in build.iterdir():
        if p.is_file():shutil.copy2(p,runtime/p.name)
    for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
    for p in retail.iterdir():
        if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
    (main/'SETUP.cfg').write_text('\n'.join(['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_dwElectricLightControl 1','set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set con_notifytime -1'])+'\n')
    (main/'TEST.cfg').write_text('\n'.join(['god','notarget','wait 80','dw_el_v11_audit 107','wait 8','echo ELSS11_AUDIT_DONE','quit'])+'\n')
    exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
    args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe','+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','SETUP.cfg','+set','dw_proofScenario','TEST.cfg','+spdevmap','church']
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))};env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
    with (out/'stdout.log').open('w') as log:
      p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
      try:rc=p.wait(timeout=900)
      except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
    text=''
    for i,p in enumerate(sorted(home.rglob('*console*.log'))):
      shutil.copy2(p,out/f'console-{i}.log');text+=p.read_text(errors='replace')+'\n'
    lines=[l for l in text.splitlines() if l.startswith('ELSS11_AUDIT_')]
    report={'exit':rc,'lines':lines,'done':'ELSS11_AUDIT_DONE' in text};(out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print('\n'.join(lines));assert rc==0 and report['done'] and lines
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('retail',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.retail.resolve(),a.out.resolve())
