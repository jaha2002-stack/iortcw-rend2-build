#!/usr/bin/env python3
from pathlib import Path
import sys

MARKER = "DARKWOLF_ANDROID_REND2_V01"

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"{label}: anchor not found")
    return text.replace(old, new, 1)

def patch_qgl(path: Path) -> None:
    s = path.read_text()
    old = '''#ifdef USE_LOCAL_HEADERS
#\tinclude "SDL_opengl.h"
#else
#\tinclude <SDL_opengl.h>
#endif
'''
    new = f'''/* {MARKER}: Android Rend2 uses GLES3 headers, never desktop GL headers. */
#if defined(DARKWOLF_ANDROID_GLES)
# include <GLES3/gl3.h>
# include <GLES3/gl3ext.h>
/* Keep the shared desktop/GLES qgl ABI source-compatible on Android. */
#ifndef APIENTRY
# define APIENTRY GL_APIENTRY
#endif
#ifndef APIENTRYP
# define APIENTRYP GL_APIENTRYP
#endif
typedef double GLdouble;
typedef double GLclampd;

/* Desktop ARB/EXT tokens used by Rend2 source, mapped to GLES3 equivalents. */
#ifndef GL_COLOR_ATTACHMENT0_EXT
# define GL_COLOR_ATTACHMENT0_EXT GL_COLOR_ATTACHMENT0
#endif
#ifndef GL_TEXTURE_CUBE_MAP_POSITIVE_X_ARB
# define GL_TEXTURE_CUBE_MAP_POSITIVE_X_ARB GL_TEXTURE_CUBE_MAP_POSITIVE_X
#endif
#ifndef GL_DEPTH_COMPONENT16_ARB
# define GL_DEPTH_COMPONENT16_ARB GL_DEPTH_COMPONENT16
#endif
#ifndef GL_DEPTH_COMPONENT24_ARB
# define GL_DEPTH_COMPONENT24_ARB GL_DEPTH_COMPONENT24
#endif
#ifndef GL_DEPTH_COMPONENT32_ARB
# define GL_DEPTH_COMPONENT32_ARB 0x81A7
#endif
#ifndef GL_FRAMEBUFFER_INCOMPLETE_DRAW_BUFFER
# define GL_FRAMEBUFFER_INCOMPLETE_DRAW_BUFFER 0x8CDB
#endif
#ifndef GL_FRAMEBUFFER_INCOMPLETE_READ_BUFFER
# define GL_FRAMEBUFFER_INCOMPLETE_READ_BUFFER 0x8CDC
#endif
#ifndef GL_STENCIL_INDEX
# define GL_STENCIL_INDEX 0x1901
#endif
#ifndef GL_STENCIL_INDEX1
# define GL_STENCIL_INDEX1 0x8D46
#endif
#ifndef GL_STENCIL_INDEX4
# define GL_STENCIL_INDEX4 0x8D47
#endif
#ifndef GL_STENCIL_INDEX16
# define GL_STENCIL_INDEX16 0x8D49
#endif
#ifndef GL_LINE
# define GL_LINE 0x1B01
#endif
#ifndef GL_FILL
# define GL_FILL 0x1B02
#endif
#ifndef GL_SAMPLES_PASSED
# define GL_SAMPLES_PASSED GL_ANY_SAMPLES_PASSED
#endif
/* Legacy enums kept as source metadata; actual GLES-safe texture formats
 * are translated separately before texture allocation/upload. */
#ifndef GL_EYE_PLANE
# define GL_EYE_PLANE 0x2502
#endif
#ifndef GL_BACK_LEFT
# define GL_BACK_LEFT 0x0402
#endif
#ifndef GL_BACK_RIGHT
# define GL_BACK_RIGHT 0x0403
#endif
#ifndef GL_STACK_OVERFLOW
# define GL_STACK_OVERFLOW 0x0503
#endif
#ifndef GL_STACK_UNDERFLOW
# define GL_STACK_UNDERFLOW 0x0504
#endif
#ifndef GL_EXP
# define GL_EXP 0x0800
#endif
#ifndef GL_DEPTH_TEXTURE_MODE
/* Legacy desktop token, referenced only by the renderer's < GL3 fallback. */
# define GL_DEPTH_TEXTURE_MODE 0x884B
#endif
#ifndef GL_COMPARE_R_TO_TEXTURE
/* GLES3 renamed the desktop comparison mode token. */
# define GL_COMPARE_R_TO_TEXTURE GL_COMPARE_REF_TO_TEXTURE
#endif
#ifndef GL_RGBA16
# define GL_RGBA16 0x805B
#endif
#ifndef GL_RGB5
# define GL_RGB5 0x8050
#endif
#ifndef GL_LUMINANCE8
# define GL_LUMINANCE8 0x8040
#endif
#ifndef GL_LUMINANCE8_ALPHA8
# define GL_LUMINANCE8_ALPHA8 0x8045
#endif
#ifndef GL_DEPTH_COMPONENT32
# define GL_DEPTH_COMPONENT32 0x81A7
#endif
#ifndef GL_SRGB_EXT
# define GL_SRGB_EXT 0x8C40
#endif
#ifndef GL_SRGB8_EXT
# define GL_SRGB8_EXT GL_SRGB8
#endif
#ifndef GL_SRGB_ALPHA_EXT
# define GL_SRGB_ALPHA_EXT 0x8C42
#endif
#ifndef GL_SRGB8_ALPHA8_EXT
# define GL_SRGB8_ALPHA8_EXT GL_SRGB8_ALPHA8
#endif
#ifndef GL_SLUMINANCE_EXT
# define GL_SLUMINANCE_EXT 0x8C46
#endif
#ifndef GL_SLUMINANCE8_EXT
# define GL_SLUMINANCE8_EXT 0x8C47
#endif
#ifndef GL_SLUMINANCE_ALPHA_EXT
# define GL_SLUMINANCE_ALPHA_EXT 0x8C44
#endif
#ifndef GL_SLUMINANCE8_ALPHA8_EXT
# define GL_SLUMINANCE8_ALPHA8_EXT 0x8C45
#endif
#ifndef GL_COMPRESSED_SRGB_S3TC_DXT1_EXT
# define GL_COMPRESSED_SRGB_S3TC_DXT1_EXT 0x8C4C
#endif
#ifndef GL_COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT
# define GL_COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT 0x8C4D
#endif
#ifndef GL_COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT
# define GL_COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT 0x8C4E
#endif
#ifndef GL_COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT
# define GL_COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT 0x8C4F
#endif
#else
#ifdef USE_LOCAL_HEADERS
# include "SDL_opengl.h"
#else
# include <SDL_opengl.h>
#endif
#endif
'''
    s = replace_once(s, old, new, "qgl include")
    path.write_text(s)

