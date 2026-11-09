#!/usr/bin/env python3
from pathlib import Path
import argparse, json, math

ap=argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("--out")
args=ap.parse_args()

sp=Path(args.source)/"SP"
root=sp/"code/rend2"

def txt(rel):
    return (root/rel).read_text()

local=txt("tr_local.h")
glsl=txt("tr_glsl.c")
frag=txt("glsl/lightall_fp.glsl")
pref=txt("glsl/iblprefilter_fp.glsl")
brdf=txt("glsl/iblbrdflut_fp.glsl")
bsp=txt("tr_bsp.c")
backend=txt("tr_backend.c")
shade=txt("tr_shade.c")
fbo=txt("tr_fbo.c")
fboh=txt("tr_fbo.h")
image=txt("tr_image.c")
cmds=txt("tr_cmds.c")
make=(sp/"Makefile").read_text()

checks={
    "base_v42_still_present": all(x in frag for x in (
        "USE_PBR2_BSP_RELIGHT_V4","BSP diffuse-IBL relight V4.2","dwEnvRatio"
    )),
    "v31_capability_guard": all(x in glsl for x in (
        "USE_PBR2_IBL_V31","glRefConfig.framebufferObject","glRefConfig.textureFloat","glConfig.numTextureUnits >= 8"
    )),
    "legacy_v3_fallback_preserved": "#define USE_PBR2_IBL_V3" in glsl and "DW_EnvironmentBRDFApprox" in frag,
    "brdf_sampler_slot": "TB_BRDFLUT     = 7" in local and "NUM_TEXTURE_BUNDLES = 8" in local,
    "brdf_uniform_registered": 'u_BRDFLut' in glsl and "UNIFORM_BRDFLUT" in local,
    "separate_prefilter_resource": "image_t *prefilteredImage" in local and "image_t *image;" in local,
    "float_prefilter_target": "GL_RGBA16F_ARB" in bsp and "*pbrV31Prefilter" in bsp,
    "float_lut_target": "*pbrBrdfLut" in image and "GL_RGBA16F_ARB" in image,
    "mip_level_fbo_attachment": "FBO_AttachImageLevel" in fbo and "mipLevel" in fboh,
    "backend_command": "RC_PBR_IBL_BUILD" in local and "RB_PbrIblBuild" in backend and "R_AddPbrIblBuildCmd" in cmds,
    "build_before_first_view": "R_PreparePbrV31Cubemaps();" in bsp and "R_IssuePendingRenderCommands();" in bsp,
    "source_destination_no_feedback": "cubemap->image, TB_CUBEMAP" in backend and "cubemap->prefilteredImage" in backend,
    "source_mip_anti_aliasing": "saSample" in pref and "saTexel" in pref and "sourceLod" in pref,
    "ggx_importance_sampling": "DW_ImportanceSampleGGX" in pref and "DW_DistributionGGX" in pref,
    "prefilter_linearizes_source": "DW_SRGBToLinear(c)" in pref,
    "lut_full_integration": all(x in brdf for x in (
        "DW_IntegrateBRDF","DW_GeometrySmith","GVis","A +=","B +="
    )),
    "lut_512_samples": "DW_MAX_BRDF_SAMPLES 512" in brdf and "512.0f" in backend,
    "prefilter_256_samples": "DW_MAX_PREFILTER_SAMPLES 256" in pref and "256.0f" in backend,
    "split_sum_runtime": "specular.rgb * dwBrdf.x + vec3(dwBrdf.y)" in frag,
    "linear_prefilter_runtime": "V3.1 prefiltered cubemap is RGBA16F and already stores linear radiance" in frag,
    "roughness_to_convolved_mip": "ROUGHNESS_MIPS * roughness" in frag,
    "shade_binds_prefilter": "environmentImage = cubemap->prefilteredImage" in shade,
    "shade_binds_lut": "GL_BindToTMU(tr.pbrBrdfLutImage, TB_BRDFLUT)" in shade,
    "legacy_modes_keep_raw_cube": "r_pbr->integer >= 3" in shade and "environmentImage = cubemap->image" in shade,
    "shader_fallbacks_embedded": all(x in make for x in (
        "iblprefilter_fp.o","iblprefilter_vp.o","iblbrdflut_fp.o","iblbrdflut_vp.o"
    )),
}

# Numerical sanity for the same split-sum equations used by the shader.
# This is not an image golden test; it catches sign/normalization mistakes.
def r2(i):
    return ((0.5 + (i+0.5)*0.7548776662466927)%1.0,
            (0.5 + (i+0.5)*0.5698402909980532)%1.0)

def norm(v):
    l=math.sqrt(sum(x*x for x in v))
    return tuple(x/l for x in v)

def dot(a,b): return sum(x*y for x,y in zip(a,b))

def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def importance(xi, N, rough):
    a=max(rough*rough,0.0025); a2=a*a
    phi=2*math.pi*xi[0]
    ct=math.sqrt((1-xi[1])/max(1+(a2-1)*xi[1],1e-7))
    st=math.sqrt(max(1-ct*ct,0))
    ht=(math.cos(phi)*st,math.sin(phi)*st,ct)
    up=(0,0,1) if abs(N[2])<0.999 else (1,0,0)
    t=norm(cross(up,N)); b=cross(N,t)
    return norm(tuple(t[k]*ht[0]+b[k]*ht[1]+N[k]*ht[2] for k in range(3)))

def geom_schlick(nv, rough):
    k=(rough*rough)*0.5
    return nv/max(nv*(1-k)+k,1e-6)

def integrate(nv, rough, samples=512):
    V=(math.sqrt(max(1-nv*nv,0)),0,nv); N=(0,0,1)
    A=B=0.0
    for i in range(samples):
        H=importance(r2(i),N,rough)
        vh=dot(V,H)
        L=norm(tuple(2*vh*H[k]-V[k] for k in range(3)))
        nl=max(L[2],0); nh=max(H[2],0); vh=max(vh,0)
        if nl>0:
            G=geom_schlick(nv,rough)*geom_schlick(nl,rough)
            gv=(G*vh)/max(nh*nv,1e-6)
            fc=(1-vh)**5
            A+=(1-fc)*gv; B+=fc*gv
    return A/samples,B/samples

a1,b1=integrate(0.9,0.1)
a2,b2=integrate(0.5,0.8)
checks["numeric_lut_bounded"] = all(math.isfinite(x) and 0.0 <= x <= 1.2 for x in (a1,b1,a2,b2))
checks["smooth_surface_high_A"] = a1 > 0.75
checks["rough_surface_finite_response"] = a2 > 0.2 and b2 >= 0.0

failed=[k for k,v in checks.items() if not v]
if failed:
    raise SystemExit("PBR_V31_IBL_TEST_FAIL: "+", ".join(failed))

print("DARKWOLF_PBR_V31_TRUE_IBL_STATIC_PASS",len(checks))
print("BRDF_SANITY",{"NoV0.9_R0.1":[a1,b1],"NoV0.5_R0.8":[a2,b2]})
if args.out:
    p=Path(args.out); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps({"checks":checks,"brdf_sanity":{
        "NoV0.9_R0.1":[a1,b1],"NoV0.5_R0.8":[a2,b2]}},indent=2)+"\n")
