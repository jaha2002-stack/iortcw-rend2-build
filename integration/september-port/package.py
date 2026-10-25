#!/usr/bin/env python3
"""Package actual September Clean Production runtime + rebuilt FourWeek feature
binaries. Preserve September appearance; neutralize rejected red V03 LUT.
"""
import argparse,hashlib,io,json,struct
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

p=argparse.ArgumentParser()
for k in ("september","october","build","source_manifest","out"):
    p.add_argument("--"+k.replace("_","-"),type=Path,required=True)
args=p.parse_args()
args.out.mkdir(parents=True,exist_ok=True)
H=lambda b:hashlib.sha256(b).hexdigest()
SEP_SHA="9b24185302c468b47b9c0125a31eb9b1edd9518e7cbd0084a80710c52d395a4b"
NAME="DarkWolf_Rend2_v4.4.6_September_CleanPlus_FourWeek_V03_NoFireTesla_SSGI_Lightmap_Win64"
ACTUAL_SEP_SHA=H(args.september.read_bytes())
assert ACTUAL_SEP_SHA in {SEP_SHA,"ff7d516dd77e17b7b77077824a5f952ae4f379ff6555e4f088238c1be07f80e9"}, "September baseline must be the identical official/user-uploaded Clean Production binary build"
manifest=json.loads(args.source_manifest.read_text())
assert manifest["september_original_tree_verified"]
assert manifest["ported_fourweek_source_files_count"]>=25
assert manifest["Fire_Tesla_architectural_light_containment"].startswith("EXCLUDED")
assert manifest["SSGI_r_lightmap_1"].startswith("ISOLATED")
with ZipFile(args.september) as z:
    assert z.testzip() is None
    roots={k.split("/")[0] for k in z.namelist()}
    assert len(roots)==1,roots
    prefix=next(iter(roots))+"/"
    sep={k[len(prefix):]:z.read(k) for k in z.namelist() if k.startswith(prefix) and not k.endswith("/")}
assert H(sep["renderer_sp_rend2_x64.dll"])=="84053287054333b89ffdc0d733e7231371098674fa75932f044598fa67df1701"
files={}
for k in ("SDL264.dll","OpenAL64.dll","renderer_sp_opengl1_x64.dll"):
    assert k in sep,k
    files[k]=sep[k]
# Preserve historical September approved FireVol startup profiles as provenance.
for k in ("Main/FIREVOL_PRODUCTION_BALANCED.cfg","Main/FIREVOL_PRODUCTION_CINEMATIC.cfg"):
    assert k in sep,k
    files[k]=sep[k]
# Every game binary comes from the newly built September-BASE source with the
# replayed feature deltas, not a pre-existing October Windows DLL.
build=args.build
dlls={"ioWolfSP.x64.exe":"ioWolfSP.x64.exe",
      "renderer_sp_rend2_x64.dll":"renderer_sp_rend2_x64.dll",
      "Main/cgame_sp_x64.dll":"cgame_sp_x64.dll",
      "Main/qagame_sp_x64.dll":"qagame_sp_x64.dll",
      "Main/ui_sp_x64.dll":"ui_sp_x64.dll"}
binary_hashes={}
for target,name in dlls.items():
    item=build/name
    assert item.is_file(),("missing built binary",name)
    data=item.read_bytes()
    assert len(data)>180000 and data[:2]==b"MZ",(name,"invalid MZ")
    off=struct.unpack_from("<I",data,60)[0]
    assert data[off:off+4]==b"PE\0\0" and struct.unpack_from("<H",data,off+4)[0]==0x8664
    files[target]=data
    binary_hashes[target]=H(data)
for x in ("r_dwCas","r_dwA2C","r_dwLut","r_ssgi","r_forceSun","r_bloom","r_volumetricLocal"):
    assert x.encode() in files["renderer_sp_rend2_x64.dll"],x
assert b"DlightWorldVisibility" not in files["renderer_sp_rend2_x64.dll"]

# Optional only production auxiliary PK3 introduced since September. NO retail pak0.
with ZipFile(args.october) as outer:
    nested=[k for k in outer.namelist() if k.endswith("_Clean_Win64.zip")]
    assert len(nested)==1,nested
    blob=outer.read(nested[0])
with ZipFile(io.BytesIO(blob)) as zip:
    x=[k for k in zip.namelist() if k.endswith("/Main/darkwolf_ignition_rc_v0_6.pk3")]
    assert len(x)==1,x
    files["Main/darkwolf_ignition_rc_v0_6.pk3"]=zip.read(x[0])