def patch_glimp(path: Path) -> None:
    s = path.read_text()
    old = '''#ifdef USE_OPENGLES
\t\tSDL_GL_SetAttribute( SDL_GL_CONTEXT_MAJOR_VERSION, 1 );
#endif
'''
    new = f'''#ifdef USE_OPENGLES
# ifdef DARKWOLF_ANDROID_GLES
\t\t/* {MARKER}: Rend2 needs programmable GLES3, not the legacy ES1 context. */
\t\tSDL_GL_SetAttribute( SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES );
\t\tSDL_GL_SetAttribute( SDL_GL_CONTEXT_MAJOR_VERSION, 3 );
\t\tSDL_GL_SetAttribute( SDL_GL_CONTEXT_MINOR_VERSION, 0 );
# else
\t\tSDL_GL_SetAttribute( SDL_GL_CONTEXT_MAJOR_VERSION, 1 );
# endif
#endif
'''
    s = replace_once(s, old, new, "glimp first ES context")
    old2 = '''#ifdef USE_OPENGLES
\t\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
\t\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 1);
\t\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
#endif

\t\tif (!fixedFunction)
'''
    new2 = f'''#ifdef USE_OPENGLES
\t\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
# ifdef DARKWOLF_ANDROID_GLES
\t\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
\t\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
# else
\t\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 1);
\t\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
# endif
#endif

\t\tif (!fixedFunction)
'''
    s = replace_once(s, old2, new2, "glimp second ES context")

    old3 = '''\t\tif (!fixedFunction)
\t\t{
\t\t\tint profileMask, majorVersion, minorVersion;
'''
    new3 = f'''\t\tif (!fixedFunction)
\t\t{{
#ifdef DARKWOLF_ANDROID_GLES
\t\t\t/* {MARKER}: SDL already owns a GLES3 context request on Android. */
\t\t\tif ((SDL_glContext = SDL_GL_CreateContext(SDL_window)) != NULL)
\t\t\t{{
\t\t\t\tif (!GLimp_GetProcAddresses(fixedFunction))
\t\t\t\t{{
\t\t\t\t\tGLimp_ClearProcAddresses();
\t\t\t\t\tSDL_GL_DeleteContext(SDL_glContext);
\t\t\t\t\tSDL_glContext = NULL;
\t\t\t\t}}
\t\t\t}}
#else
\t\t\tint profileMask, majorVersion, minorVersion;
'''
    s = replace_once(s, old3, new3, "glimp desktop context begin")
    old4 = '''\t\t\t}
\t\t}
\t\telse
\t\t{
\t\t\tSDL_glContext = NULL;
\t\t}
'''
    new4 = '''\t\t\t}
#endif
\t\t}
\t\telse
\t\t{
\t\t\tSDL_glContext = NULL;
\t\t}
'''
    # anchor occurs near end of the desktop-context block.
    idx = s.find(old4, s.find(MARKER))
    if idx < 0:
        raise SystemExit("glimp desktop context end: anchor not found")
    s = s[:idx] + new4 + s[idx+len(old4):]

    old5 = '''\t\t} else if ( QGLES_VERSION_ATLEAST( 2, 0 ) ) {
\t\t\tQGL_1_1_PROCS;
\t\t\tQGL_ES_1_1_PROCS;
\t\t\tQGL_1_3_PROCS;
\t\t\tQGL_1_5_PROCS;
\t\t\tQGL_2_0_PROCS;
\t\t\t// error so this doesn't segfault due to NULL desktop GL functions being used
\t\t\tCom_Error( ERR_FATAL, "Unsupported OpenGL Version: %s", version );
'''
    new5 = f'''\t\t}} else if ( QGLES_VERSION_ATLEAST( 3, 0 ) ) {{
\t\t\t/* {MARKER}: Rend2 programmable path on GLES3. */
\t\t\tQGL_1_1_PROCS;
\t\t\tQGL_ES_1_1_PROCS;
\t\t\tQGL_1_3_PROCS;
\t\t\tQGL_1_5_PROCS;
\t\t\tQGL_2_0_PROCS;
\t\t\t/* Desktop entry points still referenced by shared Rend2 code. */
\t\t\tqglClearDepth = GLimp_GLES_ClearDepth;
\t\t\tqglDepthRange = GLimp_GLES_DepthRange;
\t\t\tqglDrawBuffer = GLimp_GLES_DrawBuffer;
\t\t\tqglPolygonMode = GLimp_GLES_PolygonMode;
'''
    s = replace_once(s, old5, new5, "glimp GLES3 proc gate")
    path.write_text(s)

