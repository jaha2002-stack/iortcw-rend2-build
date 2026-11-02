#!/usr/bin/env python3
"""One-file CSM guard fix Win64 candidate: exact accepted Xlabs runtime, new renderer only."""
import argparse,io,zipfile,hashlib,struct,json
from pathlib import Path
H=lambda b: hashlib.sha256(b).hexdigest()
A='1ab999f0b0a994b5c2d41039a2c46195262c2378bfe14462e40bab580ce0c1da'
B='0b35294ea0c18cc3bb349c4fcc35a04b25659439694abe5de6d6a8b575270dbd'
R='77322a8bb82a67bab44632134b48a75050a565d48469b0826908790a758d9179'
G='52908cfeca0cf3d589ad8a84f083e100a4e2aa02757ee687d264946281947bcf'
NAME='DarkWolf_Rend2_Xlabs_40189858429_CSM_PrimaryAreaMask_CleanCandidate_Win64'
p=argparse.ArgumentParser()
p.add_argument('--base-artifact',required=True,type=Path)
p.add_argument('--renderer',required=True,type=Path)
p.add_argument('--proof',required=True,type=Path)
p.add_argument('--test-log',required=True,type=Path)
p.add_argument('--out',required=True,type=Path)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
assert H(a.base_artifact.read_bytes())==A
with zipfile.ZipFile(a.base_artifact) as z:
 assert z.testzip() is None
 names=[x for x in z.namelist() if x.endswith('_Win64.zip')]
 assert len(names)==1,names
 data=z.read(names[0]);assert H(data)==B
original={}
with zipfile.ZipFile(io.BytesIO(data)) as z:
 assert z.testzip() is None
 for info in z.infolist():
  if info.is_dir():continue
  parts=info.filename.split('/',1);assert len(parts)==2
  name=parts[1];assert '..' not in Path(name).parts and name not in original
  original[name]=z.read(info)
assert len(original)==22,len(original)
assert H(original['renderer_sp_rend2_x64.dll'])==R
assert H(original['Main/cgame_sp_x64.dll'])==G
re=a.renderer.read_bytes();assert re[:2]==b'MZ' and len(re)>2000000
pe=struct.unpack_from('<I',re,60)[0]
assert re[pe:pe+4]==b'PE\0\0' and struct.unpack_from('<H',re,pe+4)[0]==0x8664
assert H(re)!=R
assert b'dwSunTraceStart' not in re,'Instrumentation leaked into clean candidate'
assert b'r_forceSun' in re and b'r_ssgi' in re and b'r_dlightWorldContainment' in re
proof=json.loads(a.proof.read_text());assert proof['source_only_changed']==['SP/code/rend2/tr_scene.c']
log=a.test_log.read_text();assert 'DW_CSM_PRIMARY_MASK_NATIVE_REGRESSION_PASS' in log
files=dict(original)
files['renderer_sp_rend2_x64.dll']=re
files['docs/CSM_PRIMARY_AREAMASK_CHANGE.json']=json.dumps({**proof,'parent_GitHub_run':40189858429,
  'parent_renderer_sha256':R,'new_renderer_sha256':H(re),
  'unmodified_cgame_sha256':G,'quality_and_cvars_unchanged':True,
  'windows_GPU_visual_and_fps_acceptance':'PENDING_USER',
  'source_change':'Only the CSM invalidation state in tr_scene.c; no timer probes or new CVar'},indent=2).encode()
files['docs/CSM_PRIMARY_MASK_NATIVE_TESTS.txt']=log.encode()
files['README_CSM_AREAMASK_FIX_RU.txt']=('DarkWolf Rend2 clean Win64 candidate from verified Xlabs run 40189858429.\n'
  'The renderer_sp_rend2_x64.dll has a single source change in tr_scene.c: compare\n'
  'only primary-world areamask against the prior primary-world view, preventing\n'
  'skybox portal scenes from causing full CSM re-prime on every game frame.\n'
  'Full real-world visibility changes STILL invalidate all cascades.\n'
  'Source cadence 1 / 2 / 4, distant cascade on invalidation, PCF13, MSAA4, HDR,\n'
  'SSGI, volumetrics, Xlabs Tesla doors, visuals and all other binaries unchanged.\n'
  'This is a CLEAN CODE candidate, not yet accepted on real Windows hardware.\n'
  'Run existing original launcher, compare Escape1 and Trainyard FPS and shadow\n'
  'stability near doors, after teleport and view changes, then Assault control.\n'
  'The original source game retail pak*.pk3 are NOT distributed.\n').encode()
files.pop('docs/SHA256SUMS.txt')
files['docs/SHA256SUMS.txt']=''.join(H(b)+'  '+k+'\n' for k,b in sorted(files.items())).encode()
for k,b in original.items():
 if k not in ('renderer_sp_rend2_x64.dll','docs/SHA256SUMS.txt'):assert files[k]==b,k
out=a.out/(NAME+'.zip')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
 for k,b in sorted(files.items()):
  info=zipfile.ZipInfo(NAME+'/'+k,date_time=(2026,10,26,0,0,0))
  info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
  z.writestr(info,b)
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for line in z.read(NAME+'/docs/SHA256SUMS.txt').decode().splitlines():
  h,k=line.split('  ',1);assert H(z.read(NAME+'/'+k))==h,k
manifest={'status':'CLEAN_WIN64_CSM_SOURCE_GUARD_CANDIDATE','parent_run':40189858429,
 'only_modified_game_binary':'renderer_sp_rend2_x64.dll','renderer_sha256':H(re),
 'release_sha256':H(out.read_bytes()),'C_regression_tests':'PASS',
 'real_Windows_GPU_acceptance':'PENDING_USER'}
(a.out/'CSM_PRIMARY_AREA_RELEASE_VALIDATION.json').write_text(json.dumps(manifest,indent=2)+'\n')
(a.out/(out.name+'.sha256')).write_text(H(out.read_bytes())+'  '+out.name+'\n')
print('DW_CSM_PRIMARY_MASK_CLEAN_CANDIDATE_PACKAGE_PASS',out,H(out.read_bytes()),flush=True)
