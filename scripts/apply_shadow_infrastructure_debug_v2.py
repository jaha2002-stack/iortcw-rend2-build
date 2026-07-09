#!/usr/bin/env python3
"""
Rend2 Shadow Infrastructure Debug Kit v2

Fix over v1:
- v1 inserted debug code after every UNIFORM_LIGHTRADIUS usage.
- That accidentally hit ProjectPshadowVBOGLSL(), where l/dl/radius were not the same scope.
- v2 inserts debug only inside the dynamic-light shadowCubemap binding block,
  where l, dl, and radius are known to exist in ForwardDlight().
"""

from pathlib import Path
import re

SETS = [
    {
        "name": "SP",
        "tr_init": Path("SP/code/rend2/tr_init.c"),
        "tr_local": Path("SP/code/rend2/tr_local.h"),
        "tr_shade": Path("SP/code/rend2/tr_shade.c"),
    },
    {
        "name": "MP",
        "tr_init": Path("MP/code/rend2/tr_init.c"),
        "tr_local": Path("MP/code/rend2/tr_local.h"),
        "tr_shade": Path("MP/code/rend2/tr_shade.c"),
    },
]

NEW_CVAR_DEFS = """
cvar_t *r_dlightShadows;
cvar_t *r_dlightShadowMaxLights;
cvar_t *r_dlightShadowDebug;
cvar_t *r_dlightShadowDebugEvery;
cvar_t *r_dlightShadowMinRadius;
cvar_t *r_dlightShadowMinIntensity;
cvar_t *r_dlightShadowTorchOnly;
cvar_t *r_dlightShadowExplosions;
cvar_t *r_dlightShadowMuzzle;
"""

NEW_CVAR_EXTERNS = """
extern cvar_t *r_dlightShadows;
extern cvar_t *r_dlightShadowMaxLights;
extern cvar_t *r_dlightShadowDebug;
extern cvar_t *r_dlightShadowDebugEvery;
extern cvar_t *r_dlightShadowMinRadius;
extern cvar_t *r_dlightShadowMinIntensity;
extern cvar_t *r_dlightShadowTorchOnly;
extern cvar_t *r_dlightShadowExplosions;
extern cvar_t *r_dlightShadowMuzzle;
"""

REGISTER_SNIPPET = (
    'r_dlightShadows = ri.Cvar_Get( "r_dlightShadows", "0", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowMaxLights = ri.Cvar_Get( "r_dlightShadowMaxLights", "2", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowDebug = ri.Cvar_Get( "r_dlightShadowDebug", "0", CVAR_ARCHIVE ); '
    'r_dlightShadowDebugEvery = ri.Cvar_Get( "r_dlightShadowDebugEvery", "60", CVAR_ARCHIVE ); '
    'r_dlightShadowMinRadius = ri.Cvar_Get( "r_dlightShadowMinRadius", "32", CVAR_ARCHIVE ); '
    'r_dlightShadowMinIntensity = ri.Cvar_Get( "r_dlightShadowMinIntensity", "0.05", CVAR_ARCHIVE ); '
    'r_dlightShadowTorchOnly = ri.Cvar_Get( "r_dlightShadowTorchOnly", "0", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowExplosions = ri.Cvar_Get( "r_dlightShadowExplosions", "1", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowMuzzle = ri.Cvar_Get( "r_dlightShadowMuzzle", "1", CVAR_ARCHIVE | CVAR_LATCH );'
)