def patch_glsl(path: Path) -> None:
    s = path.read_text()
    anchor = '''\tdest[0] = '\\0';

\t// HACK: abuse the GLSL preprocessor to turn GLSL 1.20 shaders into 1.30 ones
'''
    new = f'''\tdest[0] = '\\0';

#ifdef DARKWOLF_ANDROID_GLES
\t/* {MARKER}: translate the existing Rend2 shader body to GLSL ES 3.00. */
\tQ_strcat(dest, size, "#version 300 es\\n");
\tQ_strcat(dest, size, "precision highp float;\\nprecision highp int;\\n");
\tif(shaderType == GL_VERTEX_SHADER)
\t{{
\t\tQ_strcat(dest, size, "#define attribute in\\n");
\t\tQ_strcat(dest, size, "#define varying out\\n");
\t}}
\telse
\t{{
\t\tQ_strcat(dest, size, "#define varying in\\n");
\t\tQ_strcat(dest, size, "out vec4 out_Color;\\n");
\t\tQ_strcat(dest, size, "#define gl_FragColor out_Color\\n");
\t\tQ_strcat(dest, size, "#define texture2D texture\\n");
\t\tQ_strcat(dest, size, "#define textureCubeLod textureLod\\n");
\t\tQ_strcat(dest, size, "#define shadow2D(a,b) texture(a,b)\\n");
\t}}
#else
\t// HACK: abuse the GLSL preprocessor to turn GLSL 1.20 shaders into 1.30 ones
'''
    s = replace_once(s, anchor, new, "GLSL header start")
    end_anchor = '''\t\tQ_strcat(dest, size, "#version 120\\n");
\t\tQ_strcat(dest, size, "#define shadow2D(a,b) shadow2D(a,b).r \\n");
\t}

\t// HACK: add some macros to avoid extra uniforms and save speed and code maintenance
'''
    end_new = '''\t\tQ_strcat(dest, size, "#version 120\\n");
\t\tQ_strcat(dest, size, "#define shadow2D(a,b) shadow2D(a,b).r \\n");
\t}
#endif

\t// HACK: add some macros to avoid extra uniforms and save speed and code maintenance
'''
    s = replace_once(s, end_anchor, end_new, "GLSL header end")
    path.write_text(s)

