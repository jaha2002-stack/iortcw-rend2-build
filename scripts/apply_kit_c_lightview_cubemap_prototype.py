#!/usr/bin/env python3
"""
Kit C: Rend2 true light-view cubemap prototype v1

This kit builds on the successful Kit A and Kit B findings:

Kit A proved:
- torch/fire dynamic lights reach ForwardDlight
- selected=1 works

Kit B proved:
- backend cubemap pass is called
- face 0..5 rendered=1 loop works

Kit C goal:
- Stop using the current player camera/view for the cubemap depth pass.
- For each selected dlight, temporarily switch backend view/projection to a
  point-light cubemap face:
    face 0 +X
    face 1 -X
    face 2 +Y
    face 3 -Y
    face 4 +Z
    face 5 -Z
- Render depth from dl->origin with 90 degree projection.
- Restore the original player view state afterwards.

This is still a prototype.  It is the first real attempt at light-view cubemap
matrices inside the renderer backend.
"""

from pathlib import Path
import re

SETS = [
    {"name": "SP", "tr_init": Path("SP/code/rend2/tr_init.c"), "tr_local": Path("SP/code/rend2/tr_local.h"), "tr_shade": Path("SP/code/rend2/tr_shade.c"), "tr_backend": Path("SP/code/rend2/tr_backend.c")},
    {"name": "MP", "tr_init": Path("MP/code/rend2/tr_init.c"), "tr_local": Path("MP/code/rend2/tr_local.h"), "tr_shade": Path("MP/code/rend2/tr_shade.c"), "tr_backend": Path("MP/code/rend2/tr_backend.c")},
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
cvar_t *r_dlightShadowUseLightView;
cvar_t *r_dlightShadowNear;
cvar_t *r_dlightShadowFarScale;
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
extern cvar_t *r_dlightShadowUseLightView;
extern cvar_t *r_dlightShadowNear;
extern cvar_t *r_dlightShadowFarScale;
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
    'r_dlightShadowUseLightView = ri.Cvar_Get( "r_dlightShadowUseLightView", "1", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowNear = ri.Cvar_Get( "r_dlightShadowNear", "2.0", CVAR_ARCHIVE | CVAR_LATCH ); '
    'r_dlightShadowFarScale = ri.Cvar_Get( "r_dlightShadowFarScale", "1.0", CVAR_ARCHIVE | CVAR_LATCH );'
)

