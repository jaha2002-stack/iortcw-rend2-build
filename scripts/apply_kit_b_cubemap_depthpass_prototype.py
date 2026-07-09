#!/usr/bin/env python3
"""
Kit B: Rend2 real cubemap depth-pass prototype v1

Goal:
- Move beyond cvar toggles/debug.
- Add an actual backend-side depth pass hook for selected dynamic lights.
- For each selected dlight, attach tr.shadowCubemaps[i] to a cube FBO face and render a depth-fill pass.
- Keep r_dlightMode 2 stable/no-shadow.
- Use r_dlightMode 3 + r_dlightShadows 1 for experimental cubemap shadows.

Important:
This is a prototype.  It wires a real FBO/depth render pass into the backend, but it still
uses rend2's existing renderer draw-list and shadowCubemap path.  The next iteration may need
proper light-facing matrices per cube face if the current renderer path does not already handle it.
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
cvar_t *r_dlightShadowDebugEvery;
cvar_t *r_dlightShadowMinRadius;
cvar_t *r_dlightShadowMinIntensity;
cvar_t *r_dlightShadowDepthPass;
cvar_t *r_dlightShadowDepthFaces;
cvar_t *r_dlightShadowDepthCurrentView;
"""

NEW_CVAR_EXTERNS = """
extern cvar_t *r_dlightShadows;
extern cvar_t *r_dlightShadowMaxLights;
extern cvar_t *r_dlightShadowMapSize;
extern cvar_t *r_dlightShadowBias;
extern cvar_t *r_dlightShadowFilter;
extern cvar_t *r_dlightShadowDebug;
extern cvar_t *r_dlightShadowDebugEvery;
extern cvar_t *r_dlightShadowMinRadius;
extern cvar_t *r_dlightShadowMinIntensity;
extern cvar_t *r_dlightShadowDepthPass;
extern cvar_t *r_dlightShadowDepthFaces;
extern cvar_t *r_dlightShadowDepthCurrentView;
"""

REGISTER_SNIPPET = (
    'r_dlightShadows = ri.Cvar_Get( "r_dlightShadows", "0", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowMaxLights = ri.Cvar_Get( "r_dlightShadowMaxLights", "1", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowMapSize = ri.Cvar_Get( "r_dlightShadowMapSize", "256", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowBias = ri.Cvar_Get( "r_dlightShadowBias", "0.006", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowFilter = ri.Cvar_Get( "r_dlightShadowFilter", "0", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowDebug = ri.Cvar_Get( "r_dlightShadowDebug", "1", CVAR_ARCHIVE ); '
    'r_dlightShadowDebugEvery = ri.Cvar_Get( "r_dlightShadowDebugEvery", "60", CVAR_ARCHIVE ); '
    'r_dlightShadowMinRadius = ri.Cvar_Get( "r_dlightShadowMinRadius", "32", CVAR_ARCHIVE ); '
    'r_dlightShadowMinIntensity = ri.Cvar_Get( "r_dlightShadowMinIntensity", "0.05", CVAR_ARCHIVE ); '
    'r_dlightShadowDepthPass = ri.Cvar_Get( "r_dlightShadowDepthPass", "1", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowDepthFaces = ri.Cvar_Get( "r_dlightShadowDepthFaces", "6", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowDepthCurrentView = ri.Cvar_Get( "r_dlightShadowDepthCurrentView", "1", CVAR_ARCHIVE | CVAR_LATCH );'
)

