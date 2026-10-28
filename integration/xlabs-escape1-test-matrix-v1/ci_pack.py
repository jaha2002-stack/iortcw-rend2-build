#!/usr/bin/env python3
"""Win64 source-attribution matrix over EXACT frozen #40640998083. NO engine code changes."""
import argparse,hashlib,io,json,struct,zipfile,re
from pathlib import Path
H=lambda b:hashlib.sha256(b).hexdigest()
BASE="d43a166c3f7c0b9ecb92767401c1617aecfea0337c137e28ae175b3d4db900b1"
DLL="1d27de162dff6328c1504781edd973fa286289101a0557a1012252d618804c47"
ROOT="DarkWolf_Sun3_FireE_Crypt1_Shadow_Fidelity_Clean_Production_Win64"
OUT="DarkWolf_Xlabs_Tesla_Escape1_Fire_Test_Matrix_V1_Win64"
M=[
 ("0_BASE",2,1,1,1),
 ("1_FIRE_ONLY_GATE",1,1,1,1),
 ("2_ALL_GATE_OFF",0,1,1,1),
 ("3_SYNTH_SHADOWS_OFF",2,1,0,1),
 ("4_SYNTH_LIGHT_OFF",2,0,1,1),
 ("5_FIRE_VOLUME_OFF",2,1,1,0),
 ("6_FIRE_ONLY_NO_VOLUME",1,1,1,0)]
P=argparse.ArgumentParser();P.add_argument("--base-zip",type=Path,required=True);P.add_argument("--out",type=Path,required=True)
a=P.parse_args()
payload=a.base_zip.read_bytes();assert H(payload)==BASE
with zipfile.ZipFile(io.BytesIO(payload)) as z:
 assert z.testzip() is None
 files={x.filename:z.read(x) for x in z.infolist() if not x.is_dir()}
assert len(files)==40 and {k.split("/")[0] for k in files}=={ROOT}
src={k.split("/",1)[1]:v for k,v in files.items()}
assert H(src["renderer_sp_rend2_x64.dll"])==DLL
r=src["renderer_sp_rend2_x64.dll"];off=struct.unpack_from("<I",r,0x3c)[0]
assert r[:2]==b"MZ" and r[off:off+4]==b"PE\0\0" and struct.unpack_from("<H",r,off+4)[0]==0x8664
assert "RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat" in src
assert "Main/DW_CRYPT1_SHADOW_FIDELITY_PRODUCTION.cfg" in src
assert not any(re.search(r"(^|/)pak[0-9]*\.pk3$",k,re.I) for k in src)
out=dict(src)
profiles=[]
for n,contain,extra,shadows,fire in M:
 name="Main/DW_WG_DIAG_"+n+".cfg"
 cfg=(f"// exact frozen renderer; isolated TEST control {n}\n"
      "exec DW_CRYPT1_SHADOW_FIDELITY_PRODUCTION.cfg\n"
      f'seta r_dlightWorldContainment "{contain}"\n'
      f'seta cg_xlabsTeslaDoorLight "{extra}"\n'
      f'seta cg_xlabsTeslaDoorShadows "{shadows}"\n'
      'seta cg_xlabsTeslaDoorIntensity "0.95"\n'
      'seta cg_xlabsTeslaDoorRadius "300"\n'
      f'seta r_volumetricFire "{fire}"\n'
      'seta cg_drawFPS "1"\n')
 assert "r_dw" not in cfg
 out[name]=cfg.encode("ascii")
 profiles.append({"id":n,"containment":contain,"supplemental_xlabs_light":extra,
                  "supplemental_shadows_and_world_tag":shadows,"fire_volumetric":fire})
