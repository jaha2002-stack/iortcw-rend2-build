#!/usr/bin/env python3
"""Execute existing calibrated TestLab scenarios; preserve all analyzer failures."""
from pathlib import Path
import subprocess,sys,json,os,signal,shutil,time,hashlib
from PIL import Image
src=Path(sys.argv[1]).resolve();smoke=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parent;repo=root.parent.parent
runtime=Path.cwd()/('private-runtime-'+smoke.name)
probe=next(smoke.glob('escape1-console-*.log'))
smoke_row=json.loads((smoke/'runtime-results.json').read_text())[0]
rows=[]
for scenario in ['ring','table-baseline','table-exclude742','table-exclude744']:
 cfg=runtime/'main'/('testlab-'+scenario+'.cfg')
 if scenario=='ring':
  subprocess.run([sys.executable,str(repo/'testlab/scripts/make_ring_cfg.py'),str(probe),str(repo/'testlab/scenarios/escape1_staticpromote.json'),str(cfg)],check=True)
 else:
  label=scenario.removeprefix('table-');exclude='-1' if label=='baseline' else label.removeprefix('exclude')
  subprocess.run([sys.executable,str(repo/'testlab/scripts/make_table_cluster_cfg.py'),str(probe),str(cfg),'--label',label,'--exclude-shadow-fixture',exclude],check=True)
 home=runtime/(scenario+'-home');home.mkdir()
 dest=out/scenario;dest.mkdir();(dest/'screenshots').mkdir()
 shutil.copy2(cfg,dest/cfg.name)
 command=smoke_row['command'].copy();command[command.index('fs_homepath')+1]=str(home)
 command[-2:-2]=['+set','dw_testlabScenario',cfg.name]
 started=time.time()
 with (dest/'stdout.log').open('w') as log:
  proc=subprocess.Popen(['xvfb-run','-a',*command],env={**os.environ,'LIBGL_ALWAYS_SOFTWARE':'1'},stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:rc=proc.wait(timeout=1800 if scenario=='ring' else 600)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait();rc=124
 logs=list(home.rglob('*console*.log'));text=''
 if logs:
  shutil.copy2(logs[0],dest/'qconsole.log');text=logs[0].read_text(errors='replace')
 shots=list(home.rglob('*.tga'))
 for shot in shots:
  shutil.copy2(shot,dest/'screenshots'/shot.name)
  Image.open(shot).convert('RGB').save(dest/'screenshots'/(shot.stem+'.png'))
 expected=128 if scenario=='ring' else 16
 row={'scenario':scenario,'exit_code':rc,'screenshots':len(shots),'expected':expected,'elapsed_seconds':time.time()-started,'capture_ready':'TESTLAB_CAPTURE_READY frames=' in text,'status':'CAPTURED' if rc==0 and len(shots)==expected else 'FAIL','command':command,'preset_sha256':smoke_row['preset_sha256'],'binary_sha256':smoke_row['binary_sha256'],'hardware':smoke_row['hardware'],'resolution':smoke_row['resolution']}
 if scenario=='ring':
  with (dest/'analyzer-stdout.log').open('w') as log:
   analyzed=subprocess.run([sys.executable,str(repo/'testlab/scripts/analyze_runtime.py'),str(dest/'qconsole.log'),str(repo/'testlab/scenarios/escape1_staticpromote.json'),str(dest/'analysis.json')],stdout=log,stderr=subprocess.STDOUT)
  row['analyzer_exit_code']=analyzed.returncode
 rows.append(row);(out/'scenario-results.json').write_text(json.dumps(rows,indent=2)+'\n')
# Historical exclusion analyzer expects these directory names.
cluster=out/'table-cluster';cluster.mkdir()
for label in ['baseline','exclude742','exclude744']:(cluster/label).symlink_to(out/('table-'+label),target_is_directory=True)
with (out/'table-analyzer-stdout.log').open('w') as log:
 analyzed=subprocess.run([sys.executable,str(repo/'testlab/scripts/analyze_table_ab.py'),str(cluster),str(out/'table-analysis.json')],stdout=log,stderr=subprocess.STDOUT)
(out/'table-analyzer-exit-code.txt').write_text(str(analyzed.returncode)+'\n')
# Capture failures are blocking. Semantic analyzer results are evaluated A/B later.
if any(r['status']!='CAPTURED' for r in rows):raise SystemExit('Scenario capture failure')
