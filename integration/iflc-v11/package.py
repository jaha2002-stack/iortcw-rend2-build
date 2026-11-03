#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,os,shutil,zipfile
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('evidence',type=Path);p.add_argument('dist',type=Path);a=p.parse_args()
kit=Path(__file__).resolve().parent
files=list((a.source/'SP/build').rglob('renderer_sp_rend2_x64.dll'));assert len(files)==1
binary=files[0];raw=binary.read_bytes();assert b'r_iflcFixtureTestBypass' not in raw and b'dw_fl_test_audit' not in raw
old=json.loads((a.evidence/'IFLC_SOURCE_SHA256.json').read_text())
now={str(p.relative_to(a.source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.source/'SP/code').rglob('*') if p.is_file()}
changed=sorted(p for p in set(old)|set(now) if old.get(p)!=now.get(p))
assert changed==['SP/code/rend2/tr_iflc.inc','SP/code/rend2/tr_iflc_fixture.inc','SP/code/rend2/tr_local.h','SP/code/rend2/tr_main.c','SP/code/rend2/tr_world.c'],changed
(a.evidence/'IFLC_V11_SOURCE_SHA256.json').write_text(json.dumps(now,indent=2)+'\n')
name='DarkWolf_IFLC_V11_GLOBAL_SELF_SHADOW_FROM_41408153237_Win64_TEST';stage=a.dist/name;stage.mkdir(parents=True,exist_ok=True)
shutil.copy2(binary,stage/binary.name);shutil.copy2(kit/'README_RU.md',stage/'README_V11_RU.md');shutil.copy2(kit.parent/'iflc-v1/README_RU.md',stage/'README_COMMANDS_V1_RU.md')
for n in ('DW_IFLC_V1_ENABLE.cfg','DW_IFLC_V1_DISABLE.cfg'):shutil.copy2(kit.parent/'iflc-v1'/n,stage/n)
for n in ('IFLC_SOURCE_PROOF.json','IFLC_V11_SOURCE_PROOF.json'):shutil.copy2(a.evidence/n,stage/n)
status={'status':'TEST_CANDIDATE','base_run':41408153237,'parent_iflc_run':41691075610,'build_run':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA'),'renderer_sha256':hashlib.sha256(raw).hexdigest(),'visual_acceptance':'See separate Crypt1/Crypt2 evidence and manual report','diagnostic_hooks_in_distributed_dll':False,'production_changed_files_vs_v1':changed}
(stage/'BUILD_STATUS.json').write_text(json.dumps(status,indent=2)+'\n')
zpath=a.dist/(name+'.zip')
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(stage.iterdir()):z.write(p,p.name)
(a.dist/'SHA256SUMS.txt').write_text(hashlib.sha256(zpath.read_bytes()).hexdigest()+'  '+zpath.name+'\n'+status['renderer_sha256']+'  '+binary.name+'\n')
print('IFLC_V11_WIN64_TEST_PACKAGE_READY',str(zpath),flush=True)