def patch_gles_shader_literals(path: Path) -> None:
    s = path.read_text()

    # GLSL ES 3.x (notably Qualcomm Adreno) rejects implicit int -> float
    # conversions that desktop GLSL drivers commonly accept. Keep this patch
    # idempotent because reconstructed v4.4.6 may already contain some fixes.
    replacements = (
        ("float zDeformScale = 0;", "float zDeformScale = 0.0;"),
        ("if (frequency < 0)", "if (frequency < 0.0)"),
        ("zDeformScale = 1;", "zDeformScale = 1.0;"),
        ("frequency *= -1;", "frequency *= -1.0;"),
        ("if (frequency > 999)", "if (frequency > 999.0)"),
        ("frequency -= 999;", "frequency -= 999.0;"),
        ("zDeformScale = -1;", "zDeformScale = -1.0;"),
        ("if (zDeformScale != 0)", "if (zDeformScale != 0.0)"),
        ("if (nDot * scale > 0)", "if (nDot * scale > 0.0)"),
        ("color.a = 0;", "color.a = 0.0;"),
    )
    for old, new in replacements:
        s = s.replace(old, new)

    forbidden = (
        "float zDeformScale = 0;",
        "if (frequency < 0)",
        "zDeformScale = 1;",
        "frequency *= -1;",
        "if (frequency > 999)",
        "frequency -= 999;",
        "zDeformScale = -1;",
        "if (zDeformScale != 0)",
        "if (nDot * scale > 0)",
        "color.a = 0;",
    )
    remaining = [token for token in forbidden if token in s]
    if remaining:
        raise SystemExit("generic_vp strict-float rewrite incomplete: " + ", ".join(remaining))

    path.write_text(s)

