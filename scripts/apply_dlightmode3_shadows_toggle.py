#!/usr/bin/env python3
from pathlib import Path
import re

SETS = [
    (Path("SP/code/rend2/tr_init.c"), Path("SP/code/rend2/tr_local.h"), Path("SP/code/rend2/tr_shade.c")),
    (Path("MP/code/rend2/tr_init.c"), Path("MP/code/rend2/tr_local.h"), Path("MP/code/rend2/tr_shade.c")),
]

def patch_init(path):
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")
    s = path.read_text(encoding="utf-8", errors="replace")
    if "cvar_t *r_dlightShadows;" not in s:
        s = s.replace(
            "cvar_t *r_dlightMode;",
            "cvar_t *r_dlightMode; cvar_t *r_dlightShadows; cvar_t *r_dlightShadowMaxLights; cvar_t *r_dlightShadowMapSize; cvar_t *r_dlightShadowBias; cvar_t *r_dlightShadowFilter;"
        )
    if 'r_dlightShadows = ri.Cvar_Get' not in s:
        s = s.replace(
            'r_dlightMode = ri.Cvar_Get( "r_dlightMode", "0", CVAR_ARCHIVE | CVAR_LATCH );',
            'r_dlightMode = ri.Cvar_Get( "r_dlightMode", "0", CVAR_ARCHIVE | CVAR_LATCH ); '
            'r_dlightShadows = ri.Cvar_Get( "r_dlightShadows", "0", CVAR_ARCHIVE | CVAR_LATCH ); '
            'r_dlightShadowMaxLights = ri.Cvar_Get( "r_dlightShadowMaxLights", "1", CVAR_ARCHIVE | CVAR_LATCH ); '
            'r_dlightShadowMapSize = ri.Cvar_Get( "r_dlightShadowMapSize", "256", CVAR_ARCHIVE | CVAR_LATCH ); '
            'r_dlightShadowBias = ri.Cvar_Get( "r_dlightShadowBias", "0.003", CVAR_ARCHIVE | CVAR_LATCH ); '
            'r_dlightShadowFilter = ri.Cvar_Get( "r_dlightShadowFilter", "1", CVAR_ARCHIVE | CVAR_LATCH );'
        )
    path.write_text(s, encoding="utf-8")
    print(f"Patched cvars in {path}")

def patch_local(path):
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")
    s = path.read_text(encoding="utf-8", errors="replace")
    if "extern cvar_t *r_dlightShadows;" not in s:
        if "extern cvar_t *r_dlightMode;" in s:
            s = s.replace(
                "extern cvar_t *r_dlightMode;",
                "extern cvar_t *r_dlightMode; extern cvar_t *r_dlightShadows; extern cvar_t *r_dlightShadowMaxLights; extern cvar_t *r_dlightShadowMapSize; extern cvar_t *r_dlightShadowBias; extern cvar_t *r_dlightShadowFilter;"
            )
        else:
            s += "\nextern cvar_t *r_dlightShadows; extern cvar_t *r_dlightShadowMaxLights; extern cvar_t *r_dlightShadowMapSize; extern cvar_t *r_dlightShadowBias; extern cvar_t *r_dlightShadowFilter;\n"
    path.write_text(s, encoding="utf-8")
    print(f"Patched extern cvars in {path}")

def sub(s, pattern, repl, label):
    ns, n = re.subn(pattern, repl, s)
    print(f"{label}: {n}")
    return ns

def patch_shade(path):
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")
    s = path.read_text(encoding="utf-8", errors="replace")
    original = s
    s = sub(
        s,
        r'GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_DIRECTEDLIGHT\s*,\s*dl->color\s*\)\s*;',
        'VectorScale(dl->color, 1.10f, vector);\n\t\tGLSL_SetUniformVec3(sp, UNIFORM_DIRECTEDLIGHT, vector);',
        "directed light balanced"
    )
    s = sub(
        s,
        r'VectorSet\s*\(\s*vector\s*,\s*0\s*,\s*0\s*,\s*0\s*\)\s*;\s*GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_AMBIENTLIGHT\s*,\s*vector\s*\)\s*;',
        'VectorScale(dl->color, 0.020f, vector);\n\t\tGLSL_SetUniformVec3(sp, UNIFORM_AMBIENTLIGHT, vector);',
        "low ambient"
    )
    s = sub(
        s,
        r'GLSL_SetUniformFloat\s*\(\s*sp\s*,\s*UNIFORM_LIGHTRADIUS\s*,\s*radius\s*\)\s*;',
        'GLSL_SetUniformFloat(sp, UNIFORM_LIGHTRADIUS, radius * 1.07f);',
        "radius"
    )
    s = sub(
        s,
        r'if\s*\(\s*r_dlightMode->integer\s*>=\s*2\s*\)\s*GL_BindToTMU\s*\(\s*tr\.shadowCubemaps\s*\[\s*l\s*\]\s*,\s*TB_SHADOWMAP\s*\)\s*;',
        'if (r_dlightMode->integer >= 3 && r_dlightShadows && r_dlightShadows->integer)\n\t\t{\n\t\t\tGL_BindToTMU(tr.shadowCubemaps[l], TB_SHADOWMAP);\n\t\t}\n\t\telse if (r_dlightMode->integer >= 2)\n\t\t{\n\t\t\tGL_BindToTMU(tr.whiteImage, TB_SHADOWMAP);\n\t\t}',
        "mode3 shadow gate"
    )
    if s == original:
        raise SystemExit(f"No shade changes applied to {path}")
    path.write_text(s, encoding="utf-8")
    print(f"Patched shade in {path}")

for tr_init, tr_local, tr_shade in SETS:
    patch_init(tr_init)
    patch_local(tr_local)
    patch_shade(tr_shade)

print("r_dlightMode 3 / r_dlightShadows experimental patch completed.")
