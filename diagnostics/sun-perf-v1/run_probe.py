#!/usr/bin/env python3
from pathlib import Path
import subprocess,os,shutil,json,re,statistics
runtime=Path('runtime').resolve(); evidence=Path('evidence'); evidence.mkdir(exist_ok=True)
exe=next(p for p in runtime.glob('iowolfsp*') if p.is_file()); exe.chmod(0o755)
summary={
 'acceptance_75fps':'NOT_TESTED_REAL_GPU_REQUIRED',
 'root_cause_hypothesis':'r_forceSun=1 enters legacy visible-sun CSM path and refreshes cascades 0/1/2 every rendered scene instead of the existing smart CSM reuse path',
 'stage_names':['cascade0','cascade1','cascade2','cascade3','other_draws','sun_volume','local_volume','fire_volume','postprocess_inclusive'],
 'candidate_modes':{'0':'production baseline','1':'skip sun CSM generation for RDF_SKYBOXPORTAL secondary views','2':'mode 1 + near/mid/far visible CSM cadence 1/2/4 with full-res cache reuse; level3 direction/area invalidated'},
 'notes':['Software llvmpipe evidence only; never treat measured FPS as acceptance.','Mode 2 serialized wall cost is not a GPU timer query.','Stage 8 includes stages 5-7; do not add them.','No candidate changes shadow-map size, filter, PCF, volumetric samples, MSAA, Bloom, ToneMap, Exposure, dlight shadows, or local volumetrics.']
}
blocks=[('off_base',0,0,20),('on_base_a',1,0,24),('on_portal_guard',1,1,24),('on_cache',1,2,40),('on_base_b',1,0,24),('off_base_end',0,0,20)]
for mode in (1,2):
 home=Path(f'home-probe-{mode}').resolve(); (home/'main').mkdir(parents=True,exist_ok=True)
 shutil.copy2(runtime/'main/cinematic.cfg',home/'main/autoexec.cfg')
 cfg=['set developer 0','set logfile 2','set cg_draw2D 0','set cg_drawGun 1','god','give all','weapon 3','wait 120','set com_maxfps 0','set timescale 0.05','set r_sunPerfLab 0','set r_sunPerfCandidate 0']
 for bi,(label,force,candidate,frames) in enumerate(blocks):
  cfg += [f'set r_forceSun {force}',f'set r_sunPerfCandidate {candidate}','wait 8',f'echo SUNPERF_BLOCK_BEGIN_{bi}_{label}_{force}_{candidate}',f'set r_sunPerfLab {mode}',f'wait {frames}','set r_sunPerfLab 0',f'echo SUNPERF_BLOCK_END_{bi}_{label}_{force}_{candidate}',f'screenshot sunperf_m{mode}_b{bi}_{label}']
 cfg+=['echo SUNPERF_COMPLETE','quit']
 (runtime/'main/probe.cfg').write_text('\n'.join(cfg)+'\n')
 args=[str(exe),'+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','dw_testAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight','768','+set','r_swapInterval','0','+set','com_maxfps','76','+set','logfile','2','+spdevmap','forest','+wait','60','+exec','probe.cfg']
 env=dict(os.environ,LIBGL_ALWAYS_SOFTWARE='1')
 with (evidence/f'process-{mode}.log').open('w') as out:
  result=subprocess.run(['xvfb-run','-a','timeout','-k','15s','1200s',*args],env=env,stdout=out,stderr=subprocess.STDOUT)
 logs=list(home.rglob('*console.log')); assert logs,'missing console log'
 text=logs[0].read_text(errors='replace'); (evidence/f'qconsole-{mode}.log').write_text(text)
 for shot in home.rglob('sunperf*.tga'): shutil.copy2(shot,evidence/shot.name)
 assert result.returncode==0,('runtime failed',mode,result.returncode)
 assert 'TESTLAB_GAMEPLAY_START requested=1' in text, 'gameplay not entered'
 assert 'SUNPERF_COMPLETE' in text
 assert re.search(r'HDRMSAA_PROD_INIT .*actualSamples=4',text),'MSAA not proven'
 assert re.search(r'GL_RENDERER:.*(llvmpipe|softpipe)',text,re.I),'record actual renderer before interpreting results'
 outblocks=[]
 for bi,(label,force,candidate,frames) in enumerate(blocks):
  begin=f'SUNPERF_BLOCK_BEGIN_{bi}_{label}_{force}_{candidate}'; end=f'SUNPERF_BLOCK_END_{bi}_{label}_{force}_{candidate}'
  segment=text.split(begin,1)[1].split(end,1)[0]
  rows=[dict(re.findall(r'(\w+)=([^\s]+)',line)) for line in segment.splitlines() if line.startswith('SUNPERF_FRAME ')]
  assert len(rows)>=max(12,frames-4),(mode,label,len(rows))
  rows=rows[4:]; valid={r['frame'] for r in rows}
  costs={str(i):[] for i in range(9)}; calls={str(i):[] for i in range(9)}
  for line in segment.splitlines():
   if not line.startswith('SUNPERF_STAGE '): continue
   row=dict(re.findall(r'(\w+)=([^\s]+)',line))
   if row['frame'] in valid: costs[row['stage']].append(int(row['serialized_wall_ms'])); calls[row['stage']].append(int(row['calls']))
  front=[dict(re.findall(r'(\w+)=([^\s]+)',line)) for line in segment.splitlines() if line.startswith('SUNPERF_FRONT ')]
  flags={}
  for r in front: flags[r.get('flags','?')]=flags.get(r.get('flags','?'),0)+1
  wall=[int(r['wall_ms']) for r in rows if int(r['wall_ms'])>0]
  med=statistics.median(wall) if wall else None
  outblocks.append({'block':bi,'label':label,'forceSun':force,'candidate':candidate,'frames':len(rows),'median_wall_ms':med,'software_fps_from_median':(1000.0/med if med else None),'front_scene_calls':len(front),'front_flags_histogram':flags,'mean_calls':{k:statistics.mean(v) if v else None for k,v in calls.items()},'median_serialized_wall_ms':{k:statistics.median(v) if v else None for k,v in costs.items()}})
 summary[f'mode_{mode}']=outblocks
 (evidence/'probe-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
