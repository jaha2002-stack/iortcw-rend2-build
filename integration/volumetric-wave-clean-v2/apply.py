#!/usr/bin/env python3
"""Source-gated quality fix atop the exact accepted 40294211216 shader reconstruction.
Do not modify CSM producers, Tesla, materials, SSGI or scene shadow policy.
"""
import argparse
import hashlib
import json
from pathlib import Path

MARK = "DARKWOLF_VOLUMETRIC_WAVE_CLEAN_V2_20261027"
FILES = ("glsl/volumetricsun_fp.glsl", "glsl/volumetriclocal_fp.glsl",
         "glsl/volumetriclocal_upscale_fp.glsl", "tr_backend.c", "tr_init.c")

def change(src, old, new, name):
    count = src.count(old)
    if count != 1:
        raise AssertionError("%s expected one anchor, got %d" % (name, count))
    return src.replace(old, new, 1)

def apply(root):
    parent = root / "SP/code/rend2"
    before = {f: (parent / f).read_text() for f in FILES}
    # Exact production source AFTER 40480112714 Universal Portal-Sky patch.
    backend_sha = hashlib.sha256(before["tr_backend.c"].encode()).hexdigest()
    assert backend_sha == "505ef716a0e316a99f00f0ce8d2e4e81ecef650424bfd22a537227ffbfbb37ba", ("WRONG_404801_SKY_BASE", backend_sha)
    assert "DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1" in before["tr_backend.c"]
    assert "DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1" in before["glsl/volumetricsun_fp.glsl"]
    assert "DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1" in before["glsl/volumetriclocal_upscale_fp.glsl"]
    for f, data in before.items():
        if MARK in data:
            raise AssertionError("%s already patched" % f)
    sun = before[FILES[0]]
    assert "DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1" in sun
    sun = change(sun, "#define VOLUMETRIC_MAX_SAMPLES 32",
                 "#define VOLUMETRIC_MAX_SAMPLES 64 // " + MARK, "sun GLSL ceiling")
    old_rng = """float interleavedGradientNoise(vec2 p)
{
    return fract(52.9829189 * fract(0.06711056 * p.x + 0.00583715 * p.y));
}"""
    new_rng = """// %s: decorrelated, per-pixel, stable jitter for ray steps.
float stableVolumetricJitter(vec2 p)
{
    vec2 i = floor(p);
    return fract(sin(dot(i, vec2(127.1, 311.7))) * 43758.5453123);
}""" % MARK
    sun = change(sun, old_rng, new_rng, "sun lattice jitter")
    sun = change(sun, "interleavedGradientNoise(gl_FragCoord.xy)",
                 "stableVolumetricJitter(gl_FragCoord.xy)", "sun noise call")

    local = before[FILES[1]]
    local = change(local, "#define LOCALVOL_MAX_SAMPLES 48 // DARKWOLF_LOCAL_VOLUMETRIC_SPOTLIGHT_QUALITY_V0_4: 48 only for spotlight quality ceiling",
                   "#define LOCALVOL_MAX_SAMPLES 64 // " + MARK + " fire ceiling; spotlight still capped at 48", "local GLSL ceiling")
    local = change(local, old_rng, new_rng, "local lattice jitter")
    local = change(local, "interleavedGradientNoise(gl_FragCoord.xy)",
                   "stableVolumetricJitter(gl_FragCoord.xy)", "local noise call")
    local = change(local, "int pcfMode = int(clamp(u_EnableTextures.y, 0.0, 1.0) + 0.5);",
                   "int pcfMode = int(clamp(u_EnableTextures.y, 0.0, 2.0) + 0.5);", "fire PCF quality mode")
    a = local.index("float localDlightVisibility(vec3 fragmentToLight, float currentDepth, int pcfMode)\n{")
    b = local.index("\nbool raySphereSegment(", a)
    block = local[a:b]
    assert "compareDlightShadow" in block and "filtered += compareDlightShadow" in block
    replacement = """// %s: 9-tap fire-only PCF; leave original 5-tap PCF for lamps.
float localDlightVisibility(vec3 fragmentToLight, float currentDepth, int pcfMode)
{
    if (u_DlightShadowParams.x < 0.5)
        return 1.0;
    vec3 dir = normalize(fragmentToLight);
    float bias = max(u_DlightShadowParams.y, 0.0);
    float filtered;
    bool shadowedFire = pcfMode >= 2 && u_EnableTextures.w >= 5.0 && u_EnableTextures.w <= 7.5;
    if (pcfMode <= 0)
        filtered = compareDlightShadow(dir, currentDepth, bias);
    else
    {
        vec3 helper = abs(dir.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(0.0, 1.0, 0.0);
        vec3 tangent = normalize(cross(helper, dir));
        vec3 bitangent = cross(dir, tangent);
        float radius = max(u_DlightShadowParams.z, 0.00001);
        if (shadowedFire)
        {
            float r = radius * 1.25, d = r * 0.70710678;
            filtered = compareDlightShadow(dir, currentDepth, bias) * 0.20;
            filtered += compareDlightShadow(dir + tangent * r, currentDepth, bias) * 0.10;
            filtered += compareDlightShadow(dir - tangent * r, currentDepth, bias) * 0.10;
            filtered += compareDlightShadow(dir + bitangent * r, currentDepth, bias) * 0.10;
            filtered += compareDlightShadow(dir - bitangent * r, currentDepth, bias) * 0.10;
            filtered += compareDlightShadow(dir + (tangent + bitangent) * d, currentDepth, bias) * 0.10;
            filtered += compareDlightShadow(dir + (tangent - bitangent) * d, currentDepth, bias) * 0.10;
            filtered += compareDlightShadow(dir + (-tangent + bitangent) * d, currentDepth, bias) * 0.10;
            filtered += compareDlightShadow(dir - (tangent + bitangent) * d, currentDepth, bias) * 0.10;
        }
        else
        {
            filtered = compareDlightShadow(dir, currentDepth, bias) * 0.50;
            filtered += compareDlightShadow(dir + tangent * radius, currentDepth, bias) * 0.125;
            filtered += compareDlightShadow(dir - tangent * radius, currentDepth, bias) * 0.125;
            filtered += compareDlightShadow(dir + bitangent * radius, currentDepth, bias) * 0.125;
            filtered += compareDlightShadow(dir - bitangent * radius, currentDepth, bias) * 0.125;
        }
    }
    return mix(1.0, clamp(filtered, 0.0, 1.0), clamp(u_DlightShadowParams.w, 0.0, 1.0));
}
""" % MARK
    local = local[:a] + replacement + local[b:]

    up = before[FILES[2]]
    assert "RC4_QUALITY_VOLUMETRIC_RECONSTRUCTION_V1" in up
    up = change(up, """  if (blend == 0.0)
  {
   return max(cM,vec3(0.0));
  }
""", "  // " + MARK + ": smooth interiors as well as edge pixels.\n", "upscale early exit")
    up = change(up, "vec3 antiNoise=mix(aa,neighborhood,0.18*lumaEdge);",
                "vec3 antiNoise=mix(aa,neighborhood,0.28+0.22*lumaEdge); // " + MARK, "upscale mix")
    up = change(up, "return max(mix(cM,antiNoise,blend),vec3(0.0));",
                "return max(mix(cM,antiNoise,max(blend,0.32)),vec3(0.0));", "upscale floor")
    assert "if(max(max(rel.x,rel.y),max(rel.z,rel.w))<0.06)" in up

    back = before[FILES[3]]
    back = change(back, "Com_Clamp(4, 32, r_volumetricSunSamples->integer)",
                  "Com_Clamp(4, 64, r_volumetricSunSamples->integer) /*"+MARK+"*/", "backend sun clamp")
    back = change(back, "Com_Clamp(8, 32, s_rVolumetricFireSamples->integer)",
                  "Com_Clamp(8, 64, s_rVolumetricFireSamples->integer)", "backend fire clamp")
    back = change(back, "(float)Com_Clamp(0, 1, r_volumetricLocalShadowPcf->integer)",
                  "(float)Com_Clamp(0, 2, r_volumetricLocalShadowPcf->integer)", "fire PCF selector")
    st = back.index("if (tr.volumetricFullresFbo && tr.volumetricLocalUpscaleShader.program &&\n\t\t\t((mode >= 1 && mode <= 3) || reconstructionMode > 0))")
    en = back.index("\n\t\telse if (reconstructionMode == 3", st)
    section = back[st:en]
    section = change(section, "VectorSet4(upscaleParams, 0.0f, 4.0f, 1.0f, 0.0f);",
                     """// %s: honor the Fire upscale 2/3 depth-aware 5x5 choice.
            VectorSet4(upscaleParams,
                (mode >= 5 && mode <= 8 && reconstructionMode >= 2) ?
                    Com_Clamp(0.0f, 64.0f, reconstructionDepthReject) : 0.0f,
                (mode >= 5 && mode <= 8 && reconstructionMode >= 2) ? 2.0f : 4.0f,
                1.0f, 0.0f);""" % MARK, "fire full-res upscale")
    back = back[:st] + section + back[en:]

    init = before[FILES[4]]
    init = change(init, 'ri.Cvar_CheckRange( r_volumetricLocalShadowPcf, 0, 1, qtrue );',
                  'ri.Cvar_CheckRange( r_volumetricLocalShadowPcf, 0, 2, qtrue ); // '+MARK,
                  "fire PCF 9-tap selector")
    init = change(init, 'ri.Cvar_CheckRange( r_volumetricSunMode, 0, 1, qtrue );',
                  '// '+MARK+': extended sample count.\n\tri.Cvar_CheckRange( r_volumetricSunSamples, 4, 64, qtrue );\n\tri.Cvar_CheckRange( r_volumetricSunMode, 0, 1, qtrue );', "sun samples bounds")

    output = (sun, local, up, back, init)
    for rel, data in zip(FILES, output):
        assert data != before[rel], rel
        (parent/rel).write_text(data)
    return {
        "marker": MARK,
        "modified_files": ["SP/code/rend2/"+f for f in FILES],
        "sha256_before": {f: hashlib.sha256(v.encode()).hexdigest() for f,v in before.items()},
        "sha256_after": {f: hashlib.sha256((parent/f).read_bytes()).hexdigest() for f in FILES},
        "CSM_shadow_producers": "UNCHANGED",
        "SSGI_Tesla_color_textures": "UNCHANGED",
        "GPU_visual_acceptance": "NOT_TESTED"
    }

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("source",type=Path)
    parser.add_argument("--proof",type=Path)
    args=parser.parse_args()
    outcome=apply(args.source)
    if args.proof:
        args.proof.parent.mkdir(parents=True,exist_ok=True)
        args.proof.write_text(json.dumps(outcome,indent=2)+"\n")
    print("DARKWOLF_VOLUMETRIC_WAVE_CLEAN_V2_SOURCE_PASS")
