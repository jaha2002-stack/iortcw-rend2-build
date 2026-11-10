#!/usr/bin/env python3
"""Targeted world-visibility depth mask PCF2x2, exact #40628480022 lineage.

Replace ONLY identical world-cubemap visibility functions in Rend2 GLSL.
No global shadow PCF/bias/cubemap size, C code, new CVars or telemetry changes.
"""
import argparse,hashlib,json
from pathlib import Path

MARK="DARKWOLF_CRYPT1_ARCHITECTURAL_WORLD_VISIBILITY_PCF2X2_V1_20261028"
BASE_RUN=40628480022
GLSL=("glsl/dlight_fp.glsl","glsl/lightall_fp.glsl")
EXPECTED_FUNCTION_SHA="2e518538bb8fb3db37377e539b8642e4c18bd1327e1b1ef1bf1cabdb909348d8"
def H(s): return hashlib.sha256(s.encode()).hexdigest()
def extract(s):
    a=s.index("float DlightWorldVisibility(vec3 worldPosition)")
    b=s.index("\n}\n",a)+3
    return a,b,s[a:b]

# Cube textures remain GL_NEAREST: never filter packed RGB depths in hardware.
# Bilinear filter the four *visibility comparisons*, after per-texel radial-depth
# reconstruction and receiver-plane correction. Interior occlusion still 0.0;
# fully visible regions remain 1.0. Only a 1-texel world-mask edge is softened.
REPLACEMENT=r'''// DARKWOLF_CRYPT1_ARCHITECTURAL_WORLD_VISIBILITY_PCF2X2_V1_20261028
// Keep solid-world containment. Compare four nearest 256x256 cubemap texels
// independently, and bilinearly interpolate their binary visibility results.
// Do NOT interpolate RGB-packed depth values, and do NOT change 2048x2048
// primary DLight PCF: this mask only rejects light crossing architecture.
float DlightWorldVisibility(vec3 worldPosition)
{
    if (u_DlightWorldOrigin.w <= 0.0) return 1.0;

    vec3 v = u_DlightWorldOrigin.xyz - worldPosition;
    vec3 a = abs(v);
    float major = max(a.x, max(a.y, a.z));
    if (major < 0.0001) return 1.0;

    vec3 baseRay = v / major;
    int majorAxis = (a.x >= a.y && a.x >= a.z) ? 0 :
                    (a.y >= a.z) ? 1 : 2;
    vec2 faceCoords = (majorAxis == 0) ? baseRay.yz :
                      (majorAxis == 1) ? baseRay.xz : baseRay.xy;

    // Coordinates in texel-center space: integer coordinates are texel centers.
    const float worldSize = 256.0;
    vec2 centerSpace = (faceCoords * 0.5 + 0.5) * worldSize - 0.5;
    vec2 baseTexel = floor(centerSpace);
    vec2 mixWeights = fract(centerSpace);
    vec3 receiverNormal = cross(dFdx(worldPosition), dFdy(worldPosition));
    float numerator = dot(receiverNormal, v);
    float originalDepth = length(v);
    float visibility = 0.0;

    for (int iy = 0; iy < 2; ++iy)
    {
        for (int ix = 0; ix < 2; ++ix)
        {
            vec2 texel = clamp(baseTexel + vec2(float(ix), float(iy)),
                               vec2(0.0), vec2(worldSize - 1.0));
            vec2 uv = (texel + vec2(0.5)) * (2.0 / worldSize) - vec2(1.0);
            vec3 ray = baseRay;
            if (majorAxis == 0) ray.yz = uv;
            else if (majorAxis == 1) ray.xz = uv;
            else ray.xy = uv;
            ray = normalize(ray);

            float depth = originalDepth;
            float denominator = dot(receiverNormal, ray);
            if (abs(denominator) > 0.000001)
            {
                float planeDepth = numerator / denominator;
                if (planeDepth > 0.0) depth = planeDepth;
            }
#if __VERSION__ >= 130
            vec3 encodedDepth = texture(u_DlightWorldMap, ray).rgb;
#else
            vec3 encodedDepth = textureCube(u_DlightWorldMap, ray).rgb;
#endif
            float stored = dot(encodedDepth, vec3(1.0, 1.0 / 255.0, 1.0 / 65025.0));
            float test = step((depth - 0.35) * u_DlightWorldOrigin.w, stored);
            float wx = (ix == 0) ? (1.0 - mixWeights.x) : mixWeights.x;
            float wy = (iy == 0) ? (1.0 - mixWeights.y) : mixWeights.y;
            visibility += wx * wy * test;
        }
    }
    return clamp(visibility, 0.0, 1.0);
}'''
def apply(root):
    folder=root/"SP/code/rend2"
    before={}
    after={}
    for rel in GLSL:
        path=folder/rel
        text=path.read_text()
        assert MARK not in text,("DOUBLE_PATCH",rel)
        assert "uniform samplerCube u_DlightWorldMap;" in text,rel
        assert "uniform vec4 u_DlightWorldOrigin;" in text,rel
        assert "DlightWorldVisibility(" in text,rel
        assert "u_DlightShadowMap" in text,("MAIN_SHADOW_MISSING",rel)
        a,b,old=extract(text)
        assert H(old)==EXPECTED_FUNCTION_SHA,("UNEXPECTED_PRODUCTION_WORLD_MASK",rel,H(old))
        assert old.count("return step(")==1
        assert "256.0" in old and "cross(dFdx(worldPosition), dFdy(worldPosition))" in old
        before[rel]=text
        after[rel]=text[:a]+REPLACEMENT+text[b:]
        assert after[rel].count(MARK)==1,rel
        assert after[rel].count("DlightWorldVisibility(")==text.count("DlightWorldVisibility(")
        assert after[rel].count("u_DlightShadowMap")==text.count("u_DlightShadowMap")
    assert extract(after[GLSL[0]])[2]==extract(after[GLSL[1]])[2]
    for rel,s in after.items():
        (folder/rel).write_text(s)
    return {
      "marker":MARK,"accepted_binary_base_run":BASE_RUN,
      "changed_source_files":["SP/code/rend2/"+rel for rel in GLSL],
      "before_sha256":{rel:H(s) for rel,s in before.items()},
      "after_sha256":{rel:H(s) for rel,s in after.items()},
      "old_world_function_sha256":EXPECTED_FUNCTION_SHA,
      "new_world_function_sha256":H(REPLACEMENT),
      "rendering_change":"World 256x256 point mask: nearest hard binary to 2x2 bilinear filtered depth comparisons",
      "unchanged":["world mask capture size and GL_NEAREST","raw packed depth sampling",
          "receiver-plane depth correction","world depth epsilon 0.35","solid wall rejection",
          "main 2048 point shadow/PCF","3 persistent + 2 dynamic slot budgets",
          "Sun3","FireE","Local","Sky","SSGI","Tesla","textures","Bloom v2"],
      "new_cvars":[],"telemetry":False,"gpu_acceptance":"PENDING"}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("source",type=Path)
    p.add_argument("--proof",type=Path)
    a=p.parse_args()
    proof=apply(a.source)
    if a.proof:
        a.proof.parent.mkdir(parents=True,exist_ok=True)
        a.proof.write_text(json.dumps(proof,indent=2,ensure_ascii=False)+"\n")
    print("DW_CRYPT1_WORLD_PCF2X2_EXACT_SOURCE_PATCH_PASS")