def patch_tr_image(path: Path) -> None:
    s = path.read_text()

    helper_anchor = '''static GLenum PixelDataFormatFromInternalFormat(GLenum internalFormat)
{
'''
    helper = f'''#ifdef DARKWOLF_ANDROID_GLES
/*
 * {MARKER}: desktop Rend2 allocates texture storage with glTexImage2D(NULL)
 * and relies on desktop GL to convert loosely-matched internal/external
 * format+type combinations. GLES3 validates these combinations strictly.
 *
 * Keep source uploads RGBA-compatible and canonicalize legacy/unsized desktop
 * formats to sized GLES3 storage formats. Render/depth/float/compressed formats
 * that are already GLES3-valid are preserved.
 */
static GLenum AndroidGLES_TextureStorageFormat(GLenum internalFormat)
{{
    switch (internalFormat)
    {{
        case GL_RGB:
        case GL_RGB8:
        case GL_RGB5:
        case GL_RGBA:
        case GL_RGBA4:
            return GL_RGBA8;

        case GL_SRGB_EXT:
        case GL_SRGB8_EXT:
        case GL_SRGB_ALPHA_EXT:
            return GL_SRGB8_ALPHA8;

        case GL_LUMINANCE:
        case GL_LUMINANCE8:
        case GL_LUMINANCE_ALPHA:
        case GL_LUMINANCE8_ALPHA8:
        case GL_SLUMINANCE_EXT:
        case GL_SLUMINANCE8_EXT:
        case GL_SLUMINANCE_ALPHA_EXT:
        case GL_SLUMINANCE8_ALPHA8_EXT:
            /* Legacy luminance paths are disabled in current Rend2, but keep
             * a valid sampled-color fallback instead of illegal ES tokens. */
            return GL_RGBA8;

        case GL_DEPTH_COMPONENT:
            return GL_DEPTH_COMPONENT24;

        case GL_DEPTH_COMPONENT32_ARB:
            return GL_DEPTH_COMPONENT32F;

        default:
            return internalFormat;
    }}
}}
#endif

static GLenum PixelDataFormatFromInternalFormat(GLenum internalFormat)
{{
'''
    if helper not in s:
        if helper_anchor not in s:
            raise SystemExit("tr_image helper anchor not found")
        s = s.replace(helper_anchor, helper, 1)

    format_anchor = '''\tif (!internalFormat)
\t\tinternalFormat = RawImage_GetFormat(pic, width * height, picFormat, isLightmap, image->type, image->flags);

\timage->internalFormat = internalFormat;
'''
    format_new = f'''\tif (!internalFormat)
\t\tinternalFormat = RawImage_GetFormat(pic, width * height, picFormat, isLightmap, image->type, image->flags);

#ifdef DARKWOLF_ANDROID_GLES
\t/* {MARKER}: canonical storage format must be chosen before both allocation
\t * and later subimage upload bookkeeping. */
\tinternalFormat = AndroidGLES_TextureStorageFormat(internalFormat);
#endif
\timage->internalFormat = internalFormat;
'''
    s = replace_once(s, format_anchor, format_new, "tr_image storage format normalization")

    alloc_anchor = '''\t// Allocate texture storage so we don't have to worry about it later.
\tdataFormat = PixelDataFormatFromInternalFormat(internalFormat);
\tmipWidth = width;
\tmipHeight = height;
\tmiplevel = 0;
\tdo
\t{
\t\tlastMip = !mipmap || (mipWidth == 1 && mipHeight == 1);
\t\tif (cubemap)
\t\t{
\t\t\tint i;

\t\t\tfor (i = 0; i < 6; i++)
\t\t\t\tqglTextureImage2DEXT(image->texnum, GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, miplevel, internalFormat, mipWidth, mipHeight, 0, dataFormat, GL_UNSIGNED_BYTE, NULL);
\t\t}
\t\telse
\t\t{
\t\t\tqglTextureImage2DEXT(image->texnum, GL_TEXTURE_2D, miplevel, internalFormat, mipWidth, mipHeight, 0, dataFormat, GL_UNSIGNED_BYTE, NULL);
\t\t}

\t\tmipWidth  = MAX(1, mipWidth >> 1);
\t\tmipHeight = MAX(1, mipHeight >> 1);
\t\tmiplevel++;
\t}
\twhile (!lastMip);
'''
    alloc_new = f'''\t// Allocate texture storage so we don't have to worry about it later.
\tdataFormat = PixelDataFormatFromInternalFormat(internalFormat);
#ifdef DARKWOLF_ANDROID_GLES
\t{{
\t\tint storageLevels = 1;
\t\tint storageWidth = width;
\t\tint storageHeight = height;

\t\tif (mipmap)
\t\t{{
\t\t\twhile (storageWidth > 1 || storageHeight > 1)
\t\t\t{{
\t\t\t\tstorageWidth = MAX(1, storageWidth >> 1);
\t\t\t\tstorageHeight = MAX(1, storageHeight >> 1);
\t\t\t\tstorageLevels++;
\t\t\t}}
\t\t}}

\t\t/*
\t\t * {MARKER}: GLES3 immutable storage is the correct allocation primitive.
\t\t * It accepts sized color/float/depth/compressed internal formats without
\t\t * inventing an external format/type pair. The existing upload path then
\t\t * uses TexSubImage2D/CompressedTexSubImage2D against valid storage.
\t\t */
\t\tGL_BindMultiTexture(GL_TEXTURE0, textureTarget, image->texnum);
\t\tglTexStorage2D(textureTarget, storageLevels, internalFormat, width, height);
\t\tGL_CheckErrors();
\t}}
#else
\tmipWidth = width;
\tmipHeight = height;
\tmiplevel = 0;
\tdo
\t{{
\t\tlastMip = !mipmap || (mipWidth == 1 && mipHeight == 1);
\t\tif (cubemap)
\t\t{{
\t\t\tint i;

\t\t\tfor (i = 0; i < 6; i++)
\t\t\t\tqglTextureImage2DEXT(image->texnum, GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, miplevel, internalFormat, mipWidth, mipHeight, 0, dataFormat, GL_UNSIGNED_BYTE, NULL);
\t\t}}
\t\telse
\t\t{{
\t\t\tqglTextureImage2DEXT(image->texnum, GL_TEXTURE_2D, miplevel, internalFormat, mipWidth, mipHeight, 0, dataFormat, GL_UNSIGNED_BYTE, NULL);
\t\t}}

\t\tmipWidth  = MAX(1, mipWidth >> 1);
\t\tmipHeight = MAX(1, mipHeight >> 1);
\t\tmiplevel++;
\t}}
\twhile (!lastMip);
#endif
'''
    s = replace_once(s, alloc_anchor, alloc_new, "tr_image GLES3 immutable texture storage")
    path.write_text(s)