HELPER_CODE = r"""
/*
=====================
Rend2 Shadow Infrastructure Debug v2

Diagnostic only. Does not implement final shadow-map rendering.
Logs dynamic lights that reach the ForwardDlight shadow-cubemap binding point.
=====================
*/
static int rdbg_dlightPrintCounter = 0;

static float RB_DlightDebugIntensity( const dlight_t *dl )
{
    float r, g, b;

    if ( !dl )
    {
        return 0.0f;
    }

    r = dl->color[0];
    g = dl->color[1];
    b = dl->color[2];

    if ( r >= g && r >= b )
    {
        return r;
    }
    if ( g >= r && g >= b )
    {
        return g;
    }

    return b;
}

static qboolean RB_DlightDebugWouldSelect( int dlightIndex, const dlight_t *dl, float radius )
{
    int maxLights;
    float minRadius;
    float minIntensity;
    float intensity;

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

    maxLights = r_dlightShadowMaxLights ? r_dlightShadowMaxLights->integer : 2;
    if ( maxLights < 1 )
    {
        maxLights = 1;
    }
    if ( maxLights > 4 )
    {
        maxLights = 4;
    }

    minRadius = r_dlightShadowMinRadius ? r_dlightShadowMinRadius->value : 32.0f;
    minIntensity = r_dlightShadowMinIntensity ? r_dlightShadowMinIntensity->value : 0.05f;
    intensity = RB_DlightDebugIntensity( dl );

    if ( radius < minRadius )
    {
        return qfalse;
    }

    if ( intensity < minIntensity )
    {
        return qfalse;
    }

    if ( dlightIndex >= maxLights )
    {
        return qfalse;
    }

    return qtrue;
}

static void RB_DlightDebugPrint( int dlightIndex, const dlight_t *dl, float radius, qboolean selected )
{
    int every;
    float intensity;

    if ( !r_dlightShadowDebug || !r_dlightShadowDebug->integer )
    {
        return;
    }

    every = r_dlightShadowDebugEvery ? r_dlightShadowDebugEvery->integer : 60;
    if ( every < 1 )
    {
        every = 1;
    }

    rdbg_dlightPrintCounter++;

    if ( r_dlightShadowDebug->integer < 2 && ( rdbg_dlightPrintCounter % every ) != 0 )
    {
        return;
    }

    intensity = RB_DlightDebugIntensity( dl );

    ri.Printf( PRINT_ALL,
        "DLIGHTDBG index=%d selected=%d origin=(%.1f %.1f %.1f) radius=%.1f color=(%.3f %.3f %.3f) intensity=%.3f mode=%d shadows=%d max=%d\\n",
        dlightIndex,
        selected ? 1 : 0,
        dl ? dl->origin[0] : 0.0f,
        dl ? dl->origin[1] : 0.0f,
        dl ? dl->origin[2] : 0.0f,
        radius,
        dl ? dl->color[0] : 0.0f,
        dl ? dl->color[1] : 0.0f,
        dl ? dl->color[2] : 0.0f,
        intensity,
        r_dlightMode ? r_dlightMode->integer : -1,
        r_dlightShadows ? r_dlightShadows->integer : -1,
        r_dlightShadowMaxLights ? r_dlightShadowMaxLights->integer : -1
    );
}
"""

def insert_defs(s):
    if "cvar_t *r_dlightShadowDebug;" in s:
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
    s = insert_defs(s)
    if 'ri.Cvar_Get( "r_dlightShadowDebug"' not in s:
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
    s = path.read_text(encoding="utf-8", errors="replace")
    if "extern cvar_t *r_dlightShadowDebug;" not in s:
        if "extern cvar_t *r_dlightMode;" in s:
            s = s.replace("extern cvar_t *r_dlightMode;", "extern cvar_t *r_dlightMode;\n" + NEW_CVAR_EXTERNS, 1)
        else:
            s += "\n" + NEW_CVAR_EXTERNS + "\n"
    path.write_text(s, encoding="utf-8")
    print(f"patched header: {path}")

def patch_shade(path):
    s = path.read_text(encoding="utf-8", errors="replace")
    original = s

    if "RB_DlightDebugWouldSelect" not in s:
        marker = "static void ComputeTexMods"
        if marker in s:
            s = s.replace(marker, HELPER_CODE + "\n" + marker, 1)
        else:
            s = s.replace('/* THIS ENTIRE FILE IS BACK END', HELPER_CODE + '\n/* THIS ENTIRE FILE IS BACK END', 1)

    # Replace only the specific dynamic-light cubemap binding. This location has l, dl, radius in scope.
    replacement = (
        'if (r_dlightMode->integer >= 2)\n'
        '\t\t{\n'
        '\t\t\tqboolean rdbg_selected = RB_DlightDebugWouldSelect( l, dl, radius );\n'
        '\t\t\tRB_DlightDebugPrint( l, dl, radius, rdbg_selected );\n'
        '\t\t\tif (rdbg_selected)\n'
        '\t\t\t{\n'
        '\t\t\t\tGL_BindToTMU(tr.shadowCubemaps[l], TB_SHADOWMAP);\n'
        '\t\t\t}\n'
        '\t\t\telse\n'
        '\t\t\t{\n'
        '\t\t\t\tGL_BindToTMU(tr.whiteImage, TB_SHADOWMAP);\n'
        '\t\t\t}\n'
        '\t\t}'
    )

    s, n = re.subn(
        r'if\s*\(\s*r_dlightMode->integer\s*>=\s*2\s*\)\s*GL_BindToTMU\s*\(\s*tr\.shadowCubemaps\s*\[\s*l\s*\]\s*,\s*TB_SHADOWMAP\s*\)\s*;',
        replacement,
        s
    )
    print(f"dynamic-light cubemap debug replacement: {n}")

    if n == 0:
        raise SystemExit("Could not find original dynamic-light shadowCubemap binding pattern in tr_shade.c")

    if s == original:
        raise SystemExit(f"No shade changes applied to {path}")

    path.write_text(s, encoding="utf-8")
    print(f"patched shade: {path}")

for item in SETS:
    patch_init(item["tr_init"])
    patch_local(item["tr_local"])
    patch_shade(item["tr_shade"])

print("Rend2 Shadow Infrastructure Debug v2 patch completed.")