BACKEND_HELPER = r"""
/*
=====================
Rend2 Kit B: dynamic light cubemap depth-pass prototype

This is the first backend-side prototype.  It intentionally limits itself to 1-2
selected dynamic lights and small cubemap sizes.

The pass attaches tr.shadowCubemaps[lightIndex] to tr.renderCubeFbo face-by-face,
clears depth, and renders the drawSurf list in depthFill mode.

Prototype limitation:
This v1 uses the current backend drawSurf pipeline.  If shadows appear in the wrong
direction or do not appear, the next kit must add true point-light cube-face view
matrices before the depth-fill draw call.
=====================
*/
static qboolean r_mode3DlightShadowDepthPassActive = qfalse;
static int r_mode3DlightShadowDepthPrintCounter = 0;

void RB_RenderDrawSurfList( drawSurf_t *drawSurfs, int numDrawSurfs );

static float RB_Mode3DlightIntensity( const dlight_t *dl )
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

static qboolean RB_Mode3DlightSelectedForDepthPass( int dlightIndex, const dlight_t *dl )
{
    int maxLights;
    float minRadius;
    float minIntensity;
    float intensity;
    float radius;

    if ( !r_dlightMode || r_dlightMode->integer < 3 )
    {
        return qfalse;
    }

    if ( !r_dlightShadows || !r_dlightShadows->integer )
    {
        return qfalse;
    }

    if ( !r_dlightShadowDepthPass || !r_dlightShadowDepthPass->integer )
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

    radius = dl->radius;
    minRadius = r_dlightShadowMinRadius ? r_dlightShadowMinRadius->value : 32.0f;
    minIntensity = r_dlightShadowMinIntensity ? r_dlightShadowMinIntensity->value : 0.05f;
    intensity = RB_Mode3DlightIntensity( dl );

    if ( radius < minRadius )
    {
        return qfalse;
    }

    if ( intensity < minIntensity )
    {
        return qfalse;
    }

    return qtrue;
}

static void RB_Mode3PrintDepthPass( int lightIndex, int face, const dlight_t *dl, qboolean rendered )
{
    int every;

    if ( !r_dlightShadowDebug || !r_dlightShadowDebug->integer )
    {
        return;
    }

    every = r_dlightShadowDebugEvery ? r_dlightShadowDebugEvery->integer : 60;
    if ( every < 1 )
    {
        every = 1;
    }

    r_mode3DlightShadowDepthPrintCounter++;
    if ( r_dlightShadowDebug->integer < 2 && ( r_mode3DlightShadowDepthPrintCounter % every ) != 0 )
    {
        return;
    }

    ri.Printf( PRINT_ALL,
        "CUBEPASSDBG light=%d face=%d rendered=%d origin=(%.1f %.1f %.1f) radius=%.1f color=(%.3f %.3f %.3f) size=%d mode=%d shadows=%d\\n",
        lightIndex,
        face,
        rendered ? 1 : 0,
        dl ? dl->origin[0] : 0.0f,
        dl ? dl->origin[1] : 0.0f,
        dl ? dl->origin[2] : 0.0f,
        dl ? dl->radius : 0.0f,
        dl ? dl->color[0] : 0.0f,
        dl ? dl->color[1] : 0.0f,
        dl ? dl->color[2] : 0.0f,
        r_dlightShadowMapSize ? r_dlightShadowMapSize->integer : -1,
        r_dlightMode ? r_dlightMode->integer : -1,
        r_dlightShadows ? r_dlightShadows->integer : -1
    );
}

static void RB_Mode3RenderDlightShadowCubemapDepthPass( drawSurf_t *drawSurfs, int numDrawSurfs )
{
    FBO_t *oldFbo;
    int lightIndex;
    int maxLights;
    int faces;
    int face;
    int size;
    qboolean oldDepthFill;

    if ( r_mode3DlightShadowDepthPassActive )
    {
        return;
    }

    if ( !glRefConfig.framebufferObject )
    {
        return;
    }

    if ( !tr.renderCubeFbo )
    {
        return;
    }

    if ( !backEnd.refdef.num_dlights )
    {
        return;
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

    faces = r_dlightShadowDepthFaces ? r_dlightShadowDepthFaces->integer : 6;
    if ( faces < 1 )
    {
        faces = 1;
    }
    if ( faces > 6 )
    {
        faces = 6;
    }

    size = r_dlightShadowMapSize ? r_dlightShadowMapSize->integer : 256;
    if ( size < 64 )
    {
        size = 64;
    }
    if ( size > 1024 )
    {
        size = 1024;
    }

    oldFbo = glState.currentFBO;
    oldDepthFill = backEnd.depthFill;

    r_mode3DlightShadowDepthPassActive = qtrue;
    backEnd.depthFill = qtrue;

    for ( lightIndex = 0; lightIndex < backEnd.refdef.num_dlights && lightIndex < maxLights; lightIndex++ )
    {
        dlight_t *dl = &backEnd.refdef.dlights[lightIndex];

        if ( !RB_Mode3DlightSelectedForDepthPass( lightIndex, dl ) )
        {
            continue;
        }

        if ( !tr.shadowCubemaps[lightIndex] )
        {
            RB_Mode3PrintDepthPass( lightIndex, -1, dl, qfalse );
            continue;
        }

        for ( face = 0; face < faces; face++ )
        {
            FBO_Bind( tr.renderCubeFbo );

            /*
             * Attach the selected shadow cubemap face as a depth target.
             * This is the core of Kit B.  If the target format in the current
             * renderer build is not depth-capable, the debug log will still show
             * that the pass was attempted and the next kit must adjust allocation.
             */
            FBO_AttachImage( tr.renderCubeFbo, tr.shadowCubemaps[lightIndex], GL_DEPTH_ATTACHMENT_EXT, face );

            qglViewport( 0, 0, size, size );
            qglScissor( 0, 0, size, size );
            qglColorMask( GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE );
            qglClear( GL_DEPTH_BUFFER_BIT );

            /*
             * Prototype v1 depth fill.
             * This draws the same visible drawSurf list into the cubemap face.
             * Next version must replace current-view matrices with true light-face matrices.
             */
            RB_RenderDrawSurfList( drawSurfs, numDrawSurfs );

            qglColorMask( GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE );

            RB_Mode3PrintDepthPass( lightIndex, face, dl, qtrue );
        }
    }

    backEnd.depthFill = oldDepthFill;
    r_mode3DlightShadowDepthPassActive = qfalse;

    FBO_Bind( oldFbo );
    SetViewportAndScissor();
}
"""

