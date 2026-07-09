#!/usr/bin/env python3
from pathlib import Path
import re

TARGETS = [
    Path("SP/code/rend2/tr_shade.c"),
    Path("MP/code/rend2/tr_shade.c"),
]

DLIGHT_VP = r"""attribute vec3 attr_Position;
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
        return pos;

    float base = u_DeformParams[0];
    float amplitude = u_DeformParams[1];
    float phase = u_DeformParams[2];
    float frequency = u_DeformParams[3];
    float spread = u_DeformParams[4];

    if (u_DeformGen == DGEN_BULGE)
        phase *= st.x;
    else
        phase += dot(pos.xyz, vec3(spread));

    float value = phase + (u_Time * frequency);
    float func;

    if (u_DeformGen == DGEN_WAVE_SIN)
        func = sin(value * 2.0 * M_PI);
    else if (u_DeformGen == DGEN_WAVE_SQUARE)
        func = sign(0.5 - fract(value));
    else if (u_DeformGen == DGEN_WAVE_TRIANGLE)
        func = abs(fract(value + 0.75) - 0.5) * 4.0 - 1.0;
    else if (u_DeformGen == DGEN_WAVE_SAWTOOTH)
        func = fract(value);
    else if (u_DeformGen == DGEN_WAVE_INVERSE_SAWTOOTH)
        func = (1.0 - fract(value));
    else
        func = sin(value);

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
    var_Tex1 = dist.xy * u_DlightInfo.a + vec2(0.5);

    var_DlightVector = dist;
    var_Normal = normal;

    float axialFade = clamp(2.0 * (1.0 - abs(dist.z) * u_DlightInfo.a), 0.0, 1.0);
    var_Color = u_Color * axialFade;
}
"""

DLIGHT_FP = r"""uniform sampler2D u_DiffuseMap;
uniform int u_AlphaTest;
uniform vec4 u_DlightInfo;

varying vec2 var_Tex1;
varying vec4 var_Color;
varying vec3 var_DlightVector;
varying vec3 var_Normal;

void main()
{
    if (var_Tex1.x < 0.0 || var_Tex1.x > 1.0 || var_Tex1.y < 0.0 || var_Tex1.y > 1.0)
        discard;

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

    float facing = max(dot(L, N), 0.0);
    facing = smoothstep(0.02, 0.50, facing);

    float invRadius = max(u_DlightInfo.a, 0.0001);
    float radial = clamp(1.0 - length(var_DlightVector) * invRadius * 0.82, 0.0, 1.0);
    radial = radial * radial * (3.0 - 2.0 * radial);

    vec3 lightColor = clamp(var_Color.rgb * 1.35, vec3(0.0), vec3(8.0));
    gl_FragColor.rgb = color.rgb * lightColor * facing * radial;
    gl_FragColor.a = alpha;
}
"""

def patch_tr_shade(path: Path):
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")

    s = path.read_text(encoding="utf-8", errors="replace")
    original = s

    # Boost the ForwardDlight material path used by r_dlightMode 2.
    # This path already binds diffuse/normal/specular stages and uses lightallShader.
    s, n1 = re.subn(
        r'GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_DIRECTEDLIGHT\s*,\s*dl->color\s*\)\s*;',
        (
            'VectorScale(dl->color, 1.35f, vector);\n'
            '\t\tGLSL_SetUniformVec3(sp, UNIFORM_DIRECTEDLIGHT, vector);'
        ),
        s
    )

    # Give dlights a tiny local ambient term so normal/specular mode does not go too black
    # on older lightmapped geometry.
    s, n2 = re.subn(
        r'VectorSet\s*\(\s*vector\s*,\s*0\s*,\s*0\s*,\s*0\s*\)\s*;\s*'
        r'GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_AMBIENTLIGHT\s*,\s*vector\s*\)\s*;',
        (
            'VectorScale(dl->color, 0.06f, vector);\n'
            '\t\tGLSL_SetUniformVec3(sp, UNIFORM_AMBIENTLIGHT, vector);'
        ),
        s
    )

    # Slightly larger radius for mode 2 lighting. This makes torch light less pinched.
    s, n3 = re.subn(
        r'GLSL_SetUniformFloat\s*\(\s*sp\s*,\s*UNIFORM_LIGHTRADIUS\s*,\s*radius\s*\)\s*;',
        'GLSL_SetUniformFloat(sp, UNIFORM_LIGHTRADIUS, radius * 1.18f);',
        s
    )

    # Stabilize the broken shadow part of r_dlightMode 2.
    # The stock code binds tr.shadowCubemaps[l] when r_dlightMode >= 2.
    # The readme marks mode 2 broken, so for this experimental build we bind a safe white
    # texture instead of the cubemap. This preserves the material dlight path and avoids
    # the worst shadow cubemap artifacts.
    s, n4 = re.subn(
        r'if\s*\(\s*r_dlightMode->integer\s*>=\s*2\s*\)\s*'
        r'GL_BindToTMU\s*\(\s*tr\.shadowCubemaps\s*\[\s*l\s*\]\s*,\s*TB_SHADOWMAP\s*\)\s*;',
        (
            'if (r_dlightMode->integer >= 2)\n'
            '\t\t{\n'
            '\t\t\t/* r_dlightMode 2 shadow cubemaps are documented as broken.\n'
            '\t\t\t * Bind a safe white texture so the material dynamic-light path remains usable\n'
            '\t\t\t * without hard black/garbled cubemap shadow artifacts.\n'
            '\t\t\t */\n'
            '\t\t\tGL_BindToTMU(tr.whiteImage, TB_SHADOWMAP);\n'
            '\t\t}'
        ),
        s
    )

    if s == original:
        raise SystemExit(f"No changes applied to {path}")

    path.write_text(s, encoding="utf-8")
    print(f"Patched {path}: directed={n1}, ambient={n2}, radius={n3}, shadowbind={n4}")

def overwrite_shader(path: Path, text: str):
    if not path.exists():
        raise SystemExit(f"Missing shader file: {path}")
    path.write_text(text, encoding="utf-8")
    print(f"Overwritten shader: {path}")

for p in TARGETS:
    patch_tr_shade(p)

# Keep the safer dlight shader from release 1 too, so r_dlightMode 1 remains usable.
for prefix in ["SP", "MP"]:
    overwrite_shader(Path(prefix) / "code/rend2/glsl/dlight_vp.glsl", DLIGHT_VP)
    overwrite_shader(Path(prefix) / "code/rend2/glsl/dlight_fp.glsl", DLIGHT_FP)

print("r_dlightMode 2 experimental/stable patch completed.")
