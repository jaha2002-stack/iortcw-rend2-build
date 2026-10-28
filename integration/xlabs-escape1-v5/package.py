#!/usr/bin/env python3
"""V5 test repack of byte-exact accepted #40640998083, NEVER a clean release."""
import argparse,hashlib,io,json,re,struct,zipfile
from pathlib import Path
SHA=lambda b:hashlib.sha256(b).hexdigest()
BASE_SHA="d43a166c3f7c0b9ecb92767401c1617aecfea0337c137e28ae175b3d4db900b1"
BASE_DLL_SHA="1d27de162dff6328c1504781edd973fa286289101a0557a1012252d618804c47"
OLD_ROOT="DarkWolf_Sun3_FireE_Crypt1_Shadow_Fidelity_Clean_Production_Win64"
NEW_ROOT="DarkWolf_Xlabs_Tesla_CubeFace_Filter_Escape1_Native_Attribution_Test_V5_Win64"
def main():
 ap=argparse.ArgumentParser()
 for k in ("base-zip","renderer","qa","out"):ap.add_argument("--"+k,required=True,type=Path)
 a=ap.parse_args()
 bs=a.base_zip.read_bytes();assert SHA(bs)==BASE_SHA,("BAD_FROZEN_USER_BASE",SHA(bs))
 with zipfile.ZipFile(io.BytesIO(bs)) as z:
  assert z.testzip() is None
  original={n:z.read(n) for n in z.namelist() if not n.endswith("/")}
 assert len(original)==40 and {n.split("/")[0] for n in original}=={OLD_ROOT}
 files={n.split("/",1)[1]:v for n,v in original.items()}
 assert SHA(files["renderer_sp_rend2_x64.dll"])==BASE_DLL_SHA
 render=a.renderer.read_bytes();assert SHA(render)!=BASE_DLL_SHA and len(render)>2_000_000
 pe=struct.unpack_from("<I",render,0x3c)[0]
 assert render[:2]==b"MZ" and render[pe:pe+4]==b"PE\x00\x00"
 assert struct.unpack_from("<H",render,pe+4)[0]==0x8664
 qa=json.loads(a.qa.read_text())
 assert qa["status"]=="SOURCE_UNIT_GLSL_PASS" and qa["glsl_versions"]==[120,130]
 assert qa["cubeface_roundtrips"]==10000 and qa["production_crypt1_path_same"]
 files["renderer_sp_rend2_x64.dll"]=render
 # Every preset initializes BOTH test cvars, so comparisons are independent.
 common='''// DarkWolf V5 temporary GPU test - NEVER production.
exec DW_CRYPT1_SHADOW_FIDELITY_PRODUCTION.cfg
set r_dynamiclight "1"
set r_dlightMode "2"
set r_dlightWorldContainment "2"
set r_staticPromote "1"
set r_lightmap "0"
set r_mapLightingOverride "0"
set r_mapLightingLearn "0"
set r_dwMainSceneLightAuditOnce "0"
set r_dwTeslaWorldCaptureXTest "0"
set r_dwTeslaWorldFilterTest "0"
set r_dwEscape1NativeWorldMaskTest "0"
'''
 xlabs='''set cg_xlabsTeslaDoorLight "1"
set cg_xlabsTeslaDoorShadows "1"
set cg_xlabsTeslaDoorIntensity "0.95"
set cg_xlabsTeslaDoorRadius "300"
'''
 configs={"X0_BASE":common+xlabs}
 for tag,offset in (("X1_PLUS32",32),("X2_PLUS64",64),("X4_MINUS32",-32)):
  for mode,suffix in ((0,"LEGACY2X2"),(1,"CUBEFACE2X2"),(2,"CUBEFACE4X4_TENT")):
   configs[f"{tag}_F{mode}_{suffix}"]=common+xlabs+(
    f'set r_dwTeslaWorldCaptureXTest "{offset}"\n'
    f'set r_dwTeslaWorldFilterTest "{mode}"\n')
 for mode in range(4):
  configs[f"E{mode}_ESCAPE1_{('CONTROL','SOURCE_A_ONLY','SOURCE_B_ONLY','BOTH_SOURCES')[mode]}"]=(
   common+f'set r_dwEscape1NativeWorldMaskTest "{mode}"\n')
 for k,v in configs.items():
  files[f"Main/DW_V5_{k}.cfg"]=v.encode("ascii")
 files["Main/DW_V5_AUDIT_MAIN_ONCE.cfg"]=(
  b"// After applying V5 profile, request audit of next MAIN scene only.\n"
  b"set r_dwMainSceneLightAuditOnce \"1\"\n")
 readme="""DarkWolf V5 - Xlabs Tesla cube-face PCF + Escape1 light attribution test
===========================================================================
Frozen accepted production baseline: GitHub Actions #40640998083.
DO NOT put this test DLL into your regular production installation.
New version changes ONLY renderer_sp_rend2_x64.dll; all other original files
except SHA256SUMS are byte-identical to user-accepted #40640998083.
Crypt1 standard path unchanged; Sun3 and Fire E unchanged.

Xlabs, same save/angle and light active:
  exec DW_V5_X0_BASE.cfg
  exec DW_V5_X1_PLUS32_F0_LEGACY2X2.cfg
  exec DW_V5_X1_PLUS32_F1_CUBEFACE2X2.cfg
  exec DW_V5_X1_PLUS32_F2_CUBEFACE4X4_TENT.cfg
Repeat the 3 F0/F1/F2 modes for X2_PLUS64 and X4_MINUS32.
The correction is scoped to stationary Xlabs Tesla source only:
F0 = V4 old face-unswizzled 2x2 architectural PCF
F1 = signed OpenGL cube-face texel center 2x2 PCF
F2 = signed OpenGL cube-face texel center 4x4 tent PCF (16 taps)
Record shadow softness, staircases, blue spill through walls, and
average FPS over >=15 seconds. F2 may cost more FPS; this is intentional
for controlled A/B and not automatically a production recommendation.
X0 is reference; source position/color and 2048 primary shadows unchanged.

Escape1, outside stove room wall, exactly same save/angle:
  exec DW_V5_E0_ESCAPE1_CONTROL.cfg
  exec DW_V5_E1_ESCAPE1_SOURCE_A_ONLY.cfg
  exec DW_V5_E2_ESCAPE1_SOURCE_B_ONLY.cfg
  exec DW_V5_E3_ESCAPE1_BOTH_SOURCES.cfg
These experimental modes enable architectural visibility ONLY for
two specific native unclassified warm lights in the real Escape1 log:
 A: (-1340,692,-36), B: (-1212,1492,-140).
These are diagnostic candidates, NOT yet verified stove identities.
No Fire E or local-volumetric classification is modified.
For any mode: exec DW_V5_AUDIT_MAIN_ONCE.cfg
Then wait for DW_MAIN_SCENE_AUDIT_V4_END and condump escape1_v5_E1.txt.
Check actual world=1 / slot >=0 for candidate if active.
Revert to E0 after testing.

Do not declare production or restore classified fire based only on CI.
Any accepted production change must remove diagnostic test cvars.
"""
 files["README_XLABS_ESCAPE1_V5_RU.txt"]=readme.encode("utf-8")
 manifest={
  "status":"TEST_ONLY_GPU_VALIDATION_PENDING",
  "accepted_run":40640998083,"parent_test_run":40661698228,
  "accepted_base_sha256":BASE_SHA,"new_renderer_sha256":SHA(render),
  "unchanged_cgame_sha256":SHA(files["Main/cgame_sp_x64.dll"]),
  "changed_original_files":["renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt"],
  "unchanged_original_files":38,"test_cvars":[
   "r_dwTeslaWorldCaptureXTest","r_dwTeslaWorldFilterTest",
   "r_dwEscape1NativeWorldMaskTest","r_dwMainSceneLightAuditOnce"],
  "test_cases":list(configs),
  "source_validation":qa,
  "preserved":["Crypt1 PCF2x2","Sun3","Fire E","Local","Sky","SSGI",
               "No PBR","StaticPromote 32 + 3 shadow slots",
               "Tesla color/intensity/normal point shadows"]}
 files["docs/XLABS_ESCAPE1_V5_TEST_MANIFEST.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
 files["docs/SHA256SUMS.txt"]="".join(SHA(v)+"  "+k+"\n" for k,v in sorted(files.items())
                                       if k!="docs/SHA256SUMS.txt").encode("ascii")
 assert len(configs)==14 and len(files)==56
 assert not any(re.search(r'(^|/)pak[0-9]*\.pk3$',k,re.I) for k in files)
 a.out.mkdir(parents=True,exist_ok=True)
 path=a.out/(NEW_ROOT+".zip")
 with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
  for k,v in sorted(files.items()):
   inf=zipfile.ZipInfo(NEW_ROOT+"/"+k,date_time=(2026,10,28,0,0,0))
   inf.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(inf,v)
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  final={n.split("/",1)[1]:z.read(n) for n in z.namelist()}
 assert len(final)==len(files)
 assert SHA(final["renderer_sp_rend2_x64.dll"])==SHA(render)
 for k,v in original.items():
  rel=k.split("/",1)[1]
  if rel not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt"):
   assert final[rel]==v,("FROZEN_REGRESSION",rel)
 for line in final["docs/SHA256SUMS.txt"].decode().splitlines():
  digest,key=line.split("  ",1)
  assert SHA(final[key])==digest,("FILE_SHA_MISMATCH",key)
 out={
  "status":"V5_EXACT_FROZEN_ACCEPTED_REPACKAGE_PASS",
  "accepted_base_sha256":BASE_SHA,"new_renderer_sha256":SHA(render),
  "final_sha256":SHA(path.read_bytes()),"unchanged_original_files":38,
  "total_files":len(final),"new_cfg_files":len(configs)+1,
  "shader_test_sha256":qa["sha256_function"],"test_gpu_state":"PENDING"}
 (a.out/"XLABS_ESCAPE1_V5_FINAL_AUDIT.json").write_text(json.dumps(out,indent=2)+"\n")
 (a.out/(path.name+".sha256")).write_text(out["final_sha256"]+"  "+path.name+"\n")
 print(out["status"],path,out["final_sha256"])
if __name__=="__main__":main()