SHADE_HELPER = r"""
/*
=====================
Rend2 Kit B shadow selection for shader path
=====================
*/
static float RB_Mode3ShadeDlightIntensity( const dlight_t *dl )
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

static qboolean RB_Mode3ShadeDlightSelected( int dlightIndex, const dlight_t *dl, float radius )
{
    int maxLights;
    float minRadius;
    float minIntensity;

    if ( !r_dlightMode || r_dlightMode->integer < 3 )
    {
        return qfalse;
    }

    if ( !r_dlightShadows || !r_dlightShadows->integer )
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

    minRadius = r_dlightShadowMinRadius ? r_dlightShadowMinRadius->value : 32.0f;
    minIntensity = r_dlightShadowMinIntensity ? r_dlightShadowMinIntensity->value : 0.05f;

    if ( radius < minRadius )
    {
        return qfalse;
    }

    if ( RB_Mode3ShadeDlightIntensity( dl ) < minIntensity )
    {
        return qfalse;
    }

    return qtrue;
}
"""

def insert_defs(s):
    if "cvar_t *r_dlightShadowDepthPass;" in s:
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
    if 'ri.Cvar_Get( "r_dlightShadowDepthPass"' not in s:
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
    if "extern cvar_t *r_dlightShadowDepthPass;" not in s:
        if "extern cvar_t *r_dlightMode;" in s:
            s = s.replace("extern cvar_t *r_dlightMode;", "extern cvar_t *r_dlightMode;\n" + NEW_CVAR_EXTERNS, 1)
        else:
            s += "\n" + NEW_CVAR_EXTERNS + "\n"
    path.write_text(s, encoding="utf-8")
    print(f"patched local: {path}")