def patch_depth_texture_mode(path: Path) -> None:
    s = path.read_text()
    old = '''\t\t\tif ( !QGL_VERSION_ATLEAST( 3, 0 ) ) {
\t\t\t\tqglTextureParameterfEXT(image->texnum, textureTarget, GL_DEPTH_TEXTURE_MODE, GL_LUMINANCE);
\t\t\t}
'''
    new = f'''\t\t\tif ( !QGL_VERSION_ATLEAST( 3, 0 ) && !QGLES_VERSION_ATLEAST( 3, 0 ) ) {{
\t\t\t\tqglTextureParameterfEXT(image->texnum, textureTarget, GL_DEPTH_TEXTURE_MODE, GL_LUMINANCE);
\t\t\t}}
'''
    s = replace_once(s, old, new, "depth texture mode GLES3 guard")
    path.write_text(s)

def patch_backend(path: Path) -> None:
    s = path.read_text()

    # Guard every inherited fixed-function fog disable. Do this line-by-line
    # instead of with a regex so tabs and legacy inline comments cannot evade
    # the Android GLES3 patch.
    needle = "qglDisable( GL_FOG );"
    lines = s.splitlines(keepends=True)
    out = []
    patched = 0

    for line in lines:
        if needle not in line:
            out.append(line)
            continue

        before, after = line.split(needle, 1)
        newline = "\n" if line.endswith("\n") else ""
        suffix = after[:-1] if newline else after
        out.append(before + "#ifndef DARKWOLF_ANDROID_GLES\n")
        out.append(before + needle + suffix + "\n")
        out.append(before + "#else\n")
        out.append(before + f"/* {MARKER}: fixed-function fog state does not exist in GLES3. */\n")
        out.append(before + "#endif" + newline)
        patched += 1

    if patched < 1:
        raise SystemExit("backend fixed-function fog: no GL_FOG disable sites found")

    s = "".join(out)

    # Every original call must now be immediately protected by an Android guard.
    unguarded = 0
    scan = s.splitlines()
    for i, line in enumerate(scan):
        if needle in line:
            prev = scan[i - 1].strip() if i > 0 else ""
            if prev != "#ifndef DARKWOLF_ANDROID_GLES":
                unguarded += 1
    if unguarded:
        raise SystemExit(f"backend fixed-function fog: {unguarded} unguarded sites remain")

    path.write_text(s)

