#!/usr/bin/env python3
"""Clean Sun3 + Fire E production over EXACT #40480112714 Sky Single-Sample source.

Preserves the user-tested Wave V2 GLSL base and hard-wires V3 Sun mode 3.
No new diagnostic CVars, no telemetry, no CSM producer changes.
"""
import argparse,hashlib,importlib.util,json
from pathlib import Path

MARK="DARKWOLF_SUN3_FIRE_E_CLEAN_PRODUCTION_V1_20261027"
BASE_RUN=40480112714
PRE={
    "tr_backend.c":"505ef716a0e316a99f00f0ce8d2e4e81ecef650424bfd22a537227ffbfbb37ba",
    "tr_init.c":"166dce445e85d5bf93d2b7779656ac201d78fa98b977c95ad6cfe5bd50098fff",
    "glsl/volumetricsun_fp.glsl":"dfbb9f92db919fbb54de80eb19a0f1e23a22c8df7742119aafcf638ba4e0e74d",
    "glsl/volumetriclocal_fp.glsl":"a39bd6eaa3dd81e2a30f75bb9d90343cc0d057ce48c58bea8f7fadcdf60b28a6",
    "glsl/volumetriclocal_upscale_fp.glsl":"dc85c8fa6133ea484236a230950c10f00a2c4096c678c93e5b8c36091429ff8e"}
WAVE_USER_TESTED={
    "tr_backend.c":"0cfcad4ad18882691f16749697d09a48e832b9344de4e58a11e36c3b7efb405e",
    "tr_init.c":"fa48aa1bdfe9954a5232d346b9559be2417b685318345c0641d4b11d68e883a8",
    "glsl/volumetricsun_fp.glsl":"8e22ade3bba934b471b270fd5db3e6066e500acb47bc1ea03588abe1bcd780ab",
    "glsl/volumetriclocal_fp.glsl":"ef616bfc50be66a048fe0817971e4308574ff91cab4393185f6153999dd26a67",
    "glsl/volumetriclocal_upscale_fp.glsl":"ab864faa0ed6eadcf9c8d82992d8ea0fdfc715db340ed57f8f9505e62412f15e"}
def H(s): return hashlib.sha256(s.encode()).hexdigest()
def one(s,old,new,what):
    n=s.count(old)
    assert n==1,(what,"unique anchor expected",n)
    return s.replace(old,new,1)

