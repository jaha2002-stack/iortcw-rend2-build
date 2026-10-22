#!/usr/bin/env python3
"""Fix Android GLES3 fullscreen framebuffer/viewport mismatch, not Windows."""
from pathlib import Path
import sys

MARKER = "DARKWOLF_ANDROID_FULLSCREEN_DRAWABLE_V01"

def exactly_once(src: str, old: str, new: str, label: str) -> str:
    hits = src.count(old)
    if hits != 1:
        raise RuntimeError(f"{label}: expected one source anchor, got {hits}")
    return src.replace(old, new, 1)

def patch(src: str) -> str:
    # ioRTCW's stock GLimp_SetMode targets PC fullscreen exclusive modes.
    # On Android, force a fullscreen desktop window and skip video mode switches.
    src = exactly_once(
        src,
        '\tri.Printf( PRINT_ALL, "Initializing OpenGL display\\n");',
        '''#ifdef DARKWOLF_ANDROID_GLES
\t/* DARKWOLF_ANDROID_FULLSCREEN_DRAWABLE_V01:
\t * avoid PC-only modes and the 640x480 fallback on Android. */
\tmode = -2;
\tfullscreen = qtrue;
\tnoborder = qtrue;
#endif
\tri.Printf( PRINT_ALL, "Initializing OpenGL display\\n");''',
        "Android GL window startup"
    )
    src = exactly_once(
        src,
        "\tif( fullscreen )\n\t{\n\t\tflags |= SDL_WINDOW_FULLSCREEN;\n\t\tglConfig.isFullscreen = qtrue;",
        '''\tif( fullscreen )
\t{
#ifdef DARKWOLF_ANDROID_GLES
\t\tflags |= SDL_WINDOW_FULLSCREEN_DESKTOP;
#else
\t\tflags |= SDL_WINDOW_FULLSCREEN;
#endif
\t\tglConfig.isFullscreen = qtrue;''',
        "Android fullscreen window flags"
    )
    src = exactly_once(
        src,
        "\t\tif( fullscreen )\n\t\t{\n\t\t\tSDL_DisplayMode mode;",
        '''#ifndef DARKWOLF_ANDROID_GLES
\t\tif( fullscreen )
\t\t{
\t\t\tSDL_DisplayMode mode;''',
        "Android exclusive video mode begin"
    )
    src = exactly_once(
        src,
        "\t\tSDL_SetWindowIcon( SDL_window, icon );",
        '''#endif /* Android GLES: SDL owns device display; no exclusive video mode */
\t\tSDL_SetWindowIcon( SDL_window, icon );''',
        "Android exclusive video mode end"
    )
    src = exactly_once(
        src,
        "\t\tqglClearColor( 0, 0, 0, 1 );",
        '''#ifdef DARKWOLF_ANDROID_GLES
\t\t{
\t\t\tint windowWidth = 0, windowHeight = 0;
\t\t\tint drawableWidth = 0, drawableHeight = 0;
\t\t\tSDL_GetWindowSize(SDL_window, &windowWidth, &windowHeight);
\t\t\tSDL_GL_GetDrawableSize(SDL_window, &drawableWidth, &drawableHeight);
\t\t\tif (drawableWidth <= 0 || drawableHeight <= 0)
\t\t\t{
\t\t\t\tri.Printf(PRINT_ALL, "Android drawable invalid %dx%d: %s\\n",
\t\t\t\t\tdrawableWidth, drawableHeight, SDL_GetError());
\t\t\t\tSDL_GL_DeleteContext(SDL_glContext);
\t\t\t\tSDL_glContext = NULL;
\t\t\t\tSDL_DestroyWindow(SDL_window);
\t\t\t\tSDL_window = NULL;
\t\t\t\tcontinue;
\t\t\t}
\t\t\t/* Fullscreen renderer, FBO and viewport use physical GLES pixels.
\t\t\t * The SDL logical window size can differ on high-density phones. */
\t\t\tglConfig.vidWidth = drawableWidth;
\t\t\tglConfig.vidHeight = drawableHeight;
\t\t\tglConfig.windowAspect = (float)drawableWidth / drawableHeight;
\t\t\tri.Printf(PRINT_ALL,
\t\t\t\t"DARKWOLF_ANDROID_FULLSCREEN_DRAWABLE=PASS window=%dx%d drawable=%dx%d mode=%dx%d\\n",
\t\t\t\twindowWidth, windowHeight, drawableWidth, drawableHeight,
\t\t\t\tglConfig.vidWidth, glConfig.vidHeight);
\t\t}
#endif
\t\tqglClearColor( 0, 0, 0, 1 );''',
        "physical GLES3 drawable dimensions"
    )
    if src.count(MARKER) != 1:
        raise RuntimeError("fullscreen patch marker count != 1")
    return src

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_fullscreen.py <reconstructed-source-root>")
    root = Path(sys.argv[1])
    path = root / "SP/code/sdl/sdl_glimp.c"
    src = path.read_text()
    patched = patch(src)
    path.write_text(patched)
    print("GRAPHICS_LAB_FULLSCREEN_DRAWABLE_PATCH=PASS")

if __name__ == "__main__":
    main()
