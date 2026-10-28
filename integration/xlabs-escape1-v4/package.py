#!/usr/bin/env python3
"""Exact #40640998083 game runtime + only test-only Rend2 DLL + A/B CFGs."""
import argparse,hashlib,io,json,re,struct,zipfile
from pathlib import Path
BASE_SHA='d43a166c3f7c0b9ecb92767401c1617aecfea0337c137e28ae175b3d4db900b1'
BASE_RENDERER_SHA='1d27de162dff6328c1504781edd973fa286289101a0557a1012252d618804c47'
BASE_ROOT='DarkWolf_Sun3_FireE_Crypt1_Shadow_Fidelity_Clean_Production_Win64'
OUT_ROOT='DarkWolf_Xlabs_Tesla_Escape1_World_Capture_Main_Audit_Test_V4_Win64'
MARK='DW_XLABS_ESCAPE1_WORLD_CAPTURE_MAIN_SCENE_AUDIT_V4_20261028'
H=lambda b:hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for x in ('base-zip','renderer','proof','out'):p.add_argument('--'+x,required=True,type=Path)
 a=p.parse_args()
 base=a.base_zip.read_bytes()
 assert H(base)==BASE_SHA,('INCORRECT_ACCEPTED_BASE',H(base))
 with zipfile.ZipFile(io.BytesIO(base)) as z:
  assert z.testzip() is None
  old={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
 assert len(old)==40 and {k.split('/')[0] for k in old}=={BASE_ROOT}
 files={k.split('/',1)[1]:v for k,v in old.items()}
 assert H(files['renderer_sp_rend2_x64.dll'])==BASE_RENDERER_SHA
 baseline_cgame_sha=H(files['Main/cgame_sp_x64.dll'])
 renderer=a.renderer.read_bytes()
 assert H(renderer)!=BASE_RENDERER_SHA and len(renderer)>2000000
 pe=struct.unpack_from('<I',renderer,0x3c)[0]
 assert renderer[:2]==b'MZ' and renderer[pe:pe+4]==b'PE\x00\x00'
 assert struct.unpack_from('<H',renderer,pe+4)[0]==0x8664
 proof=json.loads(a.proof.read_text())
 assert proof['marker']==MARK and proof['frozen_user_accepted_runtime_run']==40640998083
 assert proof['changed_source_files']==['SP/code/rend2/tr_main.c','SP/code/rend2/tr_scene.c']
 assert proof['source_sha_before']=={
  'SP/code/rend2/tr_main.c':'070f2bfa3c3f1d7beb02333f2ce124afc456e472e971a05afd68b6161448d0ea',
  'SP/code/rend2/tr_scene.c':'2ce98792ab054ea59529ac103a9485443f08d2c8d34b0e8ded42d2aacf9ebcaf'}
 assert proof['source_sha_after']=={
  'SP/code/rend2/tr_main.c':'f4f37f8c46b0e7b5e5ee7d24d6f069093f58fa3536685d026489b4d64d4a957f',
  'SP/code/rend2/tr_scene.c':'58e2a3aeb784558575de9d40bb64e15d1f5a7c7a8730a2d5d0d626f748d5ab37'}
 assert proof['production'] is False
 assert proof['normal_light_origin_unchanged'] and proof['point_shadow_origin_unchanged']
 files['renderer_sp_rend2_x64.dll']=renderer

 common='''// DarkWolf V4 diagnostic only, NOT production.
exec DW_CRYPT1_SHADOW_FIDELITY_PRODUCTION.cfg
set r_dlightMode "2"
set r_dynamiclight "1"
set r_staticPromote "1"
set r_lightmap "0"
set r_mapLightingProfileEnable "1"
set r_mapLightingOverride "0"
set r_mapLightingLearn "0"
set r_mapLightingBakedScale "0.25"
set r_volumetricFire "1"
set r_dwMainSceneLightAuditOnce "0"
'''
 xtra='''set cg_xlabsTeslaDoorLight "1"
set cg_xlabsTeslaDoorShadows "1"
set cg_xlabsTeslaDoorIntensity "0.95"
set cg_xlabsTeslaDoorRadius "300"
'''
 configs={}
 for name,offset,gate in [
    ('X0_BASE',0,2),('X1_CAPTURE_PLUS32',32,2),
    ('X2_CAPTURE_PLUS64',64,2),('X3_CAPTURE_PLUS96',96,2),
    ('X4_CAPTURE_MINUS32',-32,2),('X5_GATE1_CONTROL',0,1)]:
  configs[name]=common+xtra+f'set r_dlightWorldContainment "{gate}"\nset r_dwTeslaWorldCaptureXTest "{offset}"\n'
 configs['E0_ESCAPE1_BASE']=common+'set r_dlightWorldContainment "2"\nset r_dwTeslaWorldCaptureXTest "0"\nset cg_dlightFireIntensityScale "1.14"\n'
 configs['E1_ESCAPE1_DYNAMIC_OFF']=configs['E0_ESCAPE1_BASE']+'set r_dynamiclight "0"\n'
 for k,v in configs.items():files['Main/DW_V4_'+k+'.cfg']=v.encode('ascii')
 files['Main/DW_V4_AUDIT_MAIN_ONCE.cfg']=(
  '// Apply after stable test CFG, wait, then condump main scene audit.\n'
  'set r_dwMainSceneLightAuditOnce "1"\n').encode('ascii')
 readme="""DARKWOLF: Xlabs Tesla / Escape1 Stove - V4 ROOT CAUSE Win64 TEST
========================================================================
ACCEPTED BASE: #40640998083, Crypt1 PCF2x2, Sun3, Fire E.
TEST changes ONLY renderer_sp_rend2_x64.dll. All game DLLs unchanged.
No GLSL modifications, CSM, bloom, light energy, Direct origin,
normal DLight point shadows or StaticPromote budget modifications.

Xlabs, same save/view, active stationary Tesla:
  exec DW_V4_X0_BASE.cfg
  exec DW_V4_X1_CAPTURE_PLUS32.cfg
  exec DW_V4_X2_CAPTURE_PLUS64.cfg
  exec DW_V4_X3_CAPTURE_PLUS96.cfg
  exec DW_V4_X4_CAPTURE_MINUS32.cfg
  exec DW_V4_X5_GATE1_CONTROL.cfg
The X value moves ONLY world-depth capture, not real DLight origin or bolt.
X5 turns off only Tesla containment, retains fire containment.
These offsets may CAUSE light leaks; do NOT use them in production.
Wait for cubemap capture and compare walls, blue Tesla, shadow fidelity, FPS.

One-shot audit for Xlabs after X0, X1, X2:
  exec DW_V4_AUDIT_MAIN_ONCE.cfg
  condump xlabs_v4_x0.log
Repeat after changing each named X profile.
Look for DW_MAIN_SCENE_AUDIT_V4_BEGIN/LIGHT/END showing both actual
source xyz and independent capture xyz, world mask, Fire source, cache slot.

Escape1 stove, OUTSIDE wall, same angle:
  exec DW_V4_E0_ESCAPE1_BASE.cfg
  exec DW_V4_AUDIT_MAIN_ONCE.cfg
  condump escape1_v4_main.log
Then briefly: exec DW_V4_E1_ESCAPE1_DYNAMIC_OFF.cfg
Return E0 immediately. The audit is now consumed only by MAIN view,
not the RDF_SKYBOXPORTAL view; report can identify nonclassified DLight.

Keep accepted production #40640998083 in a SEPARATE folder.
Only after user GPU A/B will a targeted production correction be designed.
Two new test CVars are non-archived, NOT FOR production releases.
Licensed original RTCW pak files are not distributed.
"""
 files['README_XLABS_ESCAPE1_V4_RU.txt']=readme.encode('utf-8')
 manifest={
  'status':'TEMPORARY_TEST_ONLY_NOT_PRODUCTION',
  'accepted_base_run':40640998083,
  'accepted_zip_sha256':BASE_SHA,
  'old_renderer_sha256':BASE_RENDERER_SHA,
  'new_renderer_sha256':H(renderer),
  'cgame_sha256_unchanged':baseline_cgame_sha,
  'changed_existing_files':['renderer_sp_rend2_x64.dll','docs/SHA256SUMS.txt'],
  'byte_identical_original_files':len(old)-2,
  'source_delta':proof,
  'test_only_cvars':proof['test_cvars_non_archived'],
  'glsl_changed':False,
  'gpu_visual_acceptance':'PENDING',
  'preserved':['Crypt1 PCF2x2','Sun3','FireE','Local','Sky','SSGI',
               'Tesla blue color/radius','static shadow budgets','3+2 shadow slots']}
 files['docs/XLABS_ESCAPE1_V4_TEST_MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
 files['docs/SHA256SUMS.txt']=''.join(H(v)+'  '+k+'\n' for k,v in sorted(files.items())
                                    if k!='docs/SHA256SUMS.txt').encode('ascii')
 assert len(files)==len(old)+len(configs)+3
 assert not any(re.search(r'(^|/)pak[0-9]*\.pk3$',k,re.I) for k in files)
 a.out.mkdir(parents=True,exist_ok=True)
 path=a.out/(OUT_ROOT+'.zip')
 with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
  for k,v in sorted(files.items()):
   i=zipfile.ZipInfo(OUT_ROOT+'/'+k,date_time=(2026,10,28,0,0,0))
   i.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(i,v)
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  final={n.split('/',1)[1]:z.read(n) for n in z.namelist()}
 assert len(final)==len(files)
 assert H(final['renderer_sp_rend2_x64.dll'])==H(renderer)
 for k,v in old.items():
  rel=k.split('/',1)[1]
  if rel not in ('renderer_sp_rend2_x64.dll','docs/SHA256SUMS.txt'):
   assert final[rel]==v,('BASE_REGRESSION',rel)
 for line in final['docs/SHA256SUMS.txt'].decode('ascii').splitlines():
  h,k=line.split('  ',1)
  assert H(final[k])==h,('EMBEDDED_SHA',k)
 audit={
  'base_sha256':BASE_SHA,'new_renderer_sha256':H(renderer),
  'release_sha256':H(path.read_bytes()),'unchanged_original_files':len(old)-2,
  'new_cfg_count':len(configs)+1,'source':proof,'files':len(final),
  'gpu_runtime':'PENDING_USER_AB'}
 (a.out/'XLABS_ESCAPE1_V4_FINAL_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
 (a.out/(path.name+'.sha256')).write_text(audit['release_sha256']+'  '+path.name+'\n')
 print('DW_XLABS_ESCAPE1_V4_EXACT_BASE_PACKAGE_PASS',path,audit['release_sha256'])
if __name__=='__main__':main()
