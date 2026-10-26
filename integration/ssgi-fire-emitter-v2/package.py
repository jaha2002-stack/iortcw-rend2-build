#!/usr/bin/env python3
"""Immutable accepted #40294211216 Win64 game + one rebuilt SSGI renderer."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import argparse, hashlib, json, struct
H=lambda b: hashlib.sha256(b).hexdigest()
BASE='cabbf853370ba544cc13eca4467dba3be855cf9525b36bd610620e1777a2ead5'
BASE_DLL='11a67525c3f930165391912aced7358d8f827a1669700230c6b4672a253cf2f0'
CGAME='52908cfeca0cf3d589ad8a84f083e100a4e2aa02757ee687d264946281947bcf'
ROOT='DarkWolf_Rend2_Xlabs_CSM_Fix_Volumetric_SunRay_CascadeEdge_AA_Win64/'
NAME='DarkWolf_Rend2_Clean_Production_SSGI_EmissiveFire_V2_CSM_Volumetric_Xlabs_Win64'
p=argparse.ArgumentParser()
p.add_argument('--base',required=True,type=Path)
p.add_argument('--dll',required=True,type=Path)
p.add_argument('--proof',required=True,type=Path)
p.add_argument('--test-log',required=True,type=Path)
p.add_argument('--out',required=True,type=Path)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
assert H(a.base.read_bytes())==BASE, 'base archive NOT user-accepted #40294211216'
base={}
with ZipFile(a.base) as z:
 assert z.testzip() is None
 for item in z.infolist():
  if item.is_dir():continue
  assert item.filename.startswith(ROOT)
  name=item.filename[len(ROOT):]
  assert name and '..' not in Path(name).parts and name not in base
  base[name]=z.read(item)
assert len(base)==28,len(base)
assert H(base['renderer_sp_rend2_x64.dll'])==BASE_DLL
assert H(base['Main/cgame_sp_x64.dll'])==CGAME
assert all(t in base for t in ('docs/VOLUMETRIC_SUN_EDGE_FIX_PROVENANCE.json','docs/CSM_PRIMARY_AREAMASK_CHANGE.json','Main/darkwolf_ignition_rc_v0_6.pk3'))
dll=a.dll.read_bytes()
assert 2500000<len(dll)<3500000 and dll[:2]==b'MZ'
pe=struct.unpack_from('<I',dll,60)[0]
assert dll[pe:pe+4]==b'PE\0\0' and struct.unpack_from('<H',dll,pe+4)[0]==0x8664
assert H(dll)!=BASE_DLL
for marker in (b'r_ssgiBrightSourceFix',b'r_ssgiResolveMode',b'r_forceSun',b'r_dlightWorldContainment'):
 assert marker in dll,marker
assert b'DARKWOLF_SSGI_FIELD_DIAG_V2' not in dll
assert b'dwSunTraceStart' not in dll
proof=json.loads(a.proof.read_text())
assert proof['parent_accepted_gameplay_run']==40294211216
assert proof['source_modified']==['SP/code/rend2/glsl/ssgi_fp.glsl','SP/code/rend2/tr_init.c']
assert proof['new_ssgi_shader_sha256']=='222436a6fdecd967e439a61a5dbc7e9661d383e01297d300a3b105c5dee1a1c8'
log=a.test_log.read_text()
for check in ('DW_SSGI_FIRE_EMISSIVE_V2_REGRESSION_PASS','PASS_SSGI_GLSLANG_130_COMPILE','PASS_SSGI_GLSLANG_150_COMPILE'):
 assert check in log,check
files=dict(base)
files['renderer_sp_rend2_x64.dll']=dll
files['Main/DW_SSGI_FIRE_PRODUCTION_MODE4.cfg']=(
 '// Fire emitter fix: only SSGI CVars, no CSM/Volumetric/Tesla/PCF changes.\n'
 'seta r_ssgi "1"\nseta r_ssgiStrength "0.75"\n'
 'seta r_ssgiBrightSourceFix "4"\nseta r_ssgiResolveMode "2"\n').encode()
files['Main/DW_SSGI_FIRE_PREVIOUS_MODE3_AB.cfg']=(
 '// A/B: previous mode3, same SSGI strength and resolve.\n'
 'seta r_ssgi "1"\nseta r_ssgiStrength "0.75"\n'
 'seta r_ssgiBrightSourceFix "3"\nseta r_ssgiResolveMode "2"\n').encode()
files['Main/DW_SSGI_FACTORY_LEGACY_MODE2_AB.cfg']=(
 '// A/B: previous Factory mode2; restore mode4 after test.\n'
 'seta r_ssgi "1"\nseta r_ssgiStrength "0.75"\n'
 'seta r_ssgiBrightSourceFix "2"\nseta r_ssgiResolveMode "2"\n').encode()
files['README_SSGI_EMISSIVE_FIRE_V2_RU.txt']=(
 'DARKWOLF REND2 - SSGI EMISSIVE FIRE V2, clean Win64 candidate.\n'
 'Immutable accepted base: GitHub Actions #40294211216.\n'
 'SSGI mode4: warm fire alpha-source donor and weak self-bounce suppression.\n'
 'Prior modes 0-3 and original Factory lamp fix are unchanged.\n'
 'ONLY source changes: ssgi_fp.glsl, tr_init.c; no CSM, Volumetric, Tesla, PCF changes.\n'
 'All original game binaries except renderer_sp_rend2_x64.dll remain byte-identical.\n'
 'After map loading enter: exec DW_SSGI_FIRE_PRODUCTION_MODE4.cfg\n'
 'For A/B: exec DW_SSGI_FIRE_PREVIOUS_MODE3_AB.cfg\n'
 'For Factory old source guard A/B: exec DW_SSGI_FACTORY_LEGACY_MODE2_AB.cfg\n'
 'Check Escape1 furnace and torch, Factory tunnel, Tram at identical viewpoints.\n'
 'Tram fog geometry remains separately unresolved; not part of the fire fix.\n'
 'Promote clean CI candidate to production only after real Windows GPU A/B.\n'
 'The retail game pak*.pk3 are not included; owner must supply originals.\n').encode()
files['docs/SSGI_FIRE_V2_SOURCE_PROOF.json']=json.dumps({**proof,
 'parent_archive_sha256':BASE,'parent_renderer_sha256':BASE_DLL,
 'new_renderer_sha256':H(dll),'original_cgame_sha256':CGAME,
 'only_changed_original_game_binary':'renderer_sp_rend2_x64.dll',
 'protected_effects':'INHERITED_BYTE_EXACT','user_gpu_visual':'PENDING'},indent=2).encode()
files['docs/SSGI_FIRE_V2_TESTS.txt']=log.encode()
files.pop('docs/SHA256SUMS.txt',None)
files['docs/SHA256SUMS.txt']=''.join(H(v)+'  '+k+'\n' for k,v in sorted(files.items())).encode()
for name,data in base.items():
 if name not in ('renderer_sp_rend2_x64.dll','docs/SHA256SUMS.txt'):
  assert files[name]==data,('unauthorized regression',name)
path=a.out/(NAME+'.zip')
with ZipFile(path,'w',ZIP_DEFLATED,compresslevel=7) as z:
 for name,data in sorted(files.items()):
  info=ZipInfo(NAME+'/'+name,date_time=(2026,10,26,0,0,0))
  info.compress_type=ZIP_DEFLATED
  info.external_attr=0o100644<<16
  z.writestr(info,data)
with ZipFile(path) as z:
 assert z.testzip() is None
 for line in z.read(NAME+'/docs/SHA256SUMS.txt').decode().splitlines():
  digest,rel=line.split('  ',1)
  assert H(z.read(NAME+'/'+rel))==digest,rel
assert len(files)==len(base)+6,(len(files),len(base))
manifest={'status':'CLEAN_CI_BUILD_PENDING_GAME_GPU_ACCEPTANCE',
 'base_run':40294211216,'base_zip_sha256':BASE,'archive_sha256':H(path.read_bytes()),
 'new_renderer_sha256':H(dll),'changed_existing_game_binary':'renderer_sp_rend2_x64.dll',
 'protected_other_game_files_byte_exact':True,'glsl_tests':'PASS',
 'Tram':'SEPARATE_OPEN_DEFECT','Windows_visual_validation':'PENDING_USER'}
(a.out/'SSGI_FIRE_V2_RELEASE_VALIDATION.json').write_text(json.dumps(manifest,indent=2)+'\n')
(a.out/(path.name+'.sha256')).write_text(H(path.read_bytes())+'  '+path.name+'\n')
print('DW_SSGI_EMISSIVE_FIRE_V2_CLEAN_PACKAGE_PASS',H(path.read_bytes()),H(dll),flush=True)
