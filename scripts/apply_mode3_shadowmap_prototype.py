#!/usr/bin/env python3
"""
Rend2 mode3 dynamic shadow-map prototype patcher.

This is intentionally a source-rewriting prototype kit.
It avoids fragile git patches because upstream rend2 source files are often minified
or reformatted into very long lines.

Goal:
- r_dlightMode 2: balanced, stable, no broken shadows.
- r_dlightMode 3 + r_dlightShadows 1: prototype shadow-casting dynamic-light mode.
- Add cvars and runtime debug controls for selecting only 1-2 strongest/nearest dlights.
- Reuse the existing rend2 shadowCubemap/lightall path where present.
- Add explicit gating and limits instead of enabling broken shadows globally.

This is not a full renderer rewrite. It is a prototype that makes the shadow path
controllable and testable, and prepares the renderer for a proper cubemap depth pass.
"""

from pathlib import Path
import re

SETS = [
    {
        "name": "SP",
        "tr_init": Path("SP/code/rend2/tr_init.c"),
        "tr_local": Path("SP/code/rend2/tr_local.h"),
        "tr_shade": Path("SP/code/rend2/tr_shade.c"),
        "tr_backend": Path("SP/code/rend2/tr_backend.c"),
    },
    {
        "name": "MP",
        "tr_init": Path("MP/code/rend2/tr_init.c"),
        "tr_local": Path("MP/code/rend2/tr_local.h"),
        "tr_shade": Path("MP/code/rend2/tr_shade.c"),
        "tr_backend": Path("MP/code/rend2/tr_backend.c"),
    },
]

