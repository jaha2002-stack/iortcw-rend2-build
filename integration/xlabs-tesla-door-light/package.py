#!/usr/bin/env python3
"""Replace ONLY CGame in exact successful 40187645839 Windows x64 release.

No renderer, game server, executable, effects pak, user settings, or standard
production DLLs are changed. Optional Xlabs Tesla door CVars start in CGame.
"""
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
import hashlib,struct,json,io,argparse

H=lambda b:hashlib.sha256(b).hexdigest()
BASE_OUTER="a5f43fa095c3265d2dbc8403ab96149719c795471739f3ddf5918feb2a294718"
BASE_INNER="c1841dbed6d272989cb342d6a62a8ef1042df56e9d86d1a4773f4e6e09ea022e"
BASE_GAME="71dfa71bf5b2ab7271f95a4f8daa92d7cf4234d08452031ab3a85c23361c499d"
BASE_RENDER="77322a8bb82a67bab44632134b48a75050a565d48469b0826908790a758d9179"
BASE_EXE="c8dba37ee2eb3aa902083dfa6f99c203f37fb1dcf766c5a63bf91911b5ef8e5a"
NAME="DarkWolf_Rend2_Sept18_TeslaParity_SelectiveFireTesla_XlabsDoorDLightShadows_Win64"

