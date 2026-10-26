#!/usr/bin/env python3
"""Exact accepted #40294211216 + one replaced renderer, self-verifying clean Win64."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import argparse, hashlib, json, struct
H=lambda b:hashlib.sha256(b).hexdigest()
BASE_SHA='cabbf853370ba544cc13eca4467dba3be855cf9525b36bd610620e1777a2ead5'
BASE_DLL='11a67525c3f930165391912aced7358d8f827a1669700230c6b4672a253cf2f0'
CGAME='52908cfeca0cf3d589ad8a84f083e100a4e2aa02757ee687d264946281947bcf'
SKY_SRC='41247728dc418a4edd7c9a3ab84a43e9539983a71005b2d148ae761c634d7bc7'
ROOT='DarkWolf_Rend2_Xlabs_CSM_Fix_Volumetric_SunRay_CascadeEdge_AA_Win64/'
OUT='DarkWolf_Rend2_Sky_MSAA_Coverage_Clean_Exact40294211216_Win64'
p=argparse.ArgumentParser()
p.add_argument('--base',type=Path,required=True)
p.add_argument('--renderer',type=Path,required=True)
p.add_argument('--proof',type=Path,required=True)
p.add_argument('--tests',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
assert H(a.base.read_bytes())==BASE_SHA
original={}
with ZipFile(a.base) as z:
 assert z.testzip() is None
 for item in z.infolist():
  if item.is_dir():continue
  assert item.filename.startswith(ROOT),(item.filename,ROOT)
  rel=item.filename[len(ROOT):]
  assert rel and '..' not in Path(rel).parts and rel not in original
  original[rel]=z.read(item)
assert len(original)==28,len(original)
assert H(original['renderer_sp_rend2_x64.dll'])==BASE_DLL
assert H(original['Main/cgame_sp_x64.dll'])==CGAME
assert all(x in original for x in ('docs/VOLUMETRIC_SUN_EDGE_FIX_PROVENANCE.json','docs/CSM_PRIMARY_AREAMASK_CHANGE.json','Main/darkwolf_ignition_rc_v0_6.pk3'))
dll=a.renderer.read_bytes()
assert dll[:2]==b'MZ' and len(dll)>2_000_000
pe=struct.unpack_from('<I',dll,0x3c)[0]
assert dll[pe:pe+4]==b'PE\0\0'
assert struct.unpack_from('<H',dll,pe+4)[0]==0x8664
assert H(dll)!=BASE_DLL
for token in (b'r_forceSun',b'r_ssgi',b'r_volumetricSun',b'r_dlightWorldContainment'):
 assert token in dll,token
assert b'DARKWOLF_SSGI_FIELD_DIAG_V2' not in dll
assert b'dwSunTraceStart' not in dll
proof=json.loads(a.proof.read_text())
assert proof['marker']=='DARKWOLF_SKY_MSAA_COVERAGE_GUARD_V1'
assert proof['patched_src_sha256']==SKY_SRC
assert proof['modified_source']==['SP/code/rend2/tr_sky.c']
tests=a.tests.read_text()
assert 'DW_SKY_MSAA_COVERAGE_REGRESSION_PASS' in tests
files=dict(original)
files['renderer_sp_rend2_x64.dll']=dll
files['README_SKY_MSAA_COVERAGE_GUARD_RU.txt']=(
 'DARKWOLF REND2 SKY MSAA COVERAGE GUARD - CLEAN WIN64 CANDIDATE\n'
 'Exact user-accepted base: GitHub Actions #40294211216.\n'
 'Source: only SP/code/rend2/tr_sky.c. When rendering sky into main MSAA FBO,\n'
 'temporarily use pixel-center sky coverage and restore GL_MULTISAMPLE.\n'
 'Sky mesh, cloud UV, fog, SSGI, CSM Primary AreaMask, volumetrics,\n'
 'Tesla, shadowmask, LUT, HDR, image fidelity and all configs are unchanged.\n'
 'Original game files remain byte-identical except renderer_sp_rend2_x64.dll\n'
 'and docs/SHA256SUMS.txt. No new commands or visual quality flags are needed.\n'
 'Back up original DLL. Replace DLL when game is closed. Test identical\n'
 'Trainyard and Factory sky with MSAA 8x, Escape1 CSM, Factory lamps, Assault.\n'
 'This is a CI-verified clean candidate until Windows GPU visual acceptance.\n'
 'Original retail pak*.pk3 files must be supplied by the game owner.\n').encode()
files['docs/SKY_MSAA_COVERAGE_SOURCE_PROOF.json']=json.dumps({**proof,
 'parent_accepted_run':40294211216,'parent_zip_sha256':BASE_SHA,
 'parent_dll_sha256':BASE_DLL,'new_dll_sha256':H(dll),
 'only_changed_original_game_binary':'renderer_sp_rend2_x64.dll',
 'user_visual_validation':'PENDING'},indent=2).encode()
files['docs/SKY_MSAA_COVERAGE_TESTS.txt']=tests.encode()
files.pop('docs/SHA256SUMS.txt',None)
files['docs/SHA256SUMS.txt']=''.join(H(v)+'  '+n+'\n' for n,v in sorted(files.items())).encode()
for name,content in original.items():
 if name not in ('renderer_sp_rend2_x64.dll','docs/SHA256SUMS.txt'):
  assert files[name]==content,name
assert len(files)==len(original)+3
target=a.out/(OUT+'.zip')
with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=7) as z:
 for name,content in sorted(files.items()):
  info=ZipInfo(OUT+'/'+name,date_time=(2026,10,26,0,0,0))
  info.compress_type=ZIP_DEFLATED;info.external_attr=0o100644<<16
  z.writestr(info,content)
with ZipFile(target) as z:
 assert z.testzip() is None
 for line in z.read(OUT+'/docs/SHA256SUMS.txt').decode().splitlines():
  digest,name=line.split('  ',1)
  assert H(z.read(OUT+'/'+name))==digest,name
result={'status':'CI_CLEAN_CANDIDATE_PENDING_REAL_GPU_TEST',
 'user_accepted_base_run':40294211216,
 'base_zip_sha256':BASE_SHA,
 'output_sha256':H(target.read_bytes()),
 'new_renderer_sha256':H(dll),
 'only_replaced_binary':'renderer_sp_rend2_x64.dll',
 'all_other_game_files_byte_exact':True,
 'new_cvars':0,'full_scene_msaa_remains_enabled':True,'sky_MSAA_coverage':'DISABLED_FOR_SKY_ONLY','Trainyard_Factory_sky_visual_A_B':'PENDING_USER'}
(a.out/'SKY_MSAA_RELEASE_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
(a.out/(target.name+'.sha256')).write_text(H(target.read_bytes())+'  '+target.name+'\n')
print('DW_SKY_MSAA_COVERAGE_CLEAN_WIN64_PACKAGE_PASS',target,H(target.read_bytes()),H(dll),flush=True)