BACKEND_HELPER = r"""
/*
=====================
Rend2 Kit C: true point-light cubemap view prototype

Differences from Kit B:
- Kit B rendered cubemap faces, but still used the current camera pipeline.
- Kit C temporarily replaces backend matrices with a 90-degree view from dl->origin.

This is still not final.  The next step may need shader-side depth linearization and
bias compare correction if shadows do not appear after light-view matrices are active.
=====================
*/
static qboolean r_mode3DlightShadowDepthPassActive = qfalse;
static int r_mode3DlightShadowDepthPrintCounter = 0;

void RB_RenderDrawSurfList( drawSurf_t *drawSurfs, int numDrawSurfs );

static void RB_Mode3Perspective90( float znear, float zfar, mat4_t out )
{
    float f;

    if ( znear < 0.1f )
    {
        znear = 0.1f;
    }

    if ( zfar < znear + 1.0f )
    {
        zfar = znear + 1.0f;
    }

    /*
     * OpenGL-style 90 degree perspective.  f = cot(fov/2) = 1 for 90 degrees.
     * This is intentionally local to Kit C to avoid depending on any engine
     * projection helper whose argument conventions may differ.
     */
    f = 1.0f;

    Mat4Zero( out );
    out[0] = f;
    out[5] = f;
    out[10] = -( zfar + znear ) / ( zfar - znear );
    out[11] = -1.0f;
    out[14] = -( 2.0f * zfar * znear ) / ( zfar - znear );
}

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

    minRadius = r_dlightShadowMinRadius ? r_dlightShadowMinRadius->value : 32.0f;
    minIntensity = r_dlightShadowMinIntensity ? r_dlightShadowMinIntensity->value : 0.05f;

    if ( dl->radius < minRadius )
    {
        return qfalse;
    }

    if ( RB_Mode3DlightIntensity( dl ) < minIntensity )
    {
        return qfalse;
    }

    return qtrue;
}

static void RB_Mode3CubeFaceAxes( int face, vec3_t axes[3] )
{
    /*
     * Engine convention:
     * axes[0] = forward
     * axes[1] = left
     * axes[2] = up
     *
     * The exact handedness may still require adjustment, but these are real
     * per-face light views rather than the player's current camera.
     */
    switch ( face )
    {
        default:
        case 0: /* +X */
            VectorSet( axes[0],  1,  0,  0 );
            VectorSet( axes[1],  0,  1,  0 );
            VectorSet( axes[2],  0,  0,  1 );
            break;

        case 1: /* -X */
            VectorSet( axes[0], -1,  0,  0 );
            VectorSet( axes[1],  0, -1,  0 );
            VectorSet( axes[2],  0,  0,  1 );
            break;

        case 2: /* +Y */
            VectorSet( axes[0],  0,  1,  0 );
            VectorSet( axes[1], -1,  0,  0 );
            VectorSet( axes[2],  0,  0,  1 );
            break;

        case 3: /* -Y */
            VectorSet( axes[0],  0, -1,  0 );
            VectorSet( axes[1],  1,  0,  0 );
            VectorSet( axes[2],  0,  0,  1 );
            break;

        case 4: /* +Z */
            VectorSet( axes[0],  0,  0,  1 );
            VectorSet( axes[1],  0,  1,  0 );
            VectorSet( axes[2], -1,  0,  0 );
            break;

        case 5: /* -Z */
            VectorSet( axes[0],  0,  0, -1 );
            VectorSet( axes[1],  0,  1,  0 );
            VectorSet( axes[2],  1,  0,  0 );
            break;
    }
}

static void RB_Mode3SetupLightViewForFace( const dlight_t *dl, int face, int size )
{
    vec3_t axes[3];
    mat4_t projection;
    float znear;
    float zfar;

    if ( !dl )
    {
        return;
    }

    RB_Mode3CubeFaceAxes( face, axes );

    znear = r_dlightShadowNear ? r_dlightShadowNear->value : 2.0f;
    zfar = dl->radius * ( r_dlightShadowFarScale ? r_dlightShadowFarScale->value : 1.0f );

    if ( zfar < 64.0f )
    {
        zfar = 64.0f;
    }

    VectorCopy( dl->origin, backEnd.viewParms.or.origin );
    VectorCopy( dl->origin, backEnd.viewParms.world.origin );

    VectorCopy( axes[0], backEnd.viewParms.or.axis[0] );
    VectorCopy( axes[1], backEnd.viewParms.or.axis[1] );
    VectorCopy( axes[2], backEnd.viewParms.or.axis[2] );

    VectorCopy( axes[0], backEnd.viewParms.world.axis[0] );
    VectorCopy( axes[1], backEnd.viewParms.world.axis[1] );
    VectorCopy( axes[2], backEnd.viewParms.world.axis[2] );

    Mat4View( axes, dl->origin, backEnd.viewParms.world.modelMatrix );
    Mat4View( axes, dl->origin, backEnd.viewParms.or.modelMatrix );

    RB_Mode3Perspective90( znear, zfar, projection );
    Mat4Copy( projection, backEnd.viewParms.projectionMatrix );

    backEnd.viewParms.viewportX = 0;
    backEnd.viewParms.viewportY = 0;
    backEnd.viewParms.viewportWidth = size;
    backEnd.viewParms.viewportHeight = size;

    backEnd.or = backEnd.viewParms.world;

    GL_SetProjectionMatrix( backEnd.viewParms.projectionMatrix );
    GL_SetModelviewMatrix( backEnd.viewParms.world.modelMatrix );

    qglViewport( 0, 0, size, size );
    qglScissor( 0, 0, size, size );
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
        "CUBEVIEWDBG light=%d face=%d rendered=%d origin=(%.1f %.1f %.1f) radius=%.1f color=(%.3f %.3f %.3f) size=%d lightView=%d mode=%d shadows=%d\\n",
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
        r_dlightShadowUseLightView ? r_dlightShadowUseLightView->integer : -1,
        r_dlightMode ? r_dlightMode->integer : -1,
        r_dlightShadows ? r_dlightShadows->integer : -1
    );
}

static void RB_Mode3RenderDlightShadowCubemapDepthPass( drawSurf_t *drawSurfs, int numDrawSurfs )
{
    FBO_t *oldFbo;
    viewParms_t oldViewParms;
    orientationr_t oldOr;
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
    oldViewParms = backEnd.viewParms;
    oldOr = backEnd.or;

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
            FBO_AttachImage( tr.renderCubeFbo, tr.shadowCubemaps[lightIndex], GL_DEPTH_ATTACHMENT_EXT, face );

            if ( r_dlightShadowUseLightView && r_dlightShadowUseLightView->integer )
            {
                RB_Mode3SetupLightViewForFace( dl, face, size );
            }
            else
            {
                qglViewport( 0, 0, size, size );
                qglScissor( 0, 0, size, size );
            }

            qglColorMask( GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE );
            qglClear( GL_DEPTH_BUFFER_BIT );

            RB_RenderDrawSurfList( drawSurfs, numDrawSurfs );

            qglColorMask( GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE );

            RB_Mode3PrintDepthPass( lightIndex, face, dl, qtrue );

            /*
             * Restore after every face so any backend code that assumes current
             * player view state does not leak into the next pass unexpectedly.
             */
            backEnd.viewParms = oldViewParms;
            backEnd.or = oldOr;
            GL_SetProjectionMatrix( backEnd.viewParms.projectionMatrix );
            GL_SetModelviewMatrix( backEnd.viewParms.world.modelMatrix );
        }
    }

    backEnd.depthFill = oldDepthFill;
    r_mode3DlightShadowDepthPassActive = qfalse;

    backEnd.viewParms = oldViewParms;
    backEnd.or = oldOr;

    FBO_Bind( oldFbo );
    GL_SetProjectionMatrix( backEnd.viewParms.projectionMatrix );
    GL_SetModelviewMatrix( backEnd.viewParms.world.modelMatrix );
    SetViewportAndScissor();
}
"""