p=argparse.ArgumentParser()
p.add_argument("--base-artifact",type=Path,required=True)
p.add_argument("--cgame",type=Path,required=True)
p.add_argument("--source-proof",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
assert H(a.base_artifact.read_bytes())==BASE_OUTER, "MUST use exact successful run 40187645839"
with ZipFile(a.base_artifact) as artifact:
 assert artifact.testzip() is None
 nested=[x for x in artifact.namelist() if x.endswith("_Win64.zip")]
 assert len(nested)==1,nested
 original_zip=artifact.read(nested[0])
assert H(original_zip)==BASE_INNER
with ZipFile(io.BytesIO(original_zip)) as z:
 assert z.testzip() is None
 allfiles={}
 for key in z.namelist():
  if key.endswith("/"):continue
  parts=key.split("/",1)
  assert len(parts)==2 and ".." not in Path(parts[1]).parts
  assert parts[1] not in allfiles,parts[1]
  allfiles[parts[1]]=z.read(key)

assert len(allfiles)==20,len(allfiles)
assert H(allfiles["Main/cgame_sp_x64.dll"])==BASE_GAME
assert H(allfiles["renderer_sp_rend2_x64.dll"])==BASE_RENDER
assert H(allfiles["ioWolfSP.x64.exe"])==BASE_EXE
for req in ("Main/qagame_sp_x64.dll","Main/ui_sp_x64.dll",
            "Main/DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg",
            "Main/darkwolf_ignition_rc_v0_6.pk3",
            "RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat"):
 assert req in allfiles

data=a.cgame.read_bytes()
assert len(data)>120000 and data[:2]==b"MZ"
pe=struct.unpack_from("<I",data,60)[0]
assert data[pe:pe+4]==b"PE\0\0" and struct.unpack_from("<H",data,pe+4)[0]==0x8664
assert H(data)!=BASE_GAME
for t in (b"cg_xlabsTeslaDoorLight",b"cg_xlabsTeslaDoorRadius",
          b"cg_xlabsTeslaDoorIntensity",b"cg_xlabsTeslaDoorShadows"):
 assert t in data,("New configurable CGame control absent",t)
assert b"DARKWOLF_UNIFIED_PRODUCTION_TESLA_TIMING_V1" not in data
src=json.loads(a.source_proof.read_text())
assert src["base_run"]==40187645839
assert src["renderer_files_bit_identical"]>70
assert src["original_Tesla_effect_logic_byte_identical_after_removing_addendum"]
assert len(src["patched_source_files"])==3

original=dict(allfiles)
allfiles["Main/cgame_sp_x64.dll"]=data
allfiles["docs/XLABS_TESLA_DOOR_DLIGHT_SOURCE_PROOF.json"]=json.dumps(src,indent=2).encode()
allfiles["README_XLABS_TESLA_DOOR_DLIGHT_RU.txt"]=(
 "EXPERIMENT: Xlabs 3-bolt Tesla doors now illuminate nearby floor, walls and\n"
 "doors with a cool-blue pulsing dynamic point light. Cubemap shadows enabled.\n"
 "Original 20 Xlabs shooter_tesla entities: 19 had NO native DLIGHT flag.\n"
 "One shared light per nearby 3-bolt group avoids shadow-slot waste.\n"
 "EXACT base: GitHub Actions run #40187645839. ONLY Main/cgame_sp_x64.dll is replaced.\n"
 "All other original EXE/DLLs, configs, renderer and game module are unchanged.\n"
 "Effects and September Tesla animation remain byte-identical in their original\n"
 "C source block. No new GL code, shaders, resource files or Fire/Tesla fixes.\n"
 "Live-editable settings (no vid_restart):\n"
 "seta cg_xlabsTeslaDoorLight 1       (0 off, 1 on)\n"
 "seta cg_xlabsTeslaDoorRadius 300    (128..550)\n"
 "seta cg_xlabsTeslaDoorIntensity 0.95 (0..1.8)\n"
 "seta cg_xlabsTeslaDoorShadows 1     (0 off, 1 on)\n"
 "Keep r_dynamiclight 1, r_dlightMode 2, r_dlightWorldContainment 2.\n"
 "Shadows use up to the existing 2 dynamic cubemap slots, not guaranteed for\n"
 "every source at once. Windows GPU tests needed to confirm quality and FPS.\n"
 "Licensed RTCW pak files required and not included.\n"
).encode("utf-8")
if "docs/BUILD_PROVENANCE.json" in allfiles:
 old=json.loads(allfiles["docs/BUILD_PROVENANCE.json"])
 old["parent_run_id"]=40187645839
 old["parent_release_zip_sha256"]=BASE_INNER
 old["parent_cgame_sha256"]=BASE_GAME
 old["xlabs_cgame_sha256"]=H(data)
 old["changed_runtime_modules"]=["Main/cgame_sp_x64.dll"]
 old["visual_validation"]="PENDING_ACTUAL_GAME_XLABS_GPU_AB"
 allfiles["docs/BUILD_PROVENANCE.json"]=json.dumps(old,ensure_ascii=False,indent=2).encode()
assert "docs/SHA256SUMS.txt" in allfiles
allfiles.pop("docs/SHA256SUMS.txt")
allfiles["docs/SHA256SUMS.txt"]="".join(H(v)+"  "+k+"\n" for k,v in sorted(allfiles.items())).encode()

for key in original:
 if key not in ("Main/cgame_sp_x64.dll","docs/BUILD_PROVENANCE.json","docs/SHA256SUMS.txt"):
  assert original[key]==allfiles[key],key
for key in ("renderer_sp_rend2_x64.dll","ioWolfSP.x64.exe",
            "Main/qagame_sp_x64.dll","Main/ui_sp_x64.dll"):
 assert H(original[key])==H(allfiles[key])

output=a.out/(NAME+".zip")
with ZipFile(output,"w",ZIP_DEFLATED,compresslevel=7) as z:
 for rel,bytes_ in sorted(allfiles.items()):
  zi=ZipInfo(NAME+"/"+rel,date_time=(2026,10,25,0,0,0))
  zi.compress_type=ZIP_DEFLATED
  zi.external_attr=0o100644<<16
  z.writestr(zi,bytes_)
with ZipFile(output) as z:
 assert z.testzip() is None
 for line in z.read(NAME+"/docs/SHA256SUMS.txt").decode().splitlines():
  sha,rel=line.split("  ",1)
  assert H(z.read(NAME+"/"+rel))==sha,rel
digest=H(output.read_bytes())
(a.out/(NAME+".zip.sha256")).write_text(digest+"  "+output.name+"\n")
manifest={
 "status":"COMPLETE_WIN64_USER_RELEASE_ARCHIVE_VERIFIED",
 "name":output.name,"size_bytes":output.stat().st_size,"sha256":digest,
 "parent_GitHub_run":40187645839,"parent_artifact_sha256":BASE_OUTER,
 "parent_release_sha256":BASE_INNER,"parent_renderer_sha256":BASE_RENDER,
 "parent_executable_sha256":BASE_EXE,"previous_cgame_sha256":BASE_GAME,
 "new_cgame_sha256":H(data),"changed_runtime_modules":["Main/cgame_sp_x64.dll"],
 "all_other_original_runtime_modules_bit_identical":True,
 "licensed_original_game_files_not_included":True,
 "cinematic_tesla_dlight_source_grouped_and_shadow_eligible":True,
 "actual_game_gpu_validation":"NOT_INFERRED_FROM_COMPILE"
}
(a.out/"XLABS_TESLA_DOOR_LIGHT_RELEASE_VALIDATION.json").write_text(json.dumps(manifest,indent=2)+"\n")
print("XLABS_TESLA_DOOR_BASE_40187645839_ONLY_CGAME_RELEASE_PASS",
      json.dumps(manifest),flush=True)
