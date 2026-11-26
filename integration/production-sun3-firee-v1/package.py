#!/usr/bin/env python3
"""Repack ONLY the accepted Sky #404801 SP runtime with clean Sun3+FireE renderer."""
import argparse,hashlib,io,json,re,zipfile
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("--base-zip",type=Path,required=True)
p.add_argument("--renderer",type=Path,required=True)
p.add_argument("--proof",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args()
H=lambda b:hashlib.sha256(b).hexdigest()
BASE_RUN=40480112714
BASE_ZIP_SHA="05e6d68fe1b59924f074b18a2e60e54fee79bd4d39fb151a4978f5f6a406c8eb"
BASE_DLL_SHA="0809d44cce520d36514e6dd60c82cc3504b520217a5c867dfbee2efa8471eef8"
MARK="DARKWOLF_SUN3_FIRE_E_CLEAN_PRODUCTION_V1_20261027"
base=a.base_zip.read_bytes()
assert H(base)==BASE_ZIP_SHA,("WRONG_ACCEPTED_SKY_ZIP",H(base))
dll=a.renderer.read_bytes()
assert dll[:2]==b"MZ" and len(dll)>2000000
assert H(dll)!=BASE_DLL_SHA
proof=json.loads(a.proof.read_text())
assert proof["marker"]==MARK and proof["exact_binary_base_run"]==BASE_RUN
assert proof["new_diagnostic_cvars"]==[] and proof["telemetry"] is False
assert proof["sha256_before"]["tr_backend.c"]=="505ef716a0e316a99f00f0ce8d2e4e81ecef650424bfd22a537227ffbfbb37ba"
assert sorted(proof["modified_source_files"])==sorted("SP/code/rend2/"+s for s in
 ("tr_backend.c","tr_init.c","glsl/volumetricsun_fp.glsl","glsl/volumetriclocal_fp.glsl","glsl/volumetriclocal_upscale_fp.glsl"))
with zipfile.ZipFile(io.BytesIO(base)) as z:
 assert z.testzip() is None
 original={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
assert len(original)==30,("SKY_BASE_FILE_COUNT_CHANGED",len(original))
root="DarkWolf_Sky_Portal_Universal_Single_Sample_V1_Win64"
assert {name.split("/")[0] for name in original}=={root}
assert all(name.startswith(root+"/") and ".." not in Path(name).parts for name in original)
rend2="renderer_sp_rend2_x64.dll"
assert H(original[root+"/"+rend2])==BASE_DLL_SHA
for f in ("ioWolfSP.x64.exe","renderer_sp_opengl1_x64.dll",
          "Main/cgame_sp_x64.dll","Main/qagame_sp_x64.dll","Main/ui_sp_x64.dll",
          "SDL264.dll","OpenAL64.dll"):
 assert root+"/"+f in original
assert not any(re.search(r"(^|/)pak[0-9]*\.pk3$",name,re.I) for name in original)
entries={k.split("/",1)[1]:v for k,v in original.items()}
entries[rend2]=dll
# User's pre-existing q3config CVAR_ARCHIVE values may override new DLL defaults.
# This is an optional ONE-TIME production preset, not a diagnostic mode.
cfg="""// DarkWolf CLEAN production: user-validated Sun V3 mode 3 + Fire E
// Reapply once if archived CVAR values override compiled default settings.
seta r_volumetricSun "1"
seta r_volumetricSunMode "1"
seta r_volumetricSunSamples "32"
seta r_volumetricSunShadowPcf "2"
seta r_volumetricSunJitter "0.08"
seta r_volumetricFire "1"
seta r_volumetricFireSamples "40"
seta r_volumetricFireUpscale "2"
seta r_volumetricLocalShadowPcf "2"
seta r_volumetricLocalJitter "0.08"
"""
assert "r_dw" not in cfg and "diagnostic" not in cfg
entries["Main/DW_SUN3_FIRE_E_PRODUCTION.cfg"]=cfg.encode("ascii")
readme="""DARKWOLF / ioRTCW Rend2 SP - CLEAN PRODUCTION SUN3 + FIRE E
Release base: accepted #40480112714 Universal Portal Sky Single-Sample V1.
Sun: user-confirmed V3 MODE 3 from #40504661395, dual shadow visibility.
Sun cascade blend: the accepted original 6% interval (not narrow/hard).
Sun rays: 32 steps default; quarter-resolution; no experimental full-res path.
Fire E: 40 steps, depth-aware 5x5 upscale and 9-tap shadow PCF for Fire only.
Local lights: retain user-tested local path; no lamp diagnostic PCF additions.
All historical Sky/CSM/SSGI/Tesla/material fixes from the accepted base retained.
No new diagnostic CVARs or telemetry; no experimental mode selector.
Bloom v2 HDR Pyramid remains unchanged. No Bloom v3, no PBR materials.
Install the SP runtime with your licensed RTCW game data.
For an existing q3config with archived older CVAR settings, run once in console:
  exec DW_SUN3_FIRE_E_PRODUCTION.cfg
If you changed the latched volumetric master enable, use vid_restart afterward.
Restart the game if the DLL was previously loaded.
Priority GPU A/B: Sun arch hall and tree+cliff, Fire stove/player shadow, Sky portal.
For FPS compare several seconds of stable camera and identical game settings.
This release passes CI/GLSL/static checks; user GPU verification of this new DLL
and final FPS acceptance remain outstanding until tested on the user's PC.
Rollback: keep #40480112714 untouched in a separate installation folder.
Commercial pak*.pk3 files are NOT included.
"""
entries["README_SUN3_FIRE_E_CLEAN_PRODUCTION.txt"]=readme.encode("utf-8")
manifest={
 "release":"DARKWOLF_SUN3_FIRE_E_CLEAN_PRODUCTION_V1_20261027",
 "status":"CI_BUILD_CANDIDATE_GPU_RUNTIME_PENDING",
 "accepted_base_run_id":BASE_RUN,
 "accepted_base_zip_sha256":BASE_ZIP_SHA,
 "accepted_base_renderer_sha256":BASE_DLL_SHA,
 "compiled_renderer_sha256":H(dll),
 "source":proof,
 "Sun":"hardwired_user_preferred_V3_mode3_dual_visibility",
 "Fire":"hardwired_user_preferred_E_5x5_9tap_40_samples",
 "no_diagnostic_cvars":True,"no_telemetry":True,
 "preserved_sky_single_sample":True,
 "commercial_assets_included":False,
 "changed_existing_files":[rend2,"docs/SHA256SUMS.txt"],
 "byte_identical_existing_file_count":len(original)-2,
 "new_files":["Main/DW_SUN3_FIRE_E_PRODUCTION.cfg",
             "README_SUN3_FIRE_E_CLEAN_PRODUCTION.txt",
             "docs/SUN3_FIRE_E_PRODUCTION_MANIFEST.json"],
 "user_acceptance_this_new_binary":"PENDING"
}
entries["docs/SUN3_FIRE_E_PRODUCTION_MANIFEST.json"]=(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
entries["docs/SHA256SUMS.txt"]=("".join(H(v)+"  "+k+"\n" for k,v in sorted(entries.items())
                                       if k!="docs/SHA256SUMS.txt")).encode("ascii")
assert len(entries)==len(original)+3,("PACKAGING_FILE_COUNT",len(entries))
name="DarkWolf_Sky404801_Sun3_FireE_Clean_Production_Win64"
a.out.mkdir(parents=True,exist_ok=True)
out=a.out/(name+".zip")
with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
 for k,v in sorted(entries.items()):
  inf=zipfile.ZipInfo(name+"/"+k,date_time=(2026,10,27,0,0,0))
  inf.compress_type=zipfile.ZIP_DEFLATED
  z.writestr(inf,v)
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 contents={p.split("/",1)[1]:z.read(p) for p in z.namelist()}
 assert len(contents)==len(entries)
 assert H(contents[rend2])==H(dll)
 for k,v in original.items():
  rel=k.split("/",1)[1]
  if rel not in (rend2,"docs/SHA256SUMS.txt"):
   assert contents[rel]==v,("BASE_FILE_REGRESSION",rel)
 assert not any("VOLWAVE_" in n or "VOL_DIAG" in n or "SUN_V3_0" in n for n in contents)
assert all("r_dw" not in contents[k].decode("utf8") for k in
 ("Main/DW_SUN3_FIRE_E_PRODUCTION.cfg","README_SUN3_FIRE_E_CLEAN_PRODUCTION.txt"))
sha=H(out.read_bytes())
(a.out/(out.name+".sha256")).write_text(sha+"  "+out.name+"\n")
(a.out/"SUN3_FIRE_E_CLEAN_PRODUCTION_VERIFICATION.json").write_text(
    json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("DW_SUN3_FIRE_E_404801_CLEAN_PACKAGE_PASS",
      str(out),"sha256="+sha,"renderer_sha256="+H(dll),
      "preserved_original_files="+str(len(original)-2))
