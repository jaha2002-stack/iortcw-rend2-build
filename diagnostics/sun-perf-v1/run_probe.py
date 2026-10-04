#!/usr/bin/env python3
from pathlib import Path
import subprocess,os,shutil,json,re,statistics
runtime=Path('runtime').resolve(); evidence=Path('evidence'); evidence.mkdir(exist_ok=True)
exe=next(p for p in runtime.glob('iowolfsp*') if p.is_file());exe.chmod(0o755)
summary={'acceptance_75fps':'NOT_TESTED_REAL_GPU_REQUIRED','root_cause':'UNCONFIRMED','stage_names':['cascade0','cascade1','cascade2','cascade3','other_draws','sun_volume','local_volume','fire_volume','postprocess_inclusive'],'notes':['Software renderer evidence only. Mode 2 serialized wall cost is not GPU timer duration.','Stage 8 includes stages 5-7; do not add them.','A/B changes forceSun only; off state may retain map-defined sun.']}
for mode in (1,2):
 home=Path(f'home-probe-{mode}').resolve();home.mkdir(exist_ok=True)
 cfg=['set developer 0','set logfile 1','set cg_draw2D 0','set cg_drawGun 1','god','give all','weapon 3','wait 60','set timescale 0.0001','set r_sunPerfLab 0']
 for block,force in enumerate([0,1,1,0]):
  cfg += [f'set r_forceSun {force}','wait 16',f'echo SUNPERF_BLOCK_BEGIN_{block}_{force}',f'set r_sunPerfLab {mode}','wait 32','set r_sunPerfLab 0',f'echo SUNPERF_BLOCK_END_{block}_{force}',f'screenshot sunperf_m{mode}_b{block}_sun{force}']
 cfg+=['echo SUNPERF_COMPLETE','quit']
 (runtime/'main/probe.cfg').write_text('\n'.join(cfg)+'\n')
 args=[str(exe),'+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','dw_testAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','cinematic.cfg','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight','768','+set','r_swapInterval','0','+set','com_maxfps','0','+spdevmap','forest','+wait','60','+exec','probe.cfg']
 env=dict(os.environ,LIBGL_ALWAYS_SOFTWARE='1')
 with (evidence/f'process-{mode}.log').open('w') as out:
  result=subprocess.run(['xvfb-run','-a','timeout','-k','15s','900s',*args],env=env,stdout=out,stderr=subprocess.STDOUT)
 logs=list(home.rglob('*console.log')); assert logs,'missing console log'
 text=logs[0].read_text(errors='replace');(evidence/f'qconsole-{mode}.log').write_text(text)
 for shot in home.rglob('sunperf*.tga'):shutil.copy2(shot,evidence/shot.name)
 assert result.returncode==0,('runtime failed',mode,result.returncode)
 assert 'SUNPERF_COMPLETE' in text
 assert re.search(r'HDRMSAA_PROD_INIT .*actualSamples=4',text),'MSAA not proven'
 assert re.search(r'GL_RENDERER:.*(llvmpipe|softpipe)',text,re.I),'record actual renderer before interpreting results'
 blocks=[]
 for block,force in enumerate([0,1,1,0]):
  segment=text.split(f'SUNPERF_BLOCK_BEGIN_{block}_{force}',1)[1].split(f'SUNPERF_BLOCK_END_{block}_{force}',1)[0]
  rows=[dict(re.findall(r'(\w+)=([^\s]+)',line)) for line in segment.splitlines() if line.startswith('SUNPERF_FRAME ')]
  assert len(rows)>=24,(mode,block,len(rows))
  # Drop 4 frames at the boundary. Screenshots and warmup are outside measured windows.
  rows=rows[4:]; valid={r['frame'] for r in rows}
  costs={str(i):[] for i in range(9)};calls={str(i):[] for i in range(9)}
  for line in segment.splitlines():
   if not line.startswith('SUNPERF_STAGE '):continue
   row=dict(re.findall(r'(\w+)=([^\s]+)',line))
   if row['frame'] in valid:costs[row['stage']].append(int(row['serialized_wall_ms']));calls[row['stage']].append(int(row['calls']))
  blocks.append({'block':block,'forceSun':force,'frames':len(rows),'median_wall_ms':statistics.median(int(r['wall_ms']) for r in rows),'mean_calls':{k:statistics.mean(v) if v else None for k,v in calls.items()},'median_serialized_wall_ms':{k:statistics.median(v) if v else None for k,v in costs.items()}})
 summary[f'mode_{mode}']=blocks
 (evidence/'probe-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
