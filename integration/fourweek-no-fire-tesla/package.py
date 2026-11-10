#!/usr/bin/env python3
"""Full immutable FourWeek Master V03 Win64 package: 15-file Fire/Tesla reversal,
one SSGI pure-lightmap diagnostic guard, no experimental PCF4/V04 changes.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

NAME="DarkWolf_Rend2_v4.4.6_RC4_FourWeek_Master_V03_NoFireTesla_SSGI_Lightmap_Clean_Win64"
PARENT_DLL="4112890117f5fb16371ba8387ecd89203257eff361c22d83784db65c67eadd0a"
H=lambda data:hashlib.sha256(data).hexdigest()

def check_pe64(data):
    assert len(data)>100000 and data[:2]==b"MZ"
    offset=struct.unpack_from("<I",data,60)[0]
    assert data[offset:offset+4]==b"PE\0\0"
    assert struct.unpack_from("<H",data,offset+4)[0]==0x8664

p=argparse.ArgumentParser()
for key in ("base","renderer","cgame","source_manifest","out"):
    p.add_argument("--"+key.replace("_","-"),type=Path,required=True)
args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
manifest=json.loads(args.source_manifest.read_text())
assert manifest["fire_tesla_rollback"]=="FULL_EXACT_SOURCE_PATCH_REVERSE"
assert manifest["ssgi_lightmap_only_guard"]=="APPLIED"
assert len(manifest["reverted_fire_tesla_source_files"])==15
dll=args.renderer.read_bytes();cgame=args.cgame.read_bytes()
for b in (dll,cgame):check_pe64(b)
dll_sha,cgame_sha=H(dll),H(cgame)
assert dll_sha!=PARENT_DLL
assert b"r_ssgi" in dll and b"r_forceSun" in dll
for value in ("r_dwCas","r_dwA2C","r_dwLut","r_volumetricFire","r_dlightMode","r_bloom"):
    assert value.encode() in dll
for forbidden in (b"DARKWOLF_REF_WORLD_OCCLUSION",b"u_DlightWorldMap",b"DlightWorldVisibility"):
    assert forbidden not in dll,(forbidden,"World-occlusion mechanism remains")

with ZipFile(args.base) as z:
    assert z.testzip() is None
    files={}
    for entry in z.infolist():
        if entry.is_dir():continue
        a=entry.filename.split("/",1)
        assert len(a)==2 and a[1] and ".." not in Path(a[1]).parts
        assert a[1] not in files
        files[a[1]]=z.read(entry)
assert H(files["renderer_sp_rend2_x64.dll"])==PARENT_DLL
old_cgame_sha=H(files["Main/cgame_sp_x64.dll"])
assert old_cgame_sha!=cgame_sha, "cgame still contains Fire/Tesla change"
for name in ("ioWolfSP.x64.exe","Main/qagame_sp_x64.dll","Main/ui_sp_x64.dll",
             "Main/PRODUCTION_HIGH_QUALITY.cfg","Main/DW_4WEEK_MASTER_PRODUCTION.cfg",
             "RUN_DARKWOLF_4WEEK_MASTER.bat","SDL264.dll","OpenAL64.dll"):
    assert name in files,name
original=dict(files)
files["renderer_sp_rend2_x64.dll"]=dll
files["Main/cgame_sp_x64.dll"]=cgame

# Remove the actual old containment source patch from distribution and the
# misleading claim that containment is still enabled.
removed=[]
for key in list(files):
    if key=="README_FIRE_TESLA_CONTAINMENT_RU.txt" or key.lower().endswith("/containment.patch"):
        removed.append(key);del files[key]
assert "docs/containment.patch" in removed and "README_FIRE_TESLA_CONTAINMENT_RU.txt" in removed
if "docs/MASTER_RENDERER_SHA256.txt" in files:
    files["docs/MASTER_RENDERER_SHA256.txt"]=(dll_sha+"  renderer_sp_rend2_x64.dll\n").encode()
if "docs/MASTER_SOURCE_DEFAULTS.json" in files:
    obj=json.loads(files["docs/MASTER_SOURCE_DEFAULTS.json"])
    obj["renderer_sha256"]=dll_sha;obj["parent_renderer_sha256"]=PARENT_DLL
    obj["fire_light_containment"]="REMOVED_EXACT_OCT15_SOURCE_REVERSE"
    obj["ssgi_lightmap_diagnostic_guard"]="ENABLED_ONLY_WHEN_R_LIGHTMAP_1"
    files["docs/MASTER_SOURCE_DEFAULTS.json"]=json.dumps(obj,indent=2,ensure_ascii=False).encode()+b"\n"
if "MASTER_BUILD_PROVENANCE.json" in files:
    obj=json.loads(files["MASTER_BUILD_PROVENANCE.json"])
    obj["release"]=NAME
    obj["parent_tag"]="v4.4.6-rc4-fourweek-master-sourcedefaultson-20261024"
    obj["compiled_renderer_sha256"]=dll_sha
    obj["parent_renderer_sha256"]=PARENT_DLL
    obj["compiled_cgame_sha256"]=cgame_sha
    obj["parent_cgame_sha256"]=old_cgame_sha
    obj["fire_tesla_containment"]="REVERTED_ENTIRE_OCTOBER_15_SOURCE_PATCH"
    obj.pop("containment_patch_sha256",None)
    obj["source_chain"]=["Official Oct24 FourWeek Master V03",
                         "Reversal of exact 15-file Fire/Tesla architectural containment patch",
                         "Diagnostic-only SSGI isolation when r_lightmap 1"]
    if "game_module_sha256" in obj:
        obj["game_module_sha256"]["Main/cgame_sp_x64.dll"]=cgame_sha
    obj["windows_real_gpu_fps"]="PENDING_USER"
    files["MASTER_BUILD_PROVENANCE.json"]=json.dumps(obj,indent=2,ensure_ascii=False).encode()+b"\n"
files["README_NO_FIRE_TESLA_RU.txt"]=(
    "DarkWolf ioRTCW Rend2 v4.4.6 RC4 FourWeek Master V03 - NO FIRE/TESLA CONTAINMENT\n"
    "Official FourWeek Master V03: all effects and optimizations retained.\n"
    "Reverted the 15-file Oct 15 Fire/Tesla wall-light containment patch exactly.\n"
    "This restores light behavior from before architectural Fire/Tesla filtering;\n"
    "light may again bleed through some walls. CSM, Bloom, SSGI, volumetrics,\n"
    "Texture/Material Fidelity, CAS, A2C, LUT V03, 4x MSAA and dlight mode 2 remain.\n"
    "SSGI r_lightmap 1 diagnostic stripes fixed; SSGI gameplay r_lightmap 0 unchanged.\n"
    "NO experimental PCF4 or SSGI Fire Receiver V04 changes included.\n"
    "Requires legally owned RTCW Main/pak*.pk3. Launch RUN_DARKWOLF_4WEEK_MASTER.bat.\n"
    "Windows gaming GPU quality/FPS requires user validation.\n"
).encode()
files["docs/NO_FIRE_TESLA_ROLLBACK_SOURCE_MANIFEST.json"]=json.dumps(manifest,ensure_ascii=False,indent=2).encode()+b"\n"

# Guard the entire release: no other game, effects, DLL, config or executable changed.
allowed={"renderer_sp_rend2_x64.dll","Main/cgame_sp_x64.dll","docs/MASTER_RENDERER_SHA256.txt",
         "docs/MASTER_SOURCE_DEFAULTS.json","MASTER_BUILD_PROVENANCE.json",
         "MASTER_SHA256SUMS.txt",*removed}
for rel,b in original.items():
    if rel in allowed:continue
    assert rel in files and files[rel]==b,("unexpected non-rollback production edit",rel)
for rel in ("Main/darkwolf_ignition_rc_v0_6.pk3","Main/DW_4WEEK_MASTER_PRODUCTION.cfg"):
    assert H(files[rel])==H(original[rel]),("visual effect/quality settings changed",rel)
files.pop("MASTER_SHA256SUMS.txt",None)
files["MASTER_SHA256SUMS.txt"]="".join(H(data)+"  "+rel+"\n" for rel,data in sorted(files.items())).encode()
out=args.out/(NAME+".zip")
with ZipFile(out,"w",ZIP_DEFLATED,compresslevel=7) as z:
    for rel,data in sorted(files.items()):
        assert ".." not in Path(rel).parts and not rel.startswith("/")
        e=ZipInfo(NAME+"/"+rel,date_time=(2026,10,25,0,0,0))
        e.compress_type=ZIP_DEFLATED;e.external_attr=0o100644<<16
        z.writestr(e,data)
with ZipFile(out) as z:
    assert z.testzip() is None
    for row in z.read(NAME+"/MASTER_SHA256SUMS.txt").decode().splitlines():
        h,key=row.split("  ",1)
        assert H(z.read(NAME+"/"+key))==h,key
    assert len(z.namelist())>=35
zip_sha=H(out.read_bytes())
(args.out/(out.name+".sha256")).write_text(zip_sha+"  "+out.name+"\n")
proof={"status":"COMPLETE_CLEAN_WIN64_ZIP_VERIFIED","zip":out.name,
       "zip_sha256":zip_sha,"renderer_sha256":dll_sha,"cgame_sha256":cgame_sha,
       "parent_renderer_sha256":PARENT_DLL,"parent_cgame_sha256":old_cgame_sha,
       "source_files_reverted":15,"ssgi_lightmap_guard":True,
       "replaced_runtime_modules":["renderer_sp_rend2_x64.dll","Main/cgame_sp_x64.dll"],
       "all_other_game_files_byte_identical":True,"no_retail_assets":True,
       "windows_gpu_test":"NOT_PERFORMED"}
(args.out/"RELEASE_VALIDATION.json").write_text(json.dumps(proof,indent=2)+"\n")
print("FOURWEEK_NO_FIRE_TESLA_FULL_WIN64_RELEASE_PASS",json.dumps(proof),flush=True)