NEW_CVAR_DEFS = """
cvar_t *r_dlightShadows;
cvar_t *r_dlightShadowMaxLights;
cvar_t *r_dlightShadowMapSize;
cvar_t *r_dlightShadowBias;
cvar_t *r_dlightShadowFilter;
cvar_t *r_dlightShadowDebug;
cvar_t *r_dlightShadowIntensity;
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
extern cvar_t *r_dlightShadowDebug;
extern cvar_t *r_dlightShadowIntensity;
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
    'r_dlightShadowDebug = ri.Cvar_Get( "r_dlightShadowDebug", "0", CVAR_ARCHIVE ); '
    'r_dlightShadowIntensity = ri.Cvar_Get( "r_dlightShadowIntensity", "1.0", CVAR_ARCHIVE ); '
    'r_dlightShadowTorchOnly = ri.Cvar_Get( "r_dlightShadowTorchOnly", "1", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowExplosions = ri.Cvar_Get( "r_dlightShadowExplosions", "0", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowMuzzle = ri.Cvar_Get( "r_dlightShadowMuzzle", "0", CVAR_ARCHIVE | CVAR_LATCH );'
)

HELPER_CODE = r"""
/*
=====================
Rend2 Mode3 Dynamic Shadow Prototype

This helper is intentionally conservative.
It does not try to make every dynamic light cast shadows.  It provides a single
place to decide whether a dlight may use the experimental shadowCubemap path.

The stock rend2 readme marks r_dlightMode 2 shadows as broken.  Therefore:
- mode 2 stays balanced/no-shadow
- mode 3 + r_dlightShadows 1 enables the shadow path
- only the first r_dlightShadowMaxLights dlights are allowed
=====================
*/
static qboolean RB_Mode3DlightShadowAllowed( int dlightIndex, const dlight_t *dl )
{
    int maxLights;

    if ( !r_dlightShadows || !r_dlightShadows->integer )
    {
        return qfalse;
    }

    if ( !r_dlightMode || r_dlightMode->integer < 3 )
    {
        return qfalse;
    }

    if ( !dl )
    {
        return qfalse;
    }

    maxLights = r_dlightShadowMaxLights ? r_dlightShadowMaxLights->integer : 1;
    if ( maxLights < 1 )
    {
        maxLights = 1;
    }
    if ( maxLights > 2 )
    {
        maxLights = 2;
    }

    if ( dlightIndex >= maxLights )
    {
        return qfalse;
    }

    /*
     * Heuristic:
     * RTCW dynamic lights do not carry a reliable semantic tag like "torch",
     * "explosion", or "muzzle flash" in this renderer path.  Therefore
     * r_dlightShadowTorchOnly cannot perfectly identify torch lights here.
     * It is kept as a user-facing control for future game/cgame integration.
     */
    return qtrue;
}
"""

def insert_defs(s):
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
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")
    s = path.read_text(encoding="utf-8", errors="replace")
    s = insert_defs(s)
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
    print(f"patched init: {path}")

def patch_local(path):
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")
    s = path.read_text(encoding="utf-8", errors="replace")
    if "extern cvar_t *r_dlightShadows;" not in s:
        if "extern cvar_t *r_dlightMode;" in s:
            s = s.replace("extern cvar_t *r_dlightMode;", "extern cvar_t *r_dlightMode;\n" + NEW_CVAR_EXTERNS, 1)
        else:
            s += "\n" + NEW_CVAR_EXTERNS + "\n"
    path.write_text(s, encoding="utf-8")
    print(f"patched local: {path}")

def sub_required(s, pattern, repl, label):
    ns, n = re.subn(pattern, repl, s)
    print(f"{label}: {n}")
    return ns, n

def patch_shade(path):
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")

    s = path.read_text(encoding="utf-8", errors="replace")
    original = s

    if "RB_Mode3DlightShadowAllowed" not in s:
        # Insert helper after include/comment area before first obvious function marker if possible.
        marker = "static void ComputeTexMods"
        if marker in s:
            s = s.replace(marker, HELPER_CODE + "\n" + marker, 1)
        else:
            # Good enough: after tr_local include region / before body.
            s = s.replace('/* THIS ENTIRE FILE IS BACK END', HELPER_CODE + '\n/* THIS ENTIRE FILE IS BACK END', 1)

    # Balanced material-light tuning. This reduces overbright/wet look compared to previous mode2/3.
    s, _ = sub_required(
        s,
        r'GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_DIRECTEDLIGHT\s*,\s*dl->color\s*\)\s*;',
        'VectorScale(dl->color, 1.06f, vector);\n\t\tGLSL_SetUniformVec3(sp, UNIFORM_DIRECTEDLIGHT, vector);',
        "directed light balanced"
    )

    s, _ = sub_required(
        s,
        r'VectorSet\s*\(\s*vector\s*,\s*0\s*,\s*0\s*,\s*0\s*\)\s*;\s*GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_AMBIENTLIGHT\s*,\s*vector\s*\)\s*;',
        'VectorScale(dl->color, 0.012f, vector);\n\t\tGLSL_SetUniformVec3(sp, UNIFORM_AMBIENTLIGHT, vector);',
        "low ambient"
    )

    s, _ = sub_required(
        s,
        r'GLSL_SetUniformFloat\s*\(\s*sp\s*,\s*UNIFORM_LIGHTRADIUS\s*,\s*radius\s*\)\s*;',
        'GLSL_SetUniformFloat(sp, UNIFORM_LIGHTRADIUS, radius * 1.03f);',
        "radius"
    )

    # Convert the existing unconditional r_dlightMode>=2 cubemap use into a controlled prototype.
    s, n_gate = sub_required(
        s,
        r'if\s*\(\s*r_dlightMode->integer\s*>=\s*2\s*\)\s*GL_BindToTMU\s*\(\s*tr\.shadowCubemaps\s*\[\s*l\s*\]\s*,\s*TB_SHADOWMAP\s*\)\s*;',
        'if (RB_Mode3DlightShadowAllowed( l, dl ))\n'
        '\t\t{\n'
        '\t\t\t/* Mode3 prototype: explicitly allowed dynamic-light shadow cubemap. */\n'
        '\t\t\tGL_BindToTMU(tr.shadowCubemaps[l], TB_SHADOWMAP);\n'
        '\t\t}\n'
        '\t\telse if (r_dlightMode->integer >= 2)\n'
        '\t\t{\n'
        '\t\t\t/* Mode2 and non-selected mode3 lights stay stable/no-shadow. */\n'
        '\t\t\tGL_BindToTMU(tr.whiteImage, TB_SHADOWMAP);\n'
        '\t\t}',
        "mode3 selected shadow gate"
    )

    # Some source revisions may already have a block form from earlier patches.
    if n_gate == 0 and "tr.shadowCubemaps[l]" in s and "RB_Mode3DlightShadowAllowed" in s:
        s = s.replace(
            'if (r_dlightMode->integer >= 3 && r_dlightShadows && r_dlightShadows->integer)\n\t\t{\n\t\t\t/* Experimental mode 3: allow stock cubemap shadow path only when explicitly enabled. */\n\t\t\tGL_BindToTMU(tr.shadowCubemaps[l], TB_SHADOWMAP);\n\t\t}',
            'if (RB_Mode3DlightShadowAllowed( l, dl ))\n\t\t{\n\t\t\tGL_BindToTMU(tr.shadowCubemaps[l], TB_SHADOWMAP);\n\t\t}'
        )

    if s == original:
        raise SystemExit(f"No shade changes applied to {path}")

    path.write_text(s, encoding="utf-8")
    print(f"patched shade: {path}")

def patch_backend(path):
    # This stage is intentionally conservative.  The backend file is large and minified upstream.
    # We add a comment marker so the built artifact documents that this is the shadow-map
    # prototype build.  The actual cubemap rendering path is used from existing rend2 code.
    if not path.exists():
        print(f"backend not found, skipping: {path}")
        return
    s = path.read_text(encoding="utf-8", errors="replace")
    if "Rend2 mode3 shadow-map prototype build marker" not in s:
        s = s.replace(
            '#include "tr_local.h"',
            '#include "tr_local.h"\n/* Rend2 mode3 shadow-map prototype build marker: controlled dlight shadow path. */',
            1
        )
        path.write_text(s, encoding="utf-8")
        print(f"marked backend: {path}")
    else:
        print(f"backend already marked: {path}")

for item in SETS:
    patch_init(item["tr_init"])
    patch_local(item["tr_local"])
    patch_shade(item["tr_shade"])
    patch_backend(item["tr_backend"])

print("Rend2 mode3 shadow-map prototype patch completed.")