readme="""DARKWOLF / ioRTCW Rend2 Xlabs Tesla and Escape1 Fire - Root Cause Matrix V1
Frozen base: GitHub Actions #40640998083, identical game + renderer DLLs.
NO shader changes, NO new CVar, NO telemetry. This is a diagnostic release,
NOT an accepted fix or a performance optimization.
Run RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat; load existing licensed RTCW data.
Use 'exec DW_WG_DIAG_0_BASE.cfg' to reset this diagnostic matrix.

Xlabs stationary Tesla SAME CAMERA: test modes 0, 1, 2, 3, 4.
0: world gate 2 + synthetic Xlabs Tesla on/shadows on (bad control)
1: world gate 1 - fire still contained but ALL Tesla world gates disabled
2: world gate 0 - no containment at all, visible negative reference
3: world gate 2 - supplemental Tesla ON, but its own shadow source class
   and world-occlusion tag BOTH disabled; interpretation must account for both
4: world gate 2 - supplemental Tesla OFF; native Tesla unaffected
If 0 is dark and 1 restores blue, Tesla world gate is suppressing light.
If 3 restores blue but 4 differs, isolate supplemental Xlabs light route.

Escape1 stove OUTSIDE WALL SAME CAMERA: test modes 0, 1, 5, 6; mode 2
is intentional leakage reference. 5/6 disable ONLY r_volumetricFire, NOT
the real direct DLight. Leak persists with FireVol 0: inspect direct/world
light classification and depth. Leak disappears: investigate FireVol pass.
Always return to 0 after testing. Note 10s average FPS, not snapshot FPS.
Test 3 lamps SWF and Crypt1 after any subsequent source fix.
Do not use this matrix as a production CFG.
"""
out["README_XLABS_ESCAPE1_MATRIX_V1.txt"]=readme.encode("ascii")
manifest={"name":"DW_XLABS_ESCAPE1_TEST_MATRIX_V1","frozen_run":40640998083,
          "frozen_binary_base_sha256":BASE,"renderer_sha256":DLL,
          "code_or_shader_modifications":0,"new_cvars":[],"profiles":profiles,
          "byte_identical_previous_files":len(src)-1,
          "known_open_defects":["Xlabs blue stationary Tesla suppressed by world gate=2",
                                "Escape1 stove residual light leak when gate=2"]}
out["docs/XLABS_ESCAPE1_TEST_MATRIX_V1.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
out["docs/SHA256SUMS.txt"]="".join(H(blob)+"  "+path+"\n" for path,blob in sorted(out.items())
                                       if path!="docs/SHA256SUMS.txt").encode("ascii")
a.out.mkdir(parents=True,exist_ok=True)
path=a.out/(OUT+".zip")
with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED,compresslevel=7) as z:
 for rel,blob in sorted(out.items()):
  info=zipfile.ZipInfo(OUT+"/"+rel,date_time=(2026,10,28,0,0,0))
  info.compress_type=zipfile.ZIP_DEFLATED
  z.writestr(info,blob)
with zipfile.ZipFile(path) as z:
 assert z.testzip() is None
 check={n.split("/",1)[1]:z.read(n) for n in z.namelist()}
 for rel,blob in src.items():
  if rel!="docs/SHA256SUMS.txt":assert check[rel]==blob,rel
 assert len(check)==len(src)+len(M)+2
 assert H(check["renderer_sp_rend2_x64.dll"])==DLL
 for line in check["docs/SHA256SUMS.txt"].decode("ascii").splitlines():
  val,name=line.split("  ",1)
  assert H(check[name])==val,name
result=dict(manifest)
result.update(zip_sha256=H(path.read_bytes()),zip_name=path.name,
              verified_file_count=len(check),read_only_engine_code=True)
(a.out/"XLABS_ESCAPE1_V1_FINAL_AUDIT.json").write_text(json.dumps(result,indent=2)+"\n")
(a.out/(path.name+".sha256")).write_text(result["zip_sha256"]+"  "+path.name+"\n")
print("DW_XLABS_ESCAPE1_EXACT_FROZEN_TEST_V1_PASS",result["zip_sha256"])