def apply(root):
    p=root/"SP/code/rend2"
    before={k:(p/k).read_text() for k in PRE}
    assert {k:H(v) for k,v in before.items()}==PRE,("WRONG_SKY_404801_SOURCE",{k:H(v) for k,v in before.items()})
    assert "DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1" in before["tr_backend.c"]
    assert "DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1" in before["glsl/volumetricsun_fp.glsl"]
    assert "r_dwSunWaveMode" not in before["tr_backend.c"]
    assert "r_dwVol" not in before["tr_backend.c"]
    # Reproduce the exact 5-file shader baseline already played by the user.
    donor=Path(__file__).resolve().parents[1]/"volumetric-wave-clean-v2"/"apply.py"
    assert donor.is_file(),("MISSING_USER_TESTED_WAVE_V2_DONOR",str(donor))
    spec=importlib.util.spec_from_file_location("dw_wave_v2_verified_donor",donor)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.apply(root)
    wave={k:(p/k).read_text() for k in PRE}
    assert {k:H(v) for k,v in wave.items()}==WAVE_USER_TESTED,"DONOR_SOURCE_NOT_IDENTICAL_TO_USER_TESTED_V2"

    sun=wave["glsl/volumetricsun_fp.glsl"]
    # V3, mode=3: two shadow visibility queries at +/- one quarter of a ray step.
    # Keep the original 6% cascade fade, identical 32-sample setting, ray jitter,
    # compositing order, and quarter-resolution upscale. No debug mode selector.
    sun=one(sun,
        "        float visibility = sunVisibility(worldPos, pcfMode);\n"
        "        integrated += visibility * transmittance * density * worldStep;",
        "        // "+MARK+": permanent V3 mode-3 dual visibility, original 6% CSM blend.\n"
        "        vec3 subStep = var_ViewDir * (0.25 * stepDepth);\n"
        "        float va = sunVisibility(worldPos - subStep, pcfMode);\n"
        "        float vb = sunVisibility(worldPos + subStep, pcfMode);\n"
        "        float visibility = 0.5 * (va + vb);\n"
        "        integrated += visibility * transmittance * density * worldStep;",
        "SUN3_DUAL_VISIBILITY")
    assert sun.count("sunVisibility(worldPos - subStep, pcfMode)")==1
    assert sun.count("sunVisibility(worldPos + subStep, pcfMode)")==1
    assert "float x = clamp(dwCascadeInterior(p) / 0.06" in sun
    assert "r_dwSunWaveMode" not in sun

    back=wave["tr_backend.c"]
    back=one(back,'ri.Cvar_Get("r_volumetricFireSamples", "24", CVAR_ARCHIVE)',
             'ri.Cvar_Get("r_volumetricFireSamples", "40", CVAR_ARCHIVE) /* '+MARK+' */',
             "FIRE_E_40_DEFAULT")
    back=one(back,'ri.Cvar_Get("r_volumetricFireUpscale", "1", CVAR_ARCHIVE)',
             'ri.Cvar_Get("r_volumetricFireUpscale", "2", CVAR_ARCHIVE)',
             "FIRE_E_DEPTH5X5_DEFAULT")
    # Keep V2's selective fire 9-tap branch; Local lamps remain on the old 5-tap branch.
    assert "(float)Com_Clamp(0, 2, r_volumetricLocalShadowPcf->integer)" in back
    assert "reconstructionMode >= 2" in back
    assert "DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1" in back
    assert "r_dwSunWaveMode" not in back

    init=wave["tr_init.c"]
    init=one(init,'ri.Cvar_Get( "r_volumetricLocalShadowPcf", "1", CVAR_ARCHIVE )',
             'ri.Cvar_Get( "r_volumetricLocalShadowPcf", "2", CVAR_ARCHIVE )',
             "FIRE_E_SHADOW_PCF_DEFAULT")
    init=one(init,'ri.Cvar_Get( "r_volumetricLocalJitter", "0.10", CVAR_ARCHIVE )',
             'ri.Cvar_Get( "r_volumetricLocalJitter", "0.08", CVAR_ARCHIVE )',
             "LOCAL_JITTER_TESTED_FIRE_E")
    init=one(init,'ri.Cvar_Get( "r_volumetricSunJitter", "0.10", CVAR_ARCHIVE )',
             'ri.Cvar_Get( "r_volumetricSunJitter", "0.08", CVAR_ARCHIVE )',
             "SUN_JITTER_TESTED_V3_MODE3")
    fire=wave["glsl/volumetriclocal_fp.glsl"]
    assert "bool shadowedFire = pcfMode >= 2 && u_EnableTextures.w >= 5.0 && u_EnableTextures.w <= 7.5;" in fire
    assert "#define LOCALVOL_MAX_SAMPLES 64" in fire
    assert "int pcfMode = int(clamp(u_EnableTextures.y, 0.0, 2.0) + 0.5);" in fire
    assert fire.count("filtered += compareDlightShadow(")>=12

    after={"tr_backend.c":back,"tr_init.c":init,
           "glsl/volumetricsun_fp.glsl":sun,
           "glsl/volumetriclocal_fp.glsl":fire,
           "glsl/volumetriclocal_upscale_fp.glsl":wave["glsl/volumetriclocal_upscale_fp.glsl"]}
    assert set(after)==set(before)
    assert all(after[k]!=before[k] for k in after)
    for rel,v in after.items(): (p/rel).write_text(v)
    assert "r_dwSun" not in back+sun and "r_dwVol" not in back+sun+fire
    return {
       "marker":MARK, "exact_binary_base_run":BASE_RUN,
       "user_tested_fire_run":40487188767,"user_tested_sun_v3_run":40504661395,
       "Sun":"V3_MODE_3_DUAL_VISIBILITY_6_PERCENT_CSM",
       "Fire":"E_40_RAY_STEPS_DEPTH_5X5_9_TAP",
       "Local":"user_tested_V2_shader_and_upscale_without_Local_specific_diagnostic_modes",
       "modified_source_files":["SP/code/rend2/"+k for k in PRE],
       "sha256_before":PRE,
       "sha256_verified_tested_wave_v2":WAVE_USER_TESTED,
       "sha256_after":{k:H(v) for k,v in after.items()},
       "new_diagnostic_cvars":[],"telemetry":False,
       "default_cvars":{"r_volumetricSunSamples":"32","r_volumetricSunJitter":"0.08",
          "r_volumetricFireSamples":"40","r_volumetricFireUpscale":"2",
          "r_volumetricLocalShadowPcf":"2","r_volumetricLocalJitter":"0.08"},
       "gpu_runtime_this_new_binary":"NOT_YET_TESTED"}
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("source",type=Path);ap.add_argument("--proof",type=Path)
    args=ap.parse_args();v=apply(args.source)
    if args.proof:
        args.proof.parent.mkdir(parents=True,exist_ok=True)
        args.proof.write_text(json.dumps(v,indent=2,ensure_ascii=False)+"\n")
    print("DW_SUN3_FIRE_E_EXACT_CLEAN_PRODUCTION_SOURCE_PASS")
