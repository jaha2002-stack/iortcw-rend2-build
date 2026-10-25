#!/usr/bin/env python3
"""Exact September Clean Production origin + complete accepted October feature port,
excluding the exact Fire/Tesla wall-light fix; preserve September color defaults."""
import sys,json,re,hashlib,shutil
from pathlib import Path
sep,oct,report=(Path(x).resolve() for x in sys.argv[1:4])
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sep_init=sep/"SP/code/rend2/tr_init.c"
assert H(sep_init)=="6ef13849d4d0209299c17cec4e6e08934761247c5222fe64d8ddb412a1ba721e",("WRONG_SEPT_BASE",H(sep_init))
assert H(sep/"SP/code/rend2/glsl/ssgi_fp.glsl")=="0cc59419316103983f0c054e92e613f131a9d8a3c74a914c27b93326e47ca1aa"
assert H(oct/"SP/code/rend2/glsl/ssgi_fp.glsl")=="8e36db4e28244d8b8bfe1ac57f5889c91cf7be032417ab6a52a1b841afa212dc"
old=sep_init.read_text()
pattern=r'\b([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*ri\.Cvar_Get\(\s*"([^"\n]+)"\s*,\s*"([^"\n]*)"'
sep_defaults={name:value for _,name,value in re.findall(pattern,old)}
ported=[]
for file in (oct/"SP").rglob("*"):
    if not file.is_file():continue
    rel=file.relative_to(oct/"SP")
    if any(v in rel.parts for v in ("build",".git")):continue
    dst=sep/"SP"/rel
    if not dst.exists() or H(dst)!=H(file):
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(file,dst)
        ported.append(str(rel))
assert len(ported)>=25,(len(ported),ported)
for required in ("code/rend2/tr_backend.c","code/rend2/tr_init.c","code/rend2/tr_scene.c","code/rend2/glsl/ssgi_fp.glsl","code/cgame/cg_ents.c"):
    assert required in ported,(required,"not ported")
init=sep/"SP/code/rend2/tr_init.c"
s=init.read_text()
changes={}
def set_default(name,value,reason):
    global s
    regex=re.compile(r'(\b'+re.escape(name)+r'\s*=\s*ri\.Cvar_Get\(\s*"'+re.escape(name)+r'"\s*,\s*)"([^"\n]*)"')
    matches=list(regex.finditer(s))
    if len(matches)!=1:raise RuntimeError("Missing or ambiguous CVar "+name+" "+str(len(matches)))
    prior=matches[0].group(2)
    if prior!=value:
        s=regex.sub(lambda m:m.group(1)+'"'+value+'"',s,count=1)
        changes[name]={"before":prior,"after":value,"why":reason}
# Source-level historical tonemapping and exposure are retained where registered.
for name in ("r_toneMap","r_autoExposure","r_forceAutoExposure","r_exposure",
             "r_gamma","r_intensity","r_mapOverBrightBits","r_overBrightBits",
             "r_ambientScale","r_directedScale"):
    if name in sep_defaults and re.search(r'\b'+re.escape(name)+r'\s*=\s*ri\.Cvar_Get',s):
        set_default(name,sep_defaults[name],"September color baseline")
# All historical systems remain available and enabled. LUT intensity is neutral
# because the default V03 0.80 was visually rejected (red appearance).
required={"r_dwLut":"1","r_dwLutStrength":"0.00","r_dwCas":"1",
 "r_dwCasStrength":"0.55","r_dwA2C":"1","r_dwTextureFidelity":"1",
 "r_dwMaterialFidelity":"1","r_bloom":"1","r_bloomMode":"2",
 "r_ssgi":"1","r_forceSun":"1","r_dlightMode":"2",
 "r_volumetricSun":"1","r_volumetricLocal":"1",
 "r_ext_framebuffer_multisample":"4","r_hdr":"1"}
for name,value in required.items():
    set_default(name,value,"accepted effect, LUT zero-strength avoids red grading")
init.write_text(s)
# The FireVol CVar is registered lazily in tr_backend.c rather than tr_init.c.
backend=sep/"SP/code/rend2/tr_backend.c"
back=backend.read_text()
vol_pattern=re.compile(r'(ri\.Cvar_Get\(\s*"r_volumetricFire"\s*,\s*)"([^"\n]*)"')
v=list(vol_pattern.finditer(back))
assert len(v)==1,("r_volumetricFire registered outside tr_init; expected one",len(v))
fire_old=v[0].group(2)
back=vol_pattern.sub(lambda m:m.group(1)+'"1"',back,count=1)
backend.write_text(back)
changes["r_volumetricFire"]={"before":fire_old,"after":"1","why":"enable historically required FireVol at source registration"}
for marker in ("DARKWOLF_CRYPT1_LIGHTMAP_SSGI_ISOLATION_V1","DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01","DARKWOLF_RC4_FORCE_SUN_CSM_REPRIME_V1"):
    assert any(marker in (sep/p).read_text() for p in ("SP/code/rend2/tr_backend.c","SP/code/rend2/tr_init.c","SP/code/rend2/tr_scene.c")),marker
for rel in ("SP/code/rend2/glsl/lightall_fp.glsl","SP/code/rend2/glsl/dlight_fp.glsl",
            "SP/code/rend2/tr_local.h","SP/code/rend2/tr_glsl.c","SP/code/cgame/cg_ents.c"):
    content=(sep/rel).read_text()
    for forbidden in ("DlightWorldVisibility","u_DlightWorldMap","DARKWOLF_REF_WORLD_OCCLUSION"):
        assert forbidden not in content,(rel,forbidden)
assert "!(r_lightmap && r_lightmap->integer)" in (sep/"SP/code/rend2/tr_backend.c").read_text()
report.parent.mkdir(parents=True,exist_ok=True)
data={"source_base":"September 18 2026 Clean Production run 35361762179 (Sep21 reference)",
"september_original_tree_verified":True,
"september_source_patch_sha256":"7041376f9dccc1be3a2172ef5834c73bb270cc76d768ad1ad115b0567c1077a0",
"september_upstream_sha":"438e7d413b5f7277187c35b032eb0ef9093ae778",
"ported_fourweek_source_files_count":len(ported),"ported_october_source_files":ported,
"Fire_Tesla_architectural_light_containment":"EXCLUDED_15_FILE_EXACT_REVERSE",
"SSGI_r_lightmap_1":"ISOLATED_ONLY_IN_DIAGNOSTIC_MODE",
"SSGI_in_game":"UNCHANGED_ON",
"September_color_defaults_plus_feature_defaults":changes,
"LUT_V03":"PRESENT_ENABLED_WITH_NEUTRAL_ZERO_STRENGTH_NOT_FORCED_RED",
"excluded_experiments":["PCF4","SSGI_Fire_Receiver_V04"],
"acceptance":"WIN64_COMPILATION_AND_PACKAGE_VALIDATION_PENDING"}
report.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
print("SEPTEMBER_BASE_ALL_OCTOBER_FEATURES_WITHOUT_FIRE_TESLA_PASS",len(ported),flush=True)