SHADE_HELPER = r"""
/*
=====================
Rend2 Kit C shader-side dlight shadow selection
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
    if "cvar_t *r_dlightShadowUseLightView;" in s:
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

    if 'ri.Cvar_Get( "r_dlightShadowUseLightView"' not in s:
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

    if "extern cvar_t *r_dlightShadowUseLightView;" not in s:
        if "extern cvar_t *r_dlightMode;" in s:
            s = s.replace("extern cvar_t *r_dlightMode;", "extern cvar_t *r_dlightMode;\n" + NEW_CVAR_EXTERNS, 1)
        else:
            s += "\n" + NEW_CVAR_EXTERNS + "\n"

    path.write_text(s, encoding="utf-8")
    print(f"patched local: {path}")

def patch_backend(path):
    s = path.read_text(encoding="utf-8", errors="replace")
    original = s

    if "RB_Mode3SetupLightViewForFace" not in s:
        marker = "void RB_RenderDrawSurfList( drawSurf_t *drawSurfs, int numDrawSurfs )"
        if marker not in s:
            raise SystemExit(f"Could not find RB_RenderDrawSurfList marker in {path}")
        s = s.replace(marker, BACKEND_HELPER + "\n" + marker, 1)

    call = "if ( !r_mode3DlightShadowDepthPassActive )\n\t{\n\t\tRB_Mode3RenderDlightShadowCubemapDepthPass( drawSurfs, numDrawSurfs );\n\t}\n"

    if "RB_Mode3RenderDlightShadowCubemapDepthPass( drawSurfs, numDrawSurfs )" not in s.split("void RB_RenderDrawSurfList",1)[1][:1500]:
        s = s.replace(
            "void RB_RenderDrawSurfList( drawSurf_t *drawSurfs, int numDrawSurfs ) {",
            "void RB_RenderDrawSurfList( drawSurf_t *drawSurfs, int numDrawSurfs ) {\n\t" + call,
            1
        )

    if s != original:
        path.write_text(s, encoding="utf-8")
        print(f"patched backend: {path}")
    else:
        print(f"backend unchanged/already patched: {path}")

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

print("Kit C light-view cubemap prototype patch completed.")
