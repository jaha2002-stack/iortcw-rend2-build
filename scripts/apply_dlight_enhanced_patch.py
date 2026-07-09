#!/usr/bin/env python3
from pathlib import Path

VP = r"""attribute vec3 attr_Position;
attribute vec4 attr_TexCoord0;
attribute vec3 attr_Normal;

uniform vec4 u_DlightInfo;

#if defined(USE_DEFORM_VERTEXES)
uniform int u_DeformGen;
uniform float u_DeformParams[5];
uniform float u_Time;
#endif

uniform vec4 u_Color;
uniform mat4 u_ModelViewProjectionMatrix;

varying vec2 var_Tex1;
varying vec4 var_Color;
varying vec3 var_DlightVector;
varying vec3 var_Normal;

#if defined(USE_DEFORM_VERTEXES)
vec3 DeformPosition(const vec3 pos, const vec3 normal, const vec2 st)
{
    if (u_DeformGen == 0)
    {
        return pos;
    }

    float base = u_DeformParams[0];
    float amplitude = u_DeformParams[1];
    float phase = u_DeformParams[2];
    float frequency = u_DeformParams[3];
    float spread = u_DeformParams[4];

    if (u_DeformGen == DGEN_BULGE)
    {
        phase *= st.x;
    }
    else
    {
        phase += dot(pos.xyz, vec3(spread));
    }

    float value = phase + (u_Time * frequency);
    float func;

    if (u_DeformGen == DGEN_WAVE_SIN)
    {
        func = sin(value * 2.0 * M_PI);
    }
    else if (u_DeformGen == DGEN_WAVE_SQUARE)
    {
        func = sign(0.5 - fract(value));
    }
    else if (u_DeformGen == DGEN_WAVE_TRIANGLE)
    {
        func = abs(fract(value + 0.75) - 0.5) * 4.0 - 1.0;
    }
    else if (u_DeformGen == DGEN_WAVE_SAWTOOTH)
    {
        func = fract(value);
    }
    else if (u_DeformGen == DGEN_WAVE_INVERSE_SAWTOOTH)
    {
        func = (1.0 - fract(value));
    }
    else
    {
        func = sin(value);
    }

    return pos + normal * (base + func * amplitude);
}
#endif

void main()
{
    vec3 position = attr_Position;
    vec3 normal = normalize(attr_Normal);

#if defined(USE_DEFORM_VERTEXES)
    position = DeformPosition(position, normal, attr_TexCoord0.st);
#endif

    gl_Position = u_ModelViewProjectionMatrix * vec4(position, 1.0);

    vec3 dist = u_DlightInfo.xyz - position;

    // Keep the original projected dlight cookie coordinates.
    var_Tex1 = dist.xy * u_DlightInfo.a + vec2(0.5);

    // Pass data to the fragment shader so the important lighting terms are
    // calculated per pixel instead of only per vertex.
    var_DlightVector = dist;
    var_Normal = normal;

    // Preserve the old axial clipping/fade, but leave facing/radial falloff
    // to the fragment shader for smoother results.
    float axialFade = clamp(2.0 * (1.0 - abs(dist.z) * u_DlightInfo.a), 0.0, 1.0);
    var_Color = u_Color * axialFade;
}
"""

FP = r"""uniform sampler2D u_DiffuseMap;
uniform int u_AlphaTest;
uniform vec4 u_DlightInfo;

varying vec2 var_Tex1;
varying vec4 var_Color;
varying vec3 var_DlightVector;
varying vec3 var_Normal;

void main()
{
    // Prevent projected-light texture wrapping/leaking outside the dlight volume.
    if (var_Tex1.x < 0.0 || var_Tex1.x > 1.0 || var_Tex1.y < 0.0 || var_Tex1.y > 1.0)
    {
        discard;
    }

    vec4 color = texture2D(u_DiffuseMap, var_Tex1);
    float alpha = color.a * var_Color.a;

    if (u_AlphaTest == 1)
    {
        if (alpha <= 0.0)
            discard;
    }
    else if (u_AlphaTest == 2)
    {
        if (alpha >= 0.5)
            discard;
    }
    else if (u_AlphaTest == 3)
    {
        if (alpha < 0.5)
            discard;
    }

    vec3 L = normalize(var_DlightVector);
    vec3 N = normalize(var_Normal);

    // Original shader used a hard step(dot(dist, normal)).
    // This keeps the same idea but makes the transition much softer.
    float facing = max(dot(L, N), 0.0);
    facing = smoothstep(0.02, 0.55, facing);

    // Real radial attenuation based on light radius.
    // u_DlightInfo.a is the inverse radius used by the original shader.
    float invRadius = max(u_DlightInfo.a, 0.0001);
    float radial = clamp(1.0 - length(var_DlightVector) * invRadius, 0.0, 1.0);
    radial = radial * radial * (3.0 - 2.0 * radial);

    vec3 lightColor = clamp(var_Color.rgb, vec3(0.0), vec3(8.0));
    vec3 result = color.rgb * lightColor * facing * radial;

    gl_FragColor.rgb = result;
    gl_FragColor.a = alpha;
}
"""

paths = [
    Path("SP/code/rend2/glsl/dlight_vp.glsl"),
    Path("SP/code/rend2/glsl/dlight_fp.glsl"),
    Path("MP/code/rend2/glsl/dlight_vp.glsl"),
    Path("MP/code/rend2/glsl/dlight_fp.glsl"),
]

for p in paths:
    if not p.exists():
        raise SystemExit(f"Missing expected shader file: {p}")
    p.write_text(VP if p.name == "dlight_vp.glsl" else FP, encoding="utf-8")
    print(f"Overwritten: {p}")

print("Rend2 enhanced dlight shader overwrite completed.")
