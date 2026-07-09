#!/usr/bin/env python3
from pathlib import Path
import re

TARGETS = [Path("SP/code/rend2/tr_shade.c"), Path("MP/code/rend2/tr_shade.c")]

def sub(s, pattern, repl, label):
    ns, n = re.subn(pattern, repl, s)
    print(f"{label}: {n}")
    return ns

def patch_file(path):
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")
    s = path.read_text(encoding="utf-8", errors="replace")
    original = s

    s = sub(
        s,
        r'GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_DIRECTEDLIGHT\s*,\s*dl->color\s*\)\s*;',
        'VectorScale(dl->color, 1.10f, vector);\n\t\tGLSL_SetUniformVec3(sp, UNIFORM_DIRECTEDLIGHT, vector);',
        "directed light balanced boost"
    )
    s = sub(
        s,
        r'VectorSet\s*\(\s*vector\s*,\s*0\s*,\s*0\s*,\s*0\s*\)\s*;\s*GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_AMBIENTLIGHT\s*,\s*vector\s*\)\s*;',
        'VectorScale(dl->color, 0.020f, vector);\n\t\tGLSL_SetUniformVec3(sp, UNIFORM_AMBIENTLIGHT, vector);',
        "low dlight ambient"
    )
    s = sub(
        s,
        r'GLSL_SetUniformFloat\s*\(\s*sp\s*,\s*UNIFORM_LIGHTRADIUS\s*,\s*radius\s*\)\s*;',
        'GLSL_SetUniformFloat(sp, UNIFORM_LIGHTRADIUS, radius * 1.07f);',
        "radius balanced boost"
    )
    s = sub(
        s,
        r'if\s*\(\s*r_dlightMode->integer\s*>=\s*2\s*\)\s*GL_BindToTMU\s*\(\s*tr\.shadowCubemaps\s*\[\s*l\s*\]\s*,\s*TB_SHADOWMAP\s*\)\s*;',
        'if (r_dlightMode->integer >= 2)\n\t\t{\n\t\t\t/* Balanced Atmospheric: keep mode 2 stable and shadow-free. */\n\t\t\tGL_BindToTMU(tr.whiteImage, TB_SHADOWMAP);\n\t\t}',
        "disable broken mode2 shadow cubemap"
    )

    if s == original:
        raise SystemExit(f"No changes applied to {path}")
    path.write_text(s, encoding="utf-8")
    print(f"Patched {path}")

for p in TARGETS:
    patch_file(p)

print("r_dlightMode 2 Balanced Atmospheric patch completed.")