def patch_backend(path):
    s = path.read_text(encoding="utf-8", errors="replace")
    original = s

    if "RB_Mode3RenderDlightShadowCubemapDepthPass" not in s:
        marker = "void RB_RenderDrawSurfList( drawSurf_t *drawSurfs, int numDrawSurfs )"
        if marker not in s:
            raise SystemExit(f"Could not find RB_RenderDrawSurfList marker in {path}")
        s = s.replace(marker, BACKEND_HELPER + "\n" + marker, 1)

    call = "if ( !r_mode3DlightShadowDepthPassActive )\n\t{\n\t\tRB_Mode3RenderDlightShadowCubemapDepthPass( drawSurfs, numDrawSurfs );\n\t}\n"
    if "RB_Mode3RenderDlightShadowCubemapDepthPass( drawSurfs, numDrawSurfs )" not in s.split("void RB_RenderDrawSurfList",1)[1][:1000]:
        s = s.replace(
            "void RB_RenderDrawSurfList( drawSurf_t *drawSurfs, int numDrawSurfs ) {",
            "void RB_RenderDrawSurfList( drawSurf_t *drawSurfs, int numDrawSurfs ) {\n\t" + call,
            1
        )

    if s == original:
        print(f"backend already patched or unchanged: {path}")
    else:
        path.write_text(s, encoding="utf-8")
        print(f"patched backend: {path}")

def patch_shade(path):
    s = path.read_text(encoding="utf-8", errors="replace")
    original = s

    if "RB_Mode3ShadeDlightSelected" not in s:
        marker = "static void ComputeTexMods"
        if marker in s:
            s = s.replace(marker, SHADE_HELPER + "\n" + marker, 1)
        else:
            s = s.replace('/* THIS ENTIRE FILE IS BACK END', SHADE_HELPER + '\n/* THIS ENTIRE FILE IS BACK END', 1)

    replacement = (
        'if (RB_Mode3ShadeDlightSelected( l, dl, radius ))\n'
        '\t\t{\n'
        '\t\t\tGL_BindToTMU(tr.shadowCubemaps[l], TB_SHADOWMAP);\n'
        '\t\t}\n'
        '\t\telse if (r_dlightMode->integer >= 2)\n'
        '\t\t{\n'
        '\t\t\tGL_BindToTMU(tr.whiteImage, TB_SHADOWMAP);\n'
        '\t\t}'
    )

    s, n = re.subn(
        r'if\s*\(\s*r_dlightMode->integer\s*>=\s*2\s*\)\s*GL_BindToTMU\s*\(\s*tr\.shadowCubemaps\s*\[\s*l\s*\]\s*,\s*TB_SHADOWMAP\s*\)\s*;',
        replacement,
        s
    )
    print(f"shade cubemap bind replacement: {n}")

    # Balanced dynamic light tuning; avoid wet/overbright look.
    s, n1 = re.subn(
        r'GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_DIRECTEDLIGHT\s*,\s*dl->color\s*\)\s*;',
        'VectorScale(dl->color, 1.03f, vector);\n\t\tGLSL_SetUniformVec3(sp, UNIFORM_DIRECTEDLIGHT, vector);',
        s
    )
    print(f"shade directed balance replacements: {n1}")

    s, n2 = re.subn(
        r'VectorSet\s*\(\s*vector\s*,\s*0\s*,\s*0\s*,\s*0\s*\)\s*;\s*GLSL_SetUniformVec3\s*\(\s*sp\s*,\s*UNIFORM_AMBIENTLIGHT\s*,\s*vector\s*\)\s*;',
        'VectorScale(dl->color, 0.010f, vector);\n\t\tGLSL_SetUniformVec3(sp, UNIFORM_AMBIENTLIGHT, vector);',
        s
    )
    print(f"shade ambient balance replacements: {n2}")

    if s == original:
        raise SystemExit(f"No shade changes applied to {path}")

    path.write_text(s, encoding="utf-8")
    print(f"patched shade: {path}")

for item in SETS:
    patch_init(item["tr_init"])
    patch_local(item["tr_local"])
    patch_backend(item["tr_backend"])
    patch_shade(item["tr_shade"])

print("Kit B cubemap depth-pass prototype patch completed.")