def patch_android_console(path: Path) -> None:
    s = path.read_text()

    include_old = '#include <stdio.h>\n'
    include_new = f'''#include <stdio.h>
#ifdef __ANDROID__
#include <android/log.h>
#endif
'''
    s = replace_once(s, include_old, include_new, "Android console log include")

    print_old = '''void CON_Print( const char *msg )
{
\tif( com_ansiColor && com_ansiColor->integer )
\t\tSys_AnsiColorPrint( msg );
\telse
\t\tfputs( msg, stderr );
}
'''
    print_new = f'''void CON_Print( const char *msg )
{{
#ifdef __ANDROID__
\t/* {MARKER}: make Com_Printf visible to pid-scoped Android logcat. */
\t__android_log_write(ANDROID_LOG_INFO, "DarkWolfEngine", msg);
#endif
\tif( com_ansiColor && com_ansiColor->integer )
\t\tSys_AnsiColorPrint( msg );
\telse
\t\tfputs( msg, stderr );
}}
'''
    s = replace_once(s, print_old, print_new, "Android console log forwarding")
    path.write_text(s)

def patch_ci_playerstart(path: Path) -> None:
    s = path.read_text()

    old = '''\t// init for this gamestate
\t// use the lastExecutedServerCommand instead of the serverCommandSequence
\t// otherwise server commands sent just before a gamestate are dropped
\tVM_Call( cgvm, CG_INIT, clc.serverMessageSequence, clc.lastExecutedServerCommand, clc.clientNum );

\t// reset any CVAR_CHEAT cvars registered by cgame
'''
    new = f'''\t// init for this gamestate
\t// use the lastExecutedServerCommand instead of the serverCommandSequence
\t// otherwise server commands sent just before a gamestate are dropped
\tVM_Call( cgvm, CG_INIT, clc.serverMessageSequence, clc.lastExecutedServerCommand, clc.clientNum );

#ifdef __ANDROID__
\t/*
\t * {MARKER}: CI-only deterministic transition from SP briefing to live
\t * gameplay. The hook is inert in the ARM64 phone APK unless the explicit
\t * test cvar is supplied by the x86_64 TestLab launcher.
\t */
\tif ( Cvar_VariableIntegerValue( "dw_android_ci_playerstart" ) ) {{
\t\tif ( uivm ) {{
\t\t\tVM_Call( uivm, UI_SET_ACTIVE_MENU, UIMENU_NONE );
\t\t}}
\t\tKey_SetCatcher( Key_GetCatcher() & ~KEYCATCH_UI );
\t\tCvar_Set( "cl_paused", "0" );
\t\tCvar_Set( "g_playerstart", "1" );
\t\tCom_Printf( "DARKWOLF_ANDROID_CI_PLAYERSTART=PASS\\n" );
\t}}
#endif

\t// reset any CVAR_CHEAT cvars registered by cgame
'''
    s = replace_once(s, old, new, "CI playerstart hook")

    popup_old = '''\tcase CG_INGAME_POPUP:
\t\tif ( VMA( 1 ) && !Q_stricmp( VMA( 1 ), "briefing" ) ) {  //----(SA) added
\t\t\tVM_Call( uivm, UI_SET_ACTIVE_MENU, UIMENU_BRIEFING );
\t\t\treturn 0;
\t\t}
'''
    popup_new = f'''\tcase CG_INGAME_POPUP:
\t\tif ( VMA( 1 ) && !Q_stricmp( VMA( 1 ), "briefing" ) ) {{  //----(SA) added
#ifdef __ANDROID__
\t\t\tif ( Cvar_VariableIntegerValue( "dw_android_ci_playerstart" ) ) {{
\t\t\t\t/* {MARKER}: cgame posts briefing after CG_INIT; suppress only
\t\t\t\t * in the x86_64 TestLab opt-in so 3D evidence is deterministic. */
\t\t\t\tVM_Call( uivm, UI_SET_ACTIVE_MENU, UIMENU_NONE );
\t\t\t\tKey_SetCatcher( Key_GetCatcher() & ~KEYCATCH_UI );
\t\t\t\tCvar_Set( "cl_paused", "0" );
\t\t\t\tCvar_Set( "g_playerstart", "1" );
\t\t\t\tCom_Printf( "DARKWOLF_ANDROID_CI_BRIEFING_SUPPRESSED=PASS\\n" );
\t\t\t\treturn 0;
\t\t\t}}
#endif
\t\t\tVM_Call( uivm, UI_SET_ACTIVE_MENU, UIMENU_BRIEFING );
\t\t\treturn 0;
\t\t}}
'''
    s = replace_once(s, popup_old, popup_new, "CI briefing popup suppression")
    path.write_text(s)

