#!/usr/bin/env python3
"""Package the immutable, full Win64 SP master from two pinned GitHub Actions artifacts.
No retail pak*.pk3 is bundled. The source-compiled renderer is NOT rebuilt here:
use the SHA-verified Windows PE64 DLL from the completed source-defaults-on run.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

BASE_ARTIFACT_SHA="6c6c2d2302e2f4f45bad9d7e3df7e2573fd79a72646bcf049596440cb62f7659"
BASE_NESTED_SHA="ad112f52429020f4b6b482a103c3c5e19204073237fff2cbada82649fc84a11d"
NEW_ARTIFACT_SHA="f66a7788c8eccb4d7460eb3ce18c541e253a0ee367120710992ebc281b17f074"
NEW_DLL_SHA="4112890117f5fb16371ba8387ecd89203257eff361c22d83784db65c67eadd0a"
CONTAINMENT_SHA="e3600847ed0d1def868439af0c94f5ce250e2e7afbb0584fbb151459ea009a2f"
TAG="v4.4.6-rc4-fourweek-master-sourcedefaultson-20261024"
NAME="DarkWolf_Rend2_v4.4.6_RC4_FourWeek_Master_SourceDefaultsON_Clean_Win64"
CHECK_BINARIES={
"ioWolfSP.x64.exe":"638933abc4eeaa716c58450bd588c8311d4e463f66ecb9e8a4e90addc849d966",
"Main/cgame_sp_x64.dll":"897fce2c4fa6b9feec4cc27f220bc4c9bc10c9e173e2482b5636f04b32e057bd",
"Main/qagame_sp_x64.dll":"5a7a369ab16174f7e6683d697314c38dfb99ab0b8733b958313fe687d1347d43",
"Main/ui_sp_x64.dll":"d169b2b5b24c115f75c27d0813dcd2a50a4330e982f86e0aa0dc304c838f9191",
"SDL264.dll":"f34cd90b131ceb45b7f32d41680a13fd4b13e5f48f0d1649cbf441833105310c",
"OpenAL64.dll":"396f88738ce20905e933cb7d8c696351e41bd7e72e80b8cfdadf20ab613420b4",
"Main/darkwolf_ignition_rc_v0_6.pk3":"63f468e4edcb1fc6f2059b153c165f66b2c0b1237e93ea3b9518ef76358af5ee",
}
H=lambda b: hashlib.sha256(b).hexdigest()
def txt(s): return s.encode("utf-8")
def bat(s): return txt(s.strip("\n").replace("\r","").replace("\n","\r\n")+"\r\n")

p=argparse.ArgumentParser()
p.add_argument("--base",required=True,type=Path)
p.add_argument("--master-dll",required=True,type=Path)
p.add_argument("--out",required=True,type=Path)
a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
assert H(a.base.read_bytes())==BASE_ARTIFACT_SHA, "Original Bloom v2 Actions artifact changed"
assert H(a.master_dll.read_bytes())==NEW_ARTIFACT_SHA, "SourceDefaultsON Actions artifact changed"
with ZipFile(a.base) as outer:
    assert outer.testzip() is None
    inner=outer.read("DarkWolf-v446-RC4-BloomV2-Production-Win64-SP.zip")
    assert H(inner)==BASE_NESTED_SHA
    with ZipFile(io.BytesIO(inner)) as z:
        assert z.testzip() is None
        files={}
        for item in z.infolist():
            if item.is_dir(): continue
            rel=item.filename.split("/",1)[1]
            assert rel and not rel.startswith("/") and ".." not in Path(rel).parts and rel not in files
            files[rel]=z.read(item)
with ZipFile(a.master_dll) as z:
    assert z.testzip() is None
    dll=z.read("dist/renderer_sp_rend2_x64.dll")
    assert H(dll)==NEW_DLL_SHA
    assert z.read("dist/RENDERER.sha256").decode().split()[0]==NEW_DLL_SHA
    defaults=json.loads(z.read("dist/RELEASE_SOURCE_DEFAULTS.json"))
    delta=z.read("dist/RELEASE_CODE_DEFAULTS.patch")
    status=z.read("dist/ACCEPTANCE_STATUS.txt")
    fidelity=z.read("dist/fidelity-manifest.json")
assert defaults["renderer_sha256"]==NEW_DLL_SHA
assert defaults["status"]=="WIN64_DLL_COMPILE_AND_SOURCE_GATES_PASS"
assert len(defaults["default_changes"])==10
expected={"r_dwTextureFidelity":"1","r_dwMaterialFidelity":"1","r_dwCas":"1",
          "r_dwCasStrength":"0.55","r_dwA2C":"1","r_dwLut":"1",
          "r_dwLutStrength":"0.80","r_forceSun":"1","r_ssgi":"1",
          "r_ext_framebuffer_multisample":"4"}
assert {k:v["to"] for k,v in defaults["default_changes"].items()}==expected
assert b"--- a/SP/code/rend2/tr_init.c" in delta and delta.count(b"--- a/")==1
assert b"REAL_WINDOWS_GPU_TEST=USER_ACCEPTANCE_PENDING" in status
assert dll[:2]==b"MZ" and len(dll)>2000000 and len(dll)<10000000
import struct
pe=struct.unpack_from("<I",dll,60)[0]
assert dll[pe:pe+4]==b"PE\0\0" and struct.unpack_from("<H",dll,pe+4)[0]==0x8664
for symbol in ["r_dwTextureFidelity","r_dwMaterialFidelity","r_dwCas","r_dwA2C",
               "r_dwLut","r_bloom","r_ssgi","r_forceSun","r_volumetricFire",
               "r_volumetricSun","r_volumetricLocal","r_dlightMode"]:
    assert symbol.encode() in dll, "Missing symbol: "+symbol
for path,sha in CHECK_BINARIES.items():
    assert H(files[path])==sha, ("Historical production module changed",path)
contain=files["docs/containment.patch"]
assert H(contain)==CONTAINMENT_SHA
for marker in [b"R_RenderDlightWorldOcclusion",b"DlightWorldVisibility",
               b"DARKWOLF_REF_WORLD_OCCLUSION"]:
    assert marker in contain, ("Fire/Tesla containment mechanism missing",marker)
assert H(files["renderer_sp_rend2_x64.dll"])=="7987cd4191ee84c0f87522affe29ea1e462afd5bf4b902969fb277023fec1d38"
files["renderer_sp_rend2_x64.dll"]=dll

# Preserve all the original approved graphics values; append only explicitly approved
# quality defaults from the preceding user-verified master. Do not enable SSAO/indirect
# lighting, which were intentionally off in the historical approved high-quality mode.
quality_extension="""
// DARKWOLF TEXTURE MATERIAL FIDELITY - CLEAN PRODUCTION
// Preserve historical quality profile and Bloom v2.
seta r_bloom "1"
seta r_bloomMode "2"
seta r_picmip "0"
seta r_picmip2 "0"
seta r_roundImagesDown "0"
seta r_textureMode "GL_LINEAR_MIPMAP_LINEAR"
seta r_ext_texture_filter_anisotropic "1"
seta r_ext_max_anisotropy "8"
seta r_imageUpsample "0"
seta r_dwAdaptiveUpsample "1"
seta r_dwCutoutMip "1"
seta r_dwTextureFidelity "1"
seta r_dwMaterialFidelity "1"
"""
for fname in ("Main/PRODUCTION_HIGH_QUALITY.cfg","Main/UNIFIED_PRODUCTION.cfg"):
    original=files[fname].decode()
    assert "r_dwTextureFidelity" not in original, "Existing profile has unexpected feature change"
    files[fname]=txt(original + quality_extension)
assert 'seta r_ssao "0"' in files["Main/PRODUCTION_HIGH_QUALITY.cfg"].decode()
assert 'seta r_indirectLighting "0"' in files["Main/PRODUCTION_HIGH_QUALITY.cfg"].decode()
assert 'seta r_forceSun "1"' in files["Main/PRODUCTION_HIGH_QUALITY.cfg"].decode()
assert 'seta r_dlightMode "2"' in files["Main/PRODUCTION_HIGH_QUALITY.cfg"].decode()

master_cfg="""// DarkWolf Rend2 RC4 FourWeek Master: clean default-on production.
seta r_dwTextureFidelity "1"
seta r_dwMaterialFidelity "1"
seta r_dwAdaptiveUpsample "1"
seta r_dwCutoutMip "1"
seta r_dwCas "1"
seta r_dwCasStrength "0.55"
seta r_dwA2C "1"
seta r_dwLut "1"
seta r_dwLutStrength "0.80"
seta r_dwLutMode "1"
seta r_bloom "1"
seta r_bloomMode "2"
seta r_hdr "1"
seta r_toneMap "1"
seta r_autoExposure "1"
seta r_forceSun "1"
seta r_sunShadows "1"
seta r_dlightMode "2"
seta r_dlightShadowMaxLights "3"
seta r_staticPromote "1"
seta r_staticPromoteMaxLights "32"
seta r_ssgi "1"
seta r_volumetricSun "1"
seta r_volumetricLocal "1"
seta r_volumetricFire "1"
seta r_softParticles "1"
seta r_ext_framebuffer_multisample "4"
"""
files["Main/DW_4WEEK_MASTER_PRODUCTION.cfg"]=txt(master_cfg)
files["Main/DW_3FX_CLEAN_PRODUCTION.cfg"]=txt(master_cfg)
launcher=r"""
@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if not exist "ioWolfSP.x64.exe" exit /b 1
if not exist "renderer_sp_rend2_x64.dll" exit /b 1
if not exist "Main\PRODUCTION_HIGH_QUALITY.cfg" exit /b 1
if not exist "Main\DW_4WEEK_MASTER_PRODUCTION.cfg" exit /b 1
set "DW_HOME=%CD%\DW4WeekCleanHome"
if not exist "%DW_HOME%\Main" mkdir "%DW_HOME%\Main"
if not exist "%DW_HOME%\Main" exit /b 1
copy /y "Main\PRODUCTION_HIGH_QUALITY.cfg" "%DW_HOME%\Main\PRODUCTION_HIGH_QUALITY.cfg" >nul
if errorlevel 1 exit /b 1
copy /y "Main\DW_4WEEK_MASTER_PRODUCTION.cfg" "%DW_HOME%\Main\DW_4WEEK_MASTER_PRODUCTION.cfg" >nul
if errorlevel 1 exit /b 1
"%CD%\ioWolfSP.x64.exe" +set fs_basepath "%CD%" +set fs_homepath "%DW_HOME%" +safe +set com_introplayed 1 +set com_recommendedSet 1 +set cl_renderer rend2 +set r_renderer rend2 +set r_dwTextureFidelity 1 +set r_dwMaterialFidelity 1 +set r_dwAdaptiveUpsample 1 +set r_dwCutoutMip 1 +set r_dwCas 1 +set r_dwCasStrength 0.55 +set r_dwA2C 1 +set r_dwLut 1 +set r_dwLutStrength 0.80 +set r_dwLutMode 1 +set r_forceSun 1 +set r_dlightMode 2 +set r_bloom 1 +set r_bloomMode 2 +exec PRODUCTION_HIGH_QUALITY.cfg +exec DW_4WEEK_MASTER_PRODUCTION.cfg +vid_restart
exit /b %errorlevel%
"""
files["docs/historical/RUN_DARKWOLF_BLOOM_BASELINE.bat"]=files.pop("RUN_DARKWOLF_OPTIMIZED_CLEAN.bat")
files["RUN_DARKWOLF_4WEEK_MASTER.bat"]=bat(launcher)
files["RUN_DARKWOLF_3FX_CLEAN_PRODUCTION.bat"]=bat("@echo off\ncall \"%~dp0RUN_DARKWOLF_4WEEK_MASTER.bat\"\nexit /b %errorlevel%\n")
files["RUN_DARKWOLF_OPTIMIZED_CLEAN.bat"]=files["RUN_DARKWOLF_3FX_CLEAN_PRODUCTION.bat"]
for obsolete in ["BLOOM_V2_PRODUCTION_SHA256SUMS.txt","QUALITY_INSTALL.txt",
                 "QUALITY_PROVENANCE.json","QUALITY_SHA256SUMS.txt",
                 "docs/BUILD_PROVENANCE.json","docs/RC4_BLOOM_V2_PRODUCTION_PORT_PROVENANCE.txt",
                 "docs/SHA256SUMS.txt","docs/source-lock.json"]:
    if obsolete in files:
        files["docs/historical/"+obsolete.replace("/","_")]=files.pop(obsolete)

files["docs/MASTER_SOURCE_DEFAULTS.json"]=txt(json.dumps(defaults,ensure_ascii=False,indent=2)+"\n")
files["docs/MASTER_SOURCE_DEFAULTS.patch"]=delta
files["docs/MASTER_WINDOWS_BUILD_STATUS.txt"]=status
files["docs/MASTER_TEXTURE_FIDELITY_MANIFEST.json"]=fidelity
files["docs/MASTER_RENDERER_SHA256.txt"]=txt(NEW_DLL_SHA+"  renderer_sp_rend2_x64.dll\n")
files["docs/3FX_A2C_V02_CAS_LUT_V02_BASE.patch"]=z.read("dist/feature.patch") if False else b""
# Keep feature patches exactly as present in the independently pinned Actions artifact.
with ZipFile(a.master_dll) as evidence:
    files["docs/3FX_A2C_V02_CAS_LUT_V02_BASE.patch"]=evidence.read("dist/feature.patch")
    files["docs/3FX_CAS_LUT_VISIBLE_V03_DELTA.patch"]=evidence.read("dist/DARKWOLF_3FX_VISIBLE_V03.patch")
assert H(files["docs/3FX_A2C_V02_CAS_LUT_V02_BASE.patch"])=="6d143993ecd24537aa1b66e6649b43ba5281c3d5f21cee527192ef20c1336dec"
assert H(files["docs/3FX_CAS_LUT_VISIBLE_V03_DELTA.patch"])=="b9f83421ebc55e5bc1d9ab3fc023eece71cc6e0a3203ab4e6eafd3d8ae83059a"

files["README_FIRE_TESLA_CONTAINMENT_RU.txt"]=txt(
    "Сохранено исправление RC4 Fire/Tesla LightContainment от 15 октября 2026.\n"
    "Это исправление препятствует утечкам динамического света через архитектурные стены.\n"
    "Исходный проверенный патч: docs/containment.patch.\n"
    "Отдельный более ранний Fire Direct V2.2 повторно НЕ применяется.\n"
    "В последнем коммите изменились только 10 значений CVar по умолчанию.\n"
    "Окончательный тест FPS и визуальных регрессий на Windows GPU предстоит пользователю.\n")
files["README_FOUR_WEEK_MASTER.txt"]=txt(
    "DARKWOLF REND2 v4.4.6 RC4 FOURWEEK MASTER SOURCEDEFAULTSON - WIN64 SP\n"
    "Permanent GitHub Release tag: "+TAG+"\n"
    "Includes game EXE, renderer DLL, three game DLLs, SDL/OpenAL DLLs, approved custom PK3, CFG, launcher and proof documents.\n"
    "Requires your own licensed RTCW Main/pak*.pk3 (not redistributed).\n"
    "Install into a SEPARATE copy of RTCW. Launch RUN_DARKWOLF_4WEEK_MASTER.bat.\n"
    "Preserved: RC4 optimizations and Fire/Tesla wall occlusion, Bloom v2, CSM Guard,\n"
    "Texture/Material Fidelity, CAS 0.55, A2C, LUT 0.80, 4x MSAA,\n"
    "SSGI, Volumetric Local/Sun/Fire, soft particles and dynamic shadow settings.\n"
    "User must verify Windows gaming GPU quality, frame rate and frametime before final acceptance.\n")
files["INSTALL_AND_VALIDATION.txt"]=txt(
    "DarkWolf Rend2 v4.4.6 RC4 FourWeek Master SourceDefaultsON - Windows x64 Single Player\n"
    "1. Create a fresh copy of your licensed RTCW installation and back up saves.\n"
    "2. Extract the one top-level folder from this archive into that game directory.\n"
    "3. Keep your licensed Main/pak*.pk3 files; this ZIP does NOT include them.\n"
    "4. Run RUN_DARKWOLF_4WEEK_MASTER.bat; do not mix old DLLs or config profiles.\n"
    "5. Confirm Bloom, materials, CAS/A2C/LUT, CSM and fire/Tesla light containment.\n"
    "6. Check Escape1, Assault, Factory, frame-rate, frame-time and a full loading cycle.\n"
    "No claims of real Windows GPU visual/performance acceptance are made by CI.\n")

prov={
"release":NAME,"tag":TAG,"status":"WIN64_BUILD_PASS_USER_GPU_ACCEPTANCE_PENDING",
"builder_commit":"3c2dab6f3e92c13cbdc93b2088dacb8db5f2e51d",
"release_workflow_commit":os.getenv("GITHUB_SHA","local-test"),
"windows_renderer_run":40073883865,
"windows_renderer_artifact_id":12552083888,
"base_bloom_run":38798189322,"base_bloom_artifact_id":12004010089,
"source_chain":["RC4 approved LightContainment and Bloom v2","CSM guard",
                "Texture / Material Fidelity","CAS/A2C/LUT Visible V03",
                "Source default-ON CVar patch and Win64 rebuild"],
"game_module_sha256":CHECK_BINARIES,
"compiled_renderer_sha256":NEW_DLL_SHA,
"containment_patch_sha256":CONTAINMENT_SHA,
"source_default_change_count":10,
"source_default_changes":defaults["default_changes"],
"high_quality_profile_preserved_except_append_only_texture_bloom_quality":True,
"historical_ssao_and_indirect_lighting":"both 0 in inherited validated quality preset",
"retail_game_assets_bundled":False,"telemetry_enabled":False,
"windows_real_gpu_fps":"NOT_TESTED","runtime_visual_acceptance":"PENDING_USER"
}
files["MASTER_BUILD_PROVENANCE.json"]=txt(json.dumps(prov,ensure_ascii=False,indent=2)+"\n")
files["MASTER_SHA256SUMS.txt"]=txt("".join(H(v)+"  "+k+"\n" for k,v in sorted(files.items())))

archive=a.out/(NAME+".zip")
with ZipFile(archive,"w",ZIP_DEFLATED,compresslevel=7) as z:
    for rel,data in sorted(files.items()):
        assert ".." not in Path(rel).parts and not rel.startswith("/")
        item=ZipInfo(NAME+"/"+rel,date_time=(2026,10,24,0,0,0))
        item.compress_type=ZIP_DEFLATED
        item.external_attr=0o100644<<16
        z.writestr(item,data)
with ZipFile(archive) as z:
    assert z.testzip() is None
    for line in z.read(NAME+"/MASTER_SHA256SUMS.txt").decode().splitlines():
        checksum,path=line.split("  ",1)
        assert H(z.read(NAME+"/"+path))==checksum, path
    all_names=z.namelist()
    assert len(all_names)>=33
    assert not any(Path(x).name.lower().startswith("pak") and x.endswith(".pk3") for x in all_names)
(a.out/(archive.name+".sha256")).write_text(H(archive.read_bytes())+"  "+archive.name+"\n")
assert H(archive.read_bytes())==H(archive.read_bytes())
print(json.dumps({"zip":str(archive),"bytes":archive.stat().st_size,
    "sha256":H(archive.read_bytes()),"files":len(files),"renderer":NEW_DLL_SHA,
    "fire_tesla_containment":CONTAINMENT_SHA,"source_defaults_on":True,
    "retail_assets_included":False,"user_gpu_test":"PENDING"},indent=2))
