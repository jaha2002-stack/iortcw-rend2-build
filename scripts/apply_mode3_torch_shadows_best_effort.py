#!/usr/bin/env python3
from pathlib import Path
import re

SETS = [
    (Path("SP/code/rend2/tr_init.c"), Path("SP/code/rend2/tr_local.h"), Path("SP/code/rend2/tr_shade.c")),
    (Path("MP/code/rend2/tr_init.c"), Path("MP/code/rend2/tr_local.h"), Path("MP/code/rend2/tr_shade.c")),
]

NEW_CVAR_DEFS = """
cvar_t *r_dlightShadows;
cvar_t *r_dlightShadowMaxLights;
cvar_t *r_dlightShadowMapSize;
cvar_t *r_dlightShadowBias;
cvar_t *r_dlightShadowFilter;
cvar_t *r_dlightShadowTorchOnly;
cvar_t *r_dlightShadowExplosions;
cvar_t *r_dlightShadowMuzzle;
"""

NEW_CVAR_EXTERNS = """
extern cvar_t *r_dlightShadows;
extern cvar_t *r_dlightShadowMaxLights;
extern cvar_t *r_dlightShadowMapSize;
extern cvar_t *r_dlightShadowBias;
extern cvar_t *r_dlightShadowFilter;
extern cvar_t *r_dlightShadowTorchOnly;
extern cvar_t *r_dlightShadowExplosions;
extern cvar_t *r_dlightShadowMuzzle;
"""

REGISTER_SNIPPET = (
    'r_dlightShadows = ri.Cvar_Get( "r_dlightShadows", "0", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowMaxLights = ri.Cvar_Get( "r_dlightShadowMaxLights", "2", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowMapSize = ri.Cvar_Get( "r_dlightShadowMapSize", "512", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowBias = ri.Cvar_Get( "r_dlightShadowBias", "0.004", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowFilter = ri.Cvar_Get( "r_dlightShadowFilter", "1", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowTorchOnly = ri.Cvar_Get( "r_dlightShadowTorchOnly", "1", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowExplosions = ri.Cvar_Get( "r_dlightShadowExplosions", "0", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowMuzzle = ri.Cvar_Get( "r_dlightShadowMuzzle", "0", CVAR_ARCHIVE | CVAR_LATCH );'
)

def insert_global_defs_after_r_dlightmode(s):
    if "cvar_t *r_dlightShadows;" in s:
        return s
    if "cvar_t *r_dlightMode;" in s:
        return s.replace("cvar_t *r_dlightMode;", "cvar_t *r_dlightMode;\n" + NEW_CVAR_DEFS, 1)
    m = list(re.finditer(r'^\s*#include\s+.*$', s, flags=re.M))
    if m:
        pos = m[-1].end()
        return s[:pos] + "\n" + NEW_CVAR_DEFS + s[pos:]
    return NEW_CVAR_DEFS + "\n" + s

def patch_init(path):
    s = path.read_text(encoding="utf-8", errors="replace")
    s = insert_global_defs_after_r_dlightmode(s)
    if 'ri.Cvar_Get( "r_dlightShadows"' not in s:
        target = 'r_dlightMode = ri.Cvar_Get( "r_dlightMode", "0", CVAR_ARCHIVE | CVAR_LATCH );'
        if target in s:
            s = s.replace(target, target + " " + REGISTER_SNIPPET, 1)
        else:
            s, n = re.subn(
                r'(r_dlightMode\s*=\s*ri\.Cvar_Get\s*\(\s*"r_dlightMode"\s*,\s*"0"\s*,\s*CVAR_ARCHIVE\s*\|\s*CVAR_LATCH\s*\)\s*;)',
                r'\1 ' + REGISTER_SNIPPET,
                s,
                count=1
            )
            if n == 0:
                raise SystemExit(f"Could not find r_dlightMode registration in {path}")
    path.write_text(s, encoding="utf-8")
    print(f"Patched init: {path}")

def patch_local(path):
    s = path.read_text(encoding="utf-8", errors="replace")
    if "extern cvar_t *r_dlightShadows;" not in s:
        if "extern cvar_t *r_dlightMode;" in s:
            s = s.replace("extern cvar_t *r_dlightMode;", "extern cvar_t *r_dlightMode;\n" + NEW_CVAR_EXTERNS, 1)
        else:
            s += "\n" + NEW_CVAR_EXTERNS + "\n"
    path.write_text(s, encoding="utf-8")
    print(f"Patched header: {path}")

def sub(s, pattern, repl, label):
    ns, n = re.subn(pattern, repl, s)
    print(f"{label}: {n}")
    return ns

def patch_shade(path):
    s = path.read_text(encoding="utf-8", errors="replace")
    original = s

    # Balanced material-light tuning first.
    s = sub(
        s,
        r'GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_DIRECTEDLIGHT\s*,\s*dl->color\s*\)\s*;',
        'VectorScale(dl->color, 1.08f, vector);\n\t\tGLSL_SetUniformVec3(sp, UNIFORM_DIRECTEDLIGHT, vector);',
        "directed light balanced"
    )
    s = sub(
        s,
        r'VectorSet\s*\(\s*vector\s*,\s*0\s*,\s*0\s*,\s*0\s*\)\s*;\s*GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_AMBIENTLIGHT\s*,\s*vector\s*\)\s*;',
        'VectorScale(dl->color, 0.015f, vector);\n\t\tGLSL_SetUniformVec3(sp, UNIFORM_AMBIENTLIGHT, vector);',
        "low ambient"
    )
    s = sub(
        s,
        r'GLSL_SetUniformFloat\s*\(\s*sp\s*,\s*UNIFORM_LIGHTRADIUS\s*,\s*radius\s*\)\s*;',
        'GLSL_SetUniformFloat(sp, UNIFORM_LIGHTRADIUS, radius * 1.05f);',
        "radius"
    )

    # Main mode gate.
    s = sub(
        s,
        r'if\s*\(\s*r_dlightMode->integer\s*>=\s*2\s*\)\s*GL_BindToTMU\s*\(\s*tr\.shadowCubemaps\s*\[\s*l\s*\]\s*,\s*TB_SHADOWMAP\s*\)\s*;',
        'if (r_dlightMode->integer >= 3 && r_dlightShadows && r_dlightShadows->integer)\n'
        '\t\t{\n'
        '\t\t\t/* Best-effort mode 3: use dynamic light shadow cubemap path explicitly. */\n'
        '\t\t\tGL_BindToTMU(tr.shadowCubemaps[l], TB_SHADOWMAP);\n'
        '\t\t}\n'
        '\t\telse if (r_dlightMode->integer >= 2)\n'
        '\t\t{\n'
        '\t\t\t/* Mode 2 stays stable and shadow-free. */\n'
        '\t\t\tGL_BindToTMU(tr.whiteImage, TB_SHADOWMAP);\n'
        '\t\t}',
        "mode3 shadow gate"
    )

    if s == original:
        raise SystemExit(f"No shade changes applied to {path}")
    path.write_text(s, encoding="utf-8")
    print(f"Patched shade: {path}")

for tr_init, tr_local, tr_shade in SETS:
    patch_init(tr_init)
    patch_local(tr_local)
    patch_shade(tr_shade)

print("Applied mode3 best-effort torch shadow patch.")
