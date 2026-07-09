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
"""

NEW_CVAR_EXTERNS = """
extern cvar_t *r_dlightShadows;
extern cvar_t *r_dlightShadowMaxLights;
extern cvar_t *r_dlightShadowMapSize;
extern cvar_t *r_dlightShadowBias;
extern cvar_t *r_dlightShadowFilter;
"""

REGISTER_SNIPPET = (
    'r_dlightShadows = ri.Cvar_Get( "r_dlightShadows", "0", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowMaxLights = ri.Cvar_Get( "r_dlightShadowMaxLights", "1", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowMapSize = ri.Cvar_Get( "r_dlightShadowMapSize", "256", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowBias = ri.Cvar_Get( "r_dlightShadowBias", "0.003", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowFilter = ri.Cvar_Get( "r_dlightShadowFilter", "1", CVAR_ARCHIVE | CVAR_LATCH );'
)

def insert_global_defs_after_r_dlightmode(s):
    if "cvar_t *r_dlightShadows;" in s:
        return s

    # Best case: upstream has a real global definition for r_dlightMode in tr_init.c.
    if "cvar_t *r_dlightMode;" in s:
        return s.replace("cvar_t *r_dlightMode;", "cvar_t *r_dlightMode;\n" + NEW_CVAR_DEFS, 1)

    # Fallback for minified/unexpected layout: insert after first include block.
    m = list(re.finditer(r'^\s*#include\s+.*$', s, flags=re.M))
    if m:
        pos = m[-1].end()
        return s[:pos] + "\n" + NEW_CVAR_DEFS + s[pos:]

    # Last fallback: prepend. cvar_t should normally be known through includes, so this is less ideal.
    return NEW_CVAR_DEFS + "\n" + s

def patch_init(path):
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")
    s = path.read_text(encoding="utf-8", errors="replace")
    original = s

    s = insert_global_defs_after_r_dlightmode(s)

    # Register cvars after r_dlightMode registration. Avoid duplicate registration.
    if 'ri.Cvar_Get( "r_dlightShadows"' not in s:
        target = 'r_dlightMode = ri.Cvar_Get( "r_dlightMode", "0", CVAR_ARCHIVE | CVAR_LATCH );'
        if target in s:
            s = s.replace(target, target + " " + REGISTER_SNIPPET, 1)
        else:
            # Fallback: place near any r_dlightMode Cvar_Get occurrence.
            s, n = re.subn(
                r'(r_dlightMode\s*=\s*ri\.Cvar_Get\s*\(\s*"r_dlightMode"\s*,\s*"0"\s*,\s*CVAR_ARCHIVE\s*\|\s*CVAR_LATCH\s*\)\s*;)',
                r'\1 ' + REGISTER_SNIPPET,
                s,
                count=1
            )
            if n == 0:
                raise SystemExit(f"Could not find r_dlightMode registration in {path}")

    path.write_text(s, encoding="utf-8")
    print(f"Patched cvar definitions/registration in {path}")

def patch_local(path):
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")
    s = path.read_text(encoding="utf-8", errors="replace")

    # Add extern declarations to header only.
    if "extern cvar_t *r_dlightShadows;" not in s:
        if "extern cvar_t *r_dlightMode;" in s:
            s = s.replace("extern cvar_t *r_dlightMode;", "extern cvar_t *r_dlightMode;\n" + NEW_CVAR_EXTERNS, 1)
        else:
            s += "\n" + NEW_CVAR_EXTERNS + "\n"

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

    # Balanced lighting.
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

    # Separate no-shadow mode2 from experimental mode3 shadow gate.
    s = sub(
        s,
        r'if\s*\(\s*r_dlightMode->integer\s*>=\s*2\s*\)\s*GL_BindToTMU\s*\(\s*tr\.shadowCubemaps\s*\[\s*l\s*\]\s*,\s*TB_SHADOWMAP\s*\)\s*;',
        'if (r_dlightMode->integer >= 3 && r_dlightShadows && r_dlightShadows->integer)\n'
        '\t\t{\n'
        '\t\t\t/* Experimental mode 3: allow stock cubemap shadow path only when explicitly enabled. */\n'
        '\t\t\tGL_BindToTMU(tr.shadowCubemaps[l], TB_SHADOWMAP);\n'
        '\t\t}\n'
        '\t\telse if (r_dlightMode->integer >= 2)\n'
        '\t\t{\n'
        '\t\t\t/* Mode 2 remains balanced and shadow-free. */\n'
        '\t\t\tGL_BindToTMU(tr.whiteImage, TB_SHADOWMAP);\n'
        '\t\t}',
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

print("r_dlightMode 3 / r_dlightShadows experimental patch v2 completed.")