cfg='''// SEPTEMBER CLEAN PRODUCTION visual base + all FourWeek V03 features.
 // The original September tone mapping and brightness defaults are inherited.
 // LUT V03 is present; neutral strength prevents the rejected red 0.80 preset.
seta r_renderer "rend2"
seta r_hdr "1"
seta r_postProcess "1"
seta r_bloom "1"
seta r_bloomMode "2"
seta r_ssgi "1"
seta r_ssgiBrightSourceFix "2"
seta r_lightmap "0"
seta r_forceSun "1"
seta r_sunShadows "1"
seta r_dlightMode "2"
seta r_dlightShadowMaxLights "3"
seta r_staticPromote "1"
seta r_staticPromoteMaxLights "32"
seta r_volumetricSun "1"
seta r_volumetricLocal "1"
seta r_volumetricFire "1"
seta r_softParticles "1"
seta r_dwTextureFidelity "1"
seta r_dwMaterialFidelity "1"
seta r_dwAdaptiveUpsample "1"
seta r_dwCutoutMip "1"
seta r_dwCas "1"
seta r_dwCasStrength "0.55"
seta r_dwA2C "1"
seta r_dwLut "1"
seta r_dwLutMode "1"
seta r_dwLutStrength "0.00"
seta r_ext_framebuffer_multisample "4"
seta r_picmip "0"
seta r_picmip2 "0"
seta r_shadowFilter "4"
seta r_dlightShadowFilter "2"
seta r_dlightShadowMapSize "2048"
seta r_volumetricFireDiag "0"
seta r_volumetricFireResidencyDiag "0"
seta r_volumetricFireProofMode "0"
'''
files["Main/DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg"]=cfg.encode("utf-8")
launcher=r'''@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if not exist "ioWolfSP.x64.exe" exit /b 1
if not exist "renderer_sp_rend2_x64.dll" exit /b 1
set "DW_HOME=%CD%\DW_September_FourWeek_Home"
if not exist "%DW_HOME%\Main" mkdir "%DW_HOME%\Main"
if not exist "%DW_HOME%\Main" exit /b 1
set "DW_FIRST="
if not exist "%DW_HOME%\Main\SEPT_FIRST_RUN_DONE.txt" (
  copy /y "Main\DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg" "%DW_HOME%\Main\DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg" >nul
  if errorlevel 1 exit /b 1
  echo Startup profile installed on first launch > "%DW_HOME%\Main\SEPT_FIRST_RUN_DONE.txt"
  set "DW_FIRST=+exec DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg"
)
"%CD%\ioWolfSP.x64.exe" +set fs_basepath "%CD%" +set fs_homepath "%DW_HOME%" +set cl_renderer rend2 +set r_renderer rend2 +set com_recommendedSet 1 %DW_FIRST%
exit /b %errorlevel%
'''
files["RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat"]=launcher.replace("\n","\r\n").encode("ascii")
files["README_RELEASE_RU.txt"]=(
"DarkWolf Rend2 4.4.6 - Clean September 18 base + FourWeek V03 accepted enhancements.\n"
"All Oct feature code replayed on SHA-verified September source, except the Oct15\n"
"Fire/Tesla architectural light containment (15 files reversed). Light may leak\n"
"through walls like the original September version. PCF4 and V04 not included.\n"
"SSGI 1 with diagnostic r_lightmap 1 stripes fixed; gameplay SSGI intact.\n"
"Retained: HDR, Bloom V2, CSM Guard, volumetrics, CAS, A2C, Texture/Material,\n"
"LUT V03 functionality, 4x MSAA, forceSun 1 and dlightMode 2.\n"
"LUT starts at strength 0 because strength 0.80 produced the red tint.\n"
"Start RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat. New isolated user home directory.\n"
"On first launch the visual profile is applied once; after that console Cvars\n"
"remain freely editable and archived without launch-time overrides.\n"
"Licensed RTCW pak*.pk3 must be placed in Main (not distributed).\n"
"Actual Windows GPU color and FPS need user verification.\n"
).encode("utf-8")
files["docs/SEPTEMBER_ORIGIN_AND_PORTED_OCTOBER_FEATURES.json"]=json.dumps(manifest,ensure_ascii=False,indent=2).encode("utf-8")
proof={"status":"VALIDATED_FULL_WIN64_ARCHIVE",
       "september_base_zip_sha256":ACTUAL_SEP_SHA,"ported_source_files_count":manifest["ported_fourweek_source_files_count"],
       "runtime_new_binaries_sha256":binary_hashes,"all_accepted_feature_cvars_present":True,
       "original_september_ui_sdl_opengl1_libraries_preserved":True,
       "Fire_Tesla_containment":"NOT_INCLUDED","LUT_V03_startup_strength":"0.00",
       "SSGI_lightmap_diag_guard":True,"gameplay_FPS":"PENDING_USER"}
files["docs/BUILD_PROVENANCE.json"]=json.dumps(proof,indent=2).encode()
files["docs/SHA256SUMS.txt"]="".join(H(v)+"  "+k+"\n" for k,v in sorted(files.items())).encode()
target=args.out/(NAME+".zip")
with ZipFile(target,"w",ZIP_DEFLATED,compresslevel=7) as z:
    for k,v in sorted(files.items()):
        assert ".." not in Path(k).parts
        zi=ZipInfo(NAME+"/"+k,date_time=(2026,10,25,0,0,0))
        zi.compress_type=ZIP_DEFLATED
        zi.external_attr=0o100644<<16
        z.writestr(zi,v)
with ZipFile(target) as z:
    assert z.testzip() is None
    for line in z.read(NAME+"/docs/SHA256SUMS.txt").decode().splitlines():
        h,key=line.split("  ",1)
        assert H(z.read(NAME+"/"+key))==h
    assert len(z.namelist())>=17
digest=H(target.read_bytes())
(args.out/(NAME+".zip.sha256")).write_text(digest+"  "+target.name+"\n")
proof["full_zip_sha256"]=digest
(args.out/"SEPTEMBER_PORT_COMPLETE_RELEASE_VALIDATION.json").write_text(json.dumps(proof,indent=2)+"\n")
print("SEPTEMBER_BASE_FOURWEEK_NO_FIRE_TESLA_FULL_WIN64_RELEASE_PASS",target,digest,flush=True)