def patch_tr_extensions(path: Path) -> None:
    s = path.read_text()
    old = '''\tq_gl_version_at_least_3_0 = QGL_VERSION_ATLEAST( 3, 0 );
\tq_gl_version_at_least_3_2 = QGL_VERSION_ATLEAST( 3, 2 );
'''
    new = f'''#ifdef DARKWOLF_ANDROID_GLES
\t/* {MARKER}: core GLES3 supplies FBO/VAO; desktop-only 3.2 features stay disabled. */
\tq_gl_version_at_least_3_0 = QGLES_VERSION_ATLEAST( 3, 0 );
\tq_gl_version_at_least_3_2 = qfalse;
#else
\tq_gl_version_at_least_3_0 = QGL_VERSION_ATLEAST( 3, 0 );
\tq_gl_version_at_least_3_2 = QGL_VERSION_ATLEAST( 3, 2 );
#endif
'''
    s = replace_once(s, old, new, "extension version gate")
    path.write_text(s)

def main(root: Path) -> None:
    sp = root / "SP" / "code"
    patch_qgl(sp / "rend2" / "qgl.h")
    patch_glimp(sp / "sdl" / "sdl_glimp.c")
    patch_glsl(sp / "rend2" / "tr_glsl.c")
    patch_gles_shader_literals(sp / "rend2" / "glsl" / "generic_vp.glsl")
    patch_tr_image(sp / "rend2" / "tr_image.c")
    patch_depth_texture_mode(sp / "rend2" / "tr_image.c")
    patch_backend(sp / "rend2" / "tr_backend.c")
    patch_tr_extensions(sp / "rend2" / "tr_extensions.c")
    patch_android_console(sp / "sys" / "con_passive.c")
    patch_ci_playerstart(sp / "client" / "cl_cgame.c")
    print(f"{MARKER}: patched Android GLES3 bring-up layer")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_android_rend2_v0_1.py <iortcw-source-root>")
    main(Path(sys.argv[1]).resolve())
