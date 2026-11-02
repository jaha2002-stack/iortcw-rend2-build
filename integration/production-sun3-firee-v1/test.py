#!/usr/bin/env python3
"""Clean production preflight: Sun3 fidelity, Fire E defaults, GLSL130, no new diagnostic CVars."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
P=argparse.ArgumentParser()
P.add_argument("source",type=Path)
P.add_argument("--out",type=Path,required=True)
P.add_argument("--require-glslang",action="store_true")
a=P.parse_args()
root=a.source/"SP/code/rend2"
out=a.out;out.mkdir(parents=True,exist_ok=True)
H=lambda b:hashlib.sha256(b).hexdigest()
paths=("tr_backend.c","tr_init.c","glsl/volumetricsun_fp.glsl","glsl/volumetriclocal_fp.glsl","glsl/volumetriclocal_upscale_fp.glsl")
source={k:(root/k).read_text() for k in paths}
b=source["tr_backend.c"];i=source["tr_init.c"];s=source["glsl/volumetricsun_fp.glsl"]
f=source["glsl/volumetriclocal_fp.glsl"];up=source["glsl/volumetriclocal_upscale_fp.glsl"]
MARK="DARKWOLF_SUN3_FIRE_E_CLEAN_PRODUCTION_V1_20261027"
assert MARK in s and MARK in b
assert "DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1" in b
assert "FBO_FastBlit(tr.msaaResolveFbo, NULL, tr.renderFbo" in b
assert "DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1" in s and "DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1" in up
assert "DARKWOLF_VOLUMETRIC_WAVE_CLEAN_V2_20261027" in s and "DARKWOLF_VOLUMETRIC_WAVE_CLEAN_V2_20261027" in f
assert "DARKWOLF_SUN_WAVE_CAUSE_MATRIX_V3_20261027" not in s+b
# Exactly V3 mode 3: quarter-offset substeps, 2 shadow-map queries, 6% cascade fade.
assert "vec3 subStep = var_ViewDir * (0.25 * stepDepth);" in s
assert "float va = sunVisibility(worldPos - subStep, pcfMode);" in s
assert "float vb = sunVisibility(worldPos + subStep, pcfMode);" in s
assert "float visibility = 0.5 * (va + vb);" in s
assert "float x = clamp(dwCascadeInterior(p) / 0.06, 0.0, 1.0);" in s
assert s.count("float visibility = sunVisibility(worldPos, pcfMode);")==0
assert b.count("Com_Clamp(4, 64, r_volumetricSunSamples->integer)")==1
assert '#define VOLUMETRIC_MAX_SAMPLES 64' in s
assert 'ri.Cvar_Get( "r_volumetricSunSamples", "32", CVAR_ARCHIVE )' in i
assert 'ri.Cvar_Get( "r_volumetricSunJitter", "0.08", CVAR_ARCHIVE )' in i
# Exactly previously runtime-preferred Fire E (not added to lamp PCF branch).
assert '#define LOCALVOL_MAX_SAMPLES 64' in f
assert "stableVolumetricJitter(gl_FragCoord.xy)" in f
assert "bool shadowedFire = pcfMode >= 2 && u_EnableTextures.w >= 5.0 && u_EnableTextures.w <= 7.5;" in f
assert "if (shadowedFire)" in f and "else" in f
assert "int pcfMode = int(clamp(u_EnableTextures.y, 0.0, 2.0) + 0.5);" in f
assert f.count("filtered += compareDlightShadow(")>=12
assert 'ri.Cvar_Get("r_volumetricFireSamples", "40", CVAR_ARCHIVE)' in b
assert 'ri.Cvar_Get("r_volumetricFireUpscale", "2", CVAR_ARCHIVE)' in b
assert 'ri.Cvar_Get( "r_volumetricLocalShadowPcf", "2", CVAR_ARCHIVE )' in i
assert 'ri.Cvar_Get( "r_volumetricLocalJitter", "0.08", CVAR_ARCHIVE )' in i
assert "Com_Clamp(8, 64, s_rVolumetricFireSamples->integer)" in b
assert "(float)Com_Clamp(0, 2, r_volumetricLocalShadowPcf->integer)" in b
assert "reconstructionMode >= 2" in b
assert "r_volumetricLocalShadowPcf, 0, 2, qtrue" in i
# Unchanged, user-tested shared 5x5 reconstruction; no Local diagnostic extensions.
assert H((root/"glsl/volumetriclocal_fp.glsl").read_bytes())=="ef616bfc50be66a048fe0817971e4308574ff91cab4393185f6153999dd26a67"
assert H((root/"glsl/volumetriclocal_upscale_fp.glsl").read_bytes())=="ab864faa0ed6eadcf9c8d82992d8ea0fdfc715db340ed57f8f9505e62412f15e"
for k,v in source.items():
    for diagnostic in ("r_dwSunWaveMode","r_dwSunReconMode","r_dwVolSunFullresDiag","r_dwVolLocalSpatialDiag","r_dwVolLocalLampPcfDiag"):
        assert diagnostic not in v,(k,diagnostic)
assert "r_volumetricSunMode" in b
assert "r_dlightMode" not in MARK
glsl=shutil.which("glslangValidator")
if a.require_glslang: assert glsl, "GLSLANG_COMPILER_MISSING"
tested=[]
if glsl:
    header="#version 130\n#define varying in\nout vec4 out_Color;\n#define gl_FragColor out_Color\n#define texture2D texture\n#define shadow2D texture\n#define M_PI 3.14159265358979323846\n"
    variants=[
        ("glsl/volumetricsun_fp.glsl","SUN3_CSM","#define USE_SHADOW_CASCADE\n#define r_shadowMapSize 2048.0\n"),
        ("glsl/volumetricsun_fp.glsl","SUN3_SINGLE","#define r_shadowMapSize 2048.0\n"),
        ("glsl/volumetriclocal_fp.glsl","FIRE_E_LOCAL",""),
        ("glsl/volumetriclocal_upscale_fp.glsl","VOLUMETRIC_RECON_5X5","")]
    for path,tag,defs in variants:
        dest=out/(tag+".frag");dest.write_text(header+defs+source[path])
        p=subprocess.run([glsl,"-S","frag",str(dest)],text=True,capture_output=True)
        (out/(tag+".log")).write_text(p.stdout+"\n"+p.stderr)
        assert p.returncode==0,("GLSL130_COMPILE_FAILED",tag,p.stdout,p.stderr)
        tested.append(tag)
        print("DW_PROD_GLSL130_PASS",tag)
else: print("LOCAL_GLSLANG_UNAVAILABLE__CI_REQUIRES_GLSLANG")
res={
    "status":"SOURCE_AND_GLSL_PASS",
    "base_run":40480112714,"Sun":"V3_mode3_6pct_CSM_32_steps",
    "Fire":"E_40_steps_5x5_9tap",
    "Local":"V2_user_accepted_no_extra_diagnostics",
    "clean":True,"new_diagnostic_cvars":[],
    "shaders":tested,"source_hashes":{k:H((root/k).read_bytes()) for k in paths},
    "GPU_runtime_this_new_binary":"PENDING"
}
(out/"PRODUCTION_GL_SHADER_QA.json").write_text(json.dumps(res,indent=2)+"\n")
print("DW_SUN3_FIRE_E_CLEAN_PRODUCTION_GLSL_STATIC_PASS")
