#!/usr/bin/env python3
"""Conservative 4-tap *decoded-depth* PCF for post-Fire/Tesla world occlusion.

Source-limited diagnostic candidate, not a production acceptance.
Retains 256 cubemap, all capture and caching, receiver-plane intersection,
original 0.35 bias and wall-occlusion visibility. Does not affect CSM.
"""
import argparse
import hashlib
import json
from pathlib import Path

MARK = "DARKWOLF_WORLD_OCCLUSION_PCF4_V1"
REPLACEMENT = r'''// DARKWOLF_WORLD_OCCLUSION_PCF4_V1: interpolate four depth comparisons,
// not compressed RGB depth values. Exact original physical plane depth and bias.
float DW_WorldOcclusionSample(vec3 ray, vec3 normal, float planeDotV, float fallbackDepth)
{
    ray = normalize(ray);
    float denom = dot(normal, ray);
    float depth = fallbackDepth;
    if (abs(denom) > 0.000001)
    {
        float planeDepth = planeDotV / denom;
        if (planeDepth > 0.0) depth = planeDepth;
    }
#if __VERSION__ >= 130
    vec3 encodedDepth = texture(u_DlightWorldMap, ray).rgb;
#else
    vec3 encodedDepth = textureCube(u_DlightWorldMap, ray).rgb;
#endif
    float stored = dot(encodedDepth, vec3(1.0, 1.0 / 255.0, 1.0 / 65025.0));
    return step((depth - 0.35) * u_DlightWorldOrigin.w, stored);
}
float DW_WorldOcclusionFaceSample(vec3 faceVector, int face, vec2 texel,
                                  vec3 normal, float planeDotV, float fallbackDepth)
{
    vec2 center = (clamp(texel, vec2(0.0), vec2(255.0)) + vec2(0.5)) * (2.0 / 256.0) - vec2(1.0);
    if (face == 0) faceVector.yz = center;
    else if (face == 1) faceVector.xz = center;
    else faceVector.xy = center;
    return DW_WorldOcclusionSample(faceVector, normal, planeDotV, fallbackDepth);
}
float DlightWorldVisibility(vec3 worldPosition)
{
    if (u_DlightWorldOrigin.w <= 0.0) return 1.0;
    vec3 v = u_DlightWorldOrigin.xyz - worldPosition;
    vec3 a = abs(v);
    float major = max(a.x, max(a.y, a.z));
    if (major < 0.0001) return 1.0;
    vec3 faceVector = v / major;
    int face = 2;
    vec2 uv = faceVector.xy;
    if (a.x >= a.y && a.x >= a.z)
    {
        face = 0;
        uv = faceVector.yz;
    }
    else if (a.y >= a.z)
    {
        face = 1;
        uv = faceVector.xz;
    }
    vec2 coord = (uv * 0.5 + 0.5) * 256.0 - vec2(0.5);
    vec2 base = floor(coord);
    vec2 blend = fract(coord);
    vec3 normal = cross(dFdx(worldPosition), dFdy(worldPosition));
    float planeDotV = dot(normal, v);
    float fallbackDepth = length(v);
    float a00 = DW_WorldOcclusionFaceSample(faceVector, face, base, normal, planeDotV, fallbackDepth);
    float a10 = DW_WorldOcclusionFaceSample(faceVector, face, base + vec2(1.0, 0.0), normal, planeDotV, fallbackDepth);
    float a01 = DW_WorldOcclusionFaceSample(faceVector, face, base + vec2(0.0, 1.0), normal, planeDotV, fallbackDepth);
    float a11 = DW_WorldOcclusionFaceSample(faceVector, face, base + vec2(1.0, 1.0), normal, planeDotV, fallbackDepth);
    return mix(mix(a00, a10, blend.x), mix(a01, a11, blend.x), blend.y);
}'''

def apply(source: Path):
    reports = []
    prefix = source / "SP/code/rend2/glsl"
    for filename in ("dlight_fp.glsl", "lightall_fp.glsl"):
        path = prefix / filename
        before = path.read_text()
        assert MARK not in before, (filename, "already patched")
        anchor = "float DlightWorldVisibility(vec3 worldPosition)"
        assert before.count(anchor) == 1, (filename, "different baseline")
        start = before.index(anchor)
        end = before.index("\nuniform samplerCube u_DlightShadowMap;", start)
        original = before[start:end]
        assert original.count("return step((depth - 0.35) * u_DlightWorldOrigin.w, stored);") == 1
        assert original.count("floor((q * 0.5 + 0.5) * 256.0)") == 1
        assert original.count("textureCube(u_DlightWorldMap, q)") == 1
        assert original.count("dot(planeNormal, v) / denominator") == 1
        after = before[:start] + REPLACEMENT + before[end:]
        assert after.count(MARK) == 1
        assert after.count("DlightWorldVisibility(vec3 worldPosition)") == 1
        path.write_text(after)
        reports.append(dict(file=filename,original_sha256=hashlib.sha256(before.encode()).hexdigest(),
                            patched_sha256=hashlib.sha256(after.encode()).hexdigest()))
    print(MARK + "_SOURCE_PATCH_PASS", json.dumps(reports), flush=True)
    return reports

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source",type=Path)
    p.add_argument("--manifest",type=Path)
    args = p.parse_args()
    result = apply(args.source)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True,exist_ok=True)
        args.manifest.write_text(json.dumps({"status":"SOURCE_PATCHED_ONLY_UNTESTED", "files":result}, indent=2) + "\n")
