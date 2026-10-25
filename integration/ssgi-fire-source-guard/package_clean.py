#!/usr/bin/env python3
"""Repackage exactly one authorized FourWeek Win64 master with a compiled SSGI-only DLL.
Do not substitute other program files, config values, MSAA, CSM or world-occlusion.
"""
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
import argparse,json,hashlib
H=lambda b:hashlib.sha256(b).hexdigest()
BASE_ZIP_SHA="559d01d3815ef1d58b3f018d1c1f215cb37881d2756ad3508ae5cc891179b2e4"
BASE_DLL_SHA="4112890117f5fb16371ba8387ecd89203257eff361c22d83784db65c67eadd0a"
NAME="DarkWolf_Rend2_v4.4.6_RC4_FourWeek_Master_V03_SSGI_FireSource_Clean_Win64"
p=argparse.ArgumentParser()
p.add_argument("--base",type=Path,required=True)
p.add_argument("--dll",type=Path,required=True)
p.add_argument("--evidence",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
assert a.base.is_file() and a.base.stat().st_size > 5000000
dll=a.dll.read_bytes()
assert dll[:2]==b"MZ" and 2000000<len(dll)<12000000
new_sha=H(dll)
with ZipFile(a.base) as z:
 assert z.testzip() is None
 original={}
 for k in z.namelist():
  if k.endswith("/"):continue
  parts=k.split("/",1)
  assert len(parts)==2 and parts[1] and ".." not in Path(parts[1]).parts
  original[parts[1]]=z.read(k)
assert H(original["renderer_sp_rend2_x64.dll"])==BASE_DLL_SHA
for req in ("ioWolfSP.x64.exe","RUN_DARKWOLF_4WEEK_MASTER.bat",
            "Main/DW_4WEEK_MASTER_PRODUCTION.cfg","Main/PRODUCTION_HIGH_QUALITY.cfg",
            "Main/cgame_sp_x64.dll","Main/qagame_sp_x64.dll","Main/ui_sp_x64.dll"):
 assert req in original,req
assert b'r_dlightMode' in dll and b'r_ssgiBrightSourceFix' in dll and b'r_forceSun' in dll
files=dict(original)
files["renderer_sp_rend2_x64.dll"]=dll
# Force mode 3 even when a user's existing archived wolfconfig had mode 2.
# All other official master profile settings remain byte-identical.
profile="Main/DW_4WEEK_MASTER_PRODUCTION.cfg"
assert b"r_ssgiBrightSourceFix" not in files[profile]
files[profile]+=b'\n// Targeted Escape1 hot-emitter receiver fix; prior Factory donor rejection preserved.\nseta r_ssgiBrightSourceFix "4"\n'
files["docs/SSGI_FIRE_SOURCE_RENDERER_SHA256.txt"]=(new_sha+"  renderer_sp_rend2_x64.dll\n").encode()
srcmanifest=json.loads((a.evidence/"PATCHED_SOURCE_MANIFEST.json").read_text())
assert srcmanifest["changed_renderer_files"]==["glsl/ssgi_fp.glsl","tr_backend.c","tr_init.c"],srcmanifest
files["docs/SSGI_FIRE_SOURCE_PATCH_MANIFEST.json"]=json.dumps(srcmanifest,indent=2).encode()
files["README_SSGI_FIRE_SOURCE_RU.txt"]=(
 "DarkWolf Rend2 4.4.6 RC4 FourWeek Master V03 - targeted SSGI hot emitter fix.\n"
 "Base original 24 October 2026; only the renderer DLL and master startup CFG change; all other original game files unchanged.\n"
 "SSGI mode3 bright-emitter receiver guard; retains old mode2 donor rejection and enabled SSGI.\n"
 "r_lightmap 1 presents baked lightmaps without SSGI diagnostic bars.\n"
 "No changes to world or sun shadows, Fire/Tesla containment, 3FX, LUT, bloom, MSAA or volumetrics.\n"
 "Requires your own licensed RTCW Main/pak*.pk3. Use RUN_DARKWOLF_4WEEK_MASTER.bat.\n"
 "Linux Mesa real Escape1/Factory validations are evidence, not Windows GPU FPS proof.\n"
 ).encode("utf-8")
if "docs/MASTER_RENDERER_SHA256.txt" in files:
 files["docs/historical/FOURWEEK_V03_ORIGINAL_RENDERER_SHA256.txt"]=files.pop("docs/MASTER_RENDERER_SHA256.txt")
 files["docs/MASTER_RENDERER_SHA256.txt"]=(new_sha+"  renderer_sp_rend2_x64.dll\n").encode()
if "docs/MASTER_SOURCE_DEFAULTS.json" in files:
 obj=json.loads(files["docs/MASTER_SOURCE_DEFAULTS.json"])
 obj["renderer_sha256"]=new_sha
 obj["parent_renderer_sha256"]=BASE_DLL_SHA
 files["docs/MASTER_SOURCE_DEFAULTS.json"]=json.dumps(obj,ensure_ascii=False,indent=2).encode()
if "MASTER_BUILD_PROVENANCE.json" in files:
 obj=json.loads(files["MASTER_BUILD_PROVENANCE.json"])
 obj["parent_renderer_sha256"]=BASE_DLL_SHA
 obj["compiled_renderer_sha256"]=new_sha
 obj["ssgi_fire_source_validation"]="See docs/SSGI_FIRE_SOURCE_PATCH_MANIFEST.json"
 files["MASTER_BUILD_PROVENANCE.json"]=json.dumps(obj,ensure_ascii=False,indent=2).encode()
files.pop("MASTER_SHA256SUMS.txt",None)
files["MASTER_SHA256SUMS.txt"]="".join(H(v)+"  "+k+"\n" for k,v in sorted(files.items())).encode()
original_no_render={k:v for k,v in original.items() if k!="renderer_sp_rend2_x64.dll" and k not in ("Main/DW_4WEEK_MASTER_PRODUCTION.cfg","MASTER_SHA256SUMS.txt","MASTER_BUILD_PROVENANCE.json","docs/MASTER_RENDERER_SHA256.txt","docs/MASTER_SOURCE_DEFAULTS.json")}
for k,v in original_no_render.items():
 assert files[k]==v,("unexpected modified source release content",k)
out=a.out/(NAME+".zip")
with ZipFile(out,"w",ZIP_DEFLATED,compresslevel=7) as z:
 for rel,contents in sorted(files.items()):
  info=ZipInfo(NAME+"/"+rel,date_time=(2026,10,25,0,0,0))
  info.compress_type=ZIP_DEFLATED
  info.external_attr=0o100644<<16
  z.writestr(info,contents)
with ZipFile(out) as z:
 assert z.testzip() is None
 for line in z.read(NAME+"/MASTER_SHA256SUMS.txt").decode().splitlines():
  digest,k=line.split("  ",1)
  assert H(z.read(NAME+"/"+k))==digest,k
 (a.out/(out.name+".sha256")).write_text(H(out.read_bytes())+"  "+out.name+"\n")
(a.out/"SSGI_REPACK_STATUS.json").write_text(json.dumps({
  "status":"CLEAN_SOURCE_AND_ARCHIVE_STRUCTURE_PASS","base_zip_sha256":BASE_ZIP_SHA,
  "base_renderer_sha256":BASE_DLL_SHA,"ssgi_renderer_sha256":new_sha,
  "new_zip_sha256":H(out.read_bytes()),"preserved_release_files":len(original_no_render),
  "requires_licensed_retail_assets":True},indent=2)+"\n")
print("SSGI_FOURWEEK_CLEAN_FULL_RELEASE_PACKAGE_PASS",out,H(out.read_bytes()))
