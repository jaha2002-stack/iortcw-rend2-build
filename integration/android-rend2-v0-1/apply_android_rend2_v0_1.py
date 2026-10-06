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
    patch_tr_extensions(sp / "rend2" / "tr_extensions.c")
    print(f"{MARKER}: patched Android GLES3 bring-up layer")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_android_rend2_v0_1.py <iortcw-source-root>")
    main(Path(sys.argv[1]).resolve())
