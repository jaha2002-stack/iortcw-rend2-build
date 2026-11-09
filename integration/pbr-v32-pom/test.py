#!/usr/bin/env python3
from pathlib import Path
import argparse, json, math

ap=argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("--out")
args=ap.parse_args()
root=Path(args.source)/"SP/code/rend2"

def t(rel): return (root/rel).read_text()

frag=t("glsl/lightall_fp.glsl")
glsl=t("tr_glsl.c")
init=t("tr_init.c")
local=t("tr_local.h")

checks={
 "v31_ggx_preserved": "USE_PBR2_IBL_V31" in frag and "u_BRDFLut" in frag,
 "v42_relit_preserved": "BSP diffuse-IBL relight V4.2" in frag,
 "v32_define_is_pbr3_only": "r_pbr->integer >= 3" in glsl and "USE_PBR_PHYSICAL_RELIEF_V32" in glsl,
 "legacy_parallax_retained": "RayIntersectDisplaceMap" in frag and "#else\n\tvec3 offsetDir = E * tangentToWorld;" in frag,
 "adaptive_layers": all(x in frag for x in ("DW_POM_MIN_LAYERS","DW_POM_MAX_LAYERS","layerCountF","DW_POM_LOOP_CAP 64")),
 "binary_refinement": "DW_POM_REFINE_STEPS" in frag and "DW_POM_REFINE_CAP 8" in frag,
 "secant_finish": "fLow / denom" in frag and "mix(lowUv, highUv, w)" in frag,
 "view_z_safety": "max(abs(viewTS.z), 0.12)" in frag,
 "uv_offset_clamp": "DW_ClampPomVector" in frag and "DW_POM_MAX_OFFSET" in frag,
 "per_material_depth": "u_NormalScale.a * DW_POM_DEPTH_SCALE" in frag,
 "optional_self_shadow": "DW_PomSelfShadow" in frag and "USE_PARALLAXMAP_SHADOWS" in frag,
 "cvars_registered": all(x in init for x in (
     'r_pomMinLayers = ri.Cvar_Get', 'r_pomMaxLayers = ri.Cvar_Get',
     'r_pomRefineSteps = ri.Cvar_Get', 'r_pomMaxOffset = ri.Cvar_Get',
     'r_pomDepthScale = ri.Cvar_Get', 'r_pomShadowStrength = ri.Cvar_Get')),
 "cvars_declared": all(x in local for x in (
     "r_pomMinLayers","r_pomMaxLayers","r_pomRefineSteps",
     "r_pomMaxOffset","r_pomDepthScale","r_pomShadowStrength")),
 "safe_compile_clamps": all(x in glsl for x in (
     "CLAMP(r_pomMinLayers->integer, 8, 48)",
     "CLAMP(r_pomMaxLayers->integer, 16, 64)",
     "CLAMP(r_pomRefineSteps->integer, 2, 8)",
     "CLAMP(r_pomMaxOffset->value, 0.01f, 0.20f)",
     "CLAMP(r_pomDepthScale->value, 0.25f, 2.0f)",
     "CLAMP(r_pomShadowStrength->value, 0.0f, 1.0f)")),
}

# CPU reference of the POM crossing logic on a 1-D synthetic masonry profile.
# Depth is 1-height, matching SampleDepth().
def height(u):
    u=u%1.0
    # broad stone faces with deep mortar seams around 0.25, 0.50, 0.75
    seam=min(abs(u-0.25),abs(u-0.50),abs(u-0.75),abs(u),abs(u-1.0))
    if seam < 0.025:
        return 0.12 + seam/0.025*0.12
    # low-frequency stone crown, no micro noise
    return 0.72 + 0.10*math.cos((u%0.25)/0.25*2*math.pi)

def depth(u): return 1.0-height(u)

def pom(base_u, view_x, view_z, depth_scale=0.03, min_layers=20, max_layers=56, refine=5, max_offset=0.08):
    vz=max(abs(view_z),0.12)
    nov=max(0,min(1,vz))
    layers=round(max_layers+(min_layers-max_layers)*nov)
    layers=max(min_layers,min(max_layers,layers))
    total=max(-max_offset,min(max_offset,(-view_x/vz)*depth_scale))
    du=total/layers
    dd=1.0/layers
    cu=base_u; pu=base_u; cd=0.0; pd=0.0; md=depth(cu)
    for i in range(64):
        if i>=layers or cd>=md: break
        pu,pd=cu,cd
        cu+=du; cd+=dd; md=depth(cu)
    if cd<=1e-9: return base_u,0.0
    lo_u,hi_u=pu,cu; lo_d,hi_d=pd,cd
    for i in range(refine):
        mu=(lo_u+hi_u)*0.5; mdp=(lo_d+hi_d)*0.5
        if mdp>=depth(mu):
            hi_u,hi_d=mu,mdp
        else:
            lo_u,lo_d=mu,mdp
    flo=depth(lo_u)-lo_d; fhi=depth(hi_u)-hi_d
    den=flo-fhi
    w=max(0,min(1,flo/den)) if abs(den)>1e-9 else 0.5
    return lo_u*(1-w)+hi_u*w, lo_d*(1-w)+hi_d*w

u_front,d_front=pom(0.31,0.05,0.998)
u_mid,d_mid=pom(0.31,0.55,0.835)
u_graz,d_graz=pom(0.31,0.90,0.435)

checks["numeric_front_nearly_stable"] = abs(u_front-0.31) < 0.004
checks["numeric_grazing_displacement_increases"] = abs(u_graz-0.31) > abs(u_mid-0.31) > abs(u_front-0.31)
checks["numeric_offset_respects_clamp"] = abs(u_graz-0.31) <= 0.080001
checks["numeric_hit_depth_bounded"] = all(0.0 <= x <= 1.0 for x in (d_front,d_mid,d_graz))

failed=[k for k,v in checks.items() if not v]
if failed:
    raise SystemExit("PBR_V32_POM_TEST_FAIL: "+", ".join(failed))

out={
 "checks":checks,
 "numeric":{
   "front":{"uv":u_front,"hitDepth":d_front},
   "mid":{"uv":u_mid,"hitDepth":d_mid},
   "grazing":{"uv":u_graz,"hitDepth":d_graz}
 }
}
print("DARKWOLF_PBR_V32_PHYSICAL_RELIEF_STATIC_PASS",len(checks))
print(json.dumps(out["numeric"],indent=2))
if args.out:
    p=Path(args.out); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2)+"\n")
