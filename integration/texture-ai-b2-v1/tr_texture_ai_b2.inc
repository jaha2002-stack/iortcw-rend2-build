/* DARKWOLF_TEXTURE_AI_B2_V1
 * Real local neural restoration for one selected BSP diffuse texture.
 * Backend: Real-ESRGAN x4plus portable ncnn/Vulkan. No Internet at runtime.
 */
#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#define DWTR_AI_MODEL "realesrgan-x4plus"
#define DWTR_AI_TIMEOUT_MS 180000

static void DWTRAI_Slashes(char *s)
{
    if (!s) return;
    while (*s) {
        if (*s == '/') *s = '\\';
        ++s;
    }
}

static const char *DWTRAI_GameDir(void)
{
    cvar_t *cv = ri.Cvar_Get("fs_game", "", 0);
    if (cv && cv->string && cv->string[0]) return cv->string;
    return "Main";
}

static const char *DWTRAI_CvarString(const char *name)
{
    cvar_t *cv = ri.Cvar_Get(name, "", 0);
    if (cv && cv->string) return cv->string;
    return "";
}

static void DWTRAI_PhysicalPath(char *out, int outSize, const char *root,
                                const char *game, const char *qpath)
{
    Com_sprintf(out, outSize, "%s\\%s\\%s", root, game, qpath);
    DWTRAI_Slashes(out);
}

#ifdef _WIN32
static qboolean DWTRAI_IsFile(const char *path)
{
    DWORD a = GetFileAttributesA(path);
    return (a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY)) ? qtrue : qfalse;
}
#endif

static qboolean DWTRAI_FindBackend(char *exe, int exeSize,
                                   char *models, int modelsSize,
                                   char *workDir, int workDirSize)
{
#ifdef _WIN32
    const char *game = DWTRAI_GameDir();
    const char *base = DWTRAI_CvarString("fs_basepath");
    const char *home = DWTRAI_CvarString("fs_homepath");
    char candidate[MAX_OSPATH * 2];
    char modelParam[MAX_OSPATH * 2];
    char modelBin[MAX_OSPATH * 2];

    if (!home[0]) home = base;
    if (!base[0]) base = home;
    if (!home[0] || !base[0]) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2: fs_basepath/fs_homepath unavailable.\n");
        return qfalse;
    }

    DWTRAI_PhysicalPath(candidate, sizeof(candidate), base, game,
                        "dw_ai\\realesrgan-ncnn-vulkan.exe");
    if (!DWTRAI_IsFile(candidate)) {
        DWTRAI_PhysicalPath(candidate, sizeof(candidate), home, game,
                            "dw_ai\\realesrgan-ncnn-vulkan.exe");
    }
    if (!DWTRAI_IsFile(candidate)) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2: backend missing. Expected %s\\%s\\dw_ai\\realesrgan-ncnn-vulkan.exe\n",
                  base, game);
        return qfalse;
    }
    Q_strncpyz(exe, candidate, exeSize);

    DWTRAI_PhysicalPath(models, modelsSize,
                        strstr(candidate, home) == candidate ? home : base,
                        game, "dw_ai\\models");
    Com_sprintf(modelParam, sizeof(modelParam), "%s\\%s.param", models, DWTR_AI_MODEL);
    Com_sprintf(modelBin, sizeof(modelBin), "%s\\%s.bin", models, DWTR_AI_MODEL);
    if (!DWTRAI_IsFile(modelParam) || !DWTRAI_IsFile(modelBin)) {
        /* If substring heuristic was fooled by similar roots, try base explicitly. */
        DWTRAI_PhysicalPath(models, modelsSize, base, game, "dw_ai\\models");
        Com_sprintf(modelParam, sizeof(modelParam), "%s\\%s.param", models, DWTR_AI_MODEL);
        Com_sprintf(modelBin, sizeof(modelBin), "%s\\%s.bin", models, DWTR_AI_MODEL);
    }
    if (!DWTRAI_IsFile(modelParam) || !DWTRAI_IsFile(modelBin)) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2: %s model files are missing in %s.\n",
                  DWTR_AI_MODEL, models);
        return qfalse;
    }

    DWTRAI_PhysicalPath(workDir, workDirSize, home, game, "texture_restoration");
    return qtrue;
#else
    ri.Printf(PRINT_WARNING, "DWTR AI B2: this test backend is Win64-only.\n");
    return qfalse;
#endif
}

#ifdef _WIN32
static qboolean DWTRAI_RunProcess(const char *exe, const char *models,
                                  const char *input, const char *output)
{
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    DWORD waitResult, exitCode = 0;
    char cmd[8192];
    char working[MAX_OSPATH * 2];
    char *slash;

    Q_strncpyz(working, exe, sizeof(working));
    slash = strrchr(working, '\\');
    if (slash) *slash = '\0';

    Com_Memset(&si, 0, sizeof(si));
    Com_Memset(&pi, 0, sizeof(pi));
    si.cb = sizeof(si);

    Com_sprintf(cmd, sizeof(cmd),
                "\"%s\" -i \"%s\" -o \"%s\" -s 4 -t 0 -m \"%s\" -n %s -f png",
                exe, input, output, models, DWTR_AI_MODEL);

    ri.Printf(PRINT_ALL, "DWTR AI B2: local neural inference started (%s, x4).\n",
              DWTR_AI_MODEL);

    if (!CreateProcessA(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW,
                        NULL, working[0] ? working : NULL, &si, &pi)) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2: CreateProcess failed, winerr=%lu.\n",
                  (unsigned long)GetLastError());
        return qfalse;
    }

    waitResult = WaitForSingleObject(pi.hProcess, DWTR_AI_TIMEOUT_MS);
    if (waitResult == WAIT_TIMEOUT) {
        TerminateProcess(pi.hProcess, 124);
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        ri.Printf(PRINT_WARNING, "DWTR AI B2: inference timed out.\n");
        return qfalse;
    }
    if (waitResult != WAIT_OBJECT_0 || !GetExitCodeProcess(pi.hProcess, &exitCode)) {
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        ri.Printf(PRINT_WARNING, "DWTR AI B2: cannot obtain backend result.\n");
        return qfalse;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);

    if (exitCode != 0) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2: Real-ESRGAN exited with code %lu. Check Vulkan support.\n",
                  (unsigned long)exitCode);
        return qfalse;
    }
    return qtrue;
}
#endif

static qboolean DWTRAI_OriginalToJPG(image_t *source, const char *qpath,
                                     int *sourceWidth, int *sourceHeight)
{
    byte *pic = NULL, *rgb = NULL;
    int width = 0, height = 0, mips = 0, i;
    GLenum fmt = GL_RGBA8;

    R_LoadImage(source->imgName, &pic, &width, &height, &fmt, &mips);
    if (!pic || width <= 0 || height <= 0) {
        if (pic) ri.Free(pic);
        ri.Printf(PRINT_WARNING, "DWTR AI B2: cannot read %s.\n", source->imgName);
        return qfalse;
    }
    if (fmt != GL_RGBA8 && fmt != GL_SRGB8_ALPHA8_EXT) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2: compressed/non-RGBA source is not supported in V1.\n");
        ri.Free(pic);
        return qfalse;
    }

    for (i = 0; i < width * height; ++i) {
        if (pic[i * 4 + 3] < 250) {
            ri.Printf(PRINT_WARNING,
                      "DWTR AI B2: alpha/cutout texture refused in V1 (%s).\n",
                      source->imgName);
            ri.Free(pic);
            return qfalse;
        }
    }

    rgb = (byte *)ri.Z_Malloc(width * height * 3);
    for (i = 0; i < width * height; ++i) {
        rgb[i * 3 + 0] = pic[i * 4 + 0];
        rgb[i * 3 + 1] = pic[i * 4 + 1];
        rgb[i * 3 + 2] = pic[i * 4 + 2];
    }
    ri.Free(pic);

    RE_SaveJPG((char *)qpath, 100, width, height, rgb, 0);
    ri.Free(rgb);

    if (!ri.FS_FileExists(qpath)) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2: failed to write AI input %s.\n", qpath);
        return qfalse;
    }

    *sourceWidth = width;
    *sourceHeight = height;
    return qtrue;
}

void R_DWTextureAIBuild_f(void)
{
#ifdef _WIN32
    char exe[MAX_OSPATH * 2], models[MAX_OSPATH * 2], workDir[MAX_OSPATH * 2];
    char inputQ[MAX_QPATH], outputQ[MAX_QPATH];
    char inputPhysical[MAX_OSPATH * 2], outputPhysical[MAX_OSPATH * 2];
    const char *home, *game;
    byte *out = NULL;
    int outWidth = 0, outHeight = 0, outMips = 0;
    int sourceWidth = 0, sourceHeight = 0;
    GLenum outFmt = GL_RGBA8;
    imgFlags_t flags;
    char previewName[MAX_QPATH];
    static unsigned int serial = 0;
    unsigned int h;

    if (!s_dwtr.selected || !s_dwtr.original) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2: select a texture first with /dw_tex_pick.\n");
        return;
    }
    if (s_dwtr.previewBuilt && s_dwtr.preview) {
        DWTR_Show(qtrue);
        ri.Printf(PRINT_ALL, "DWTR AI B2: existing B2 preview activated.\n");
        return;
    }

    R_IssuePendingRenderCommands();

    if (!DWTRAI_FindBackend(exe, sizeof(exe), models, sizeof(models),
                            workDir, sizeof(workDir))) {
        return;
    }

    h = DWTR_HashPath(s_dwtr.original->imgName);
    Com_sprintf(inputQ, sizeof(inputQ), "texture_restoration/b2_%08x_input.jpg", h);
    Com_sprintf(outputQ, sizeof(outputQ), "texture_restoration/b2_%08x_output.png", h);

    if (!DWTRAI_OriginalToJPG(s_dwtr.original, inputQ, &sourceWidth, &sourceHeight)) {
        return;
    }

    home = DWTRAI_CvarString("fs_homepath");
    if (!home[0]) home = DWTRAI_CvarString("fs_basepath");
    game = DWTRAI_GameDir();
    DWTRAI_PhysicalPath(inputPhysical, sizeof(inputPhysical), home, game, inputQ);
    DWTRAI_PhysicalPath(outputPhysical, sizeof(outputPhysical), home, game, outputQ);

    if (!DWTRAI_RunProcess(exe, models, inputPhysical, outputPhysical)) {
        return;
    }

    R_LoadImage(outputQ, &out, &outWidth, &outHeight, &outFmt, &outMips);
    if (!out || outWidth <= 0 || outHeight <= 0) {
        if (out) ri.Free(out);
        ri.Printf(PRINT_WARNING, "DWTR AI B2: backend completed but output PNG was not loadable.\n");
        return;
    }
    if (outFmt != GL_RGBA8 && outFmt != GL_SRGB8_ALPHA8_EXT) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2: unexpected output format.\n");
        ri.Free(out);
        return;
    }
    if (outWidth != sourceWidth * 4 || outHeight != sourceHeight * 4) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2: expected %dx%d, got %dx%d; preview refused.\n",
                  sourceWidth * 4, sourceHeight * 4, outWidth, outHeight);
        ri.Free(out);
        return;
    }
    if (outWidth > glConfig.maxTextureSize || outHeight > glConfig.maxTextureSize) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2: AI result %dx%d exceeds GPU max texture size %d.\n",
                  outWidth, outHeight, glConfig.maxTextureSize);
        ri.Free(out);
        return;
    }

    flags = s_dwtr.original->flags;
    flags |= IMGFLAG_NO_COMPRESSION;
    flags &= ~(IMGFLAG_PICMIP | IMGFLAG_GENNORMALMAP);
    Com_sprintf(previewName, sizeof(previewName), "*dwtr_ai_b2_%u", ++serial);
    s_dwtr.preview = R_CreateImage(previewName, out, outWidth, outHeight,
                                   s_dwtr.original->type, flags, 0);
    if (!s_dwtr.preview) {
        ri.Free(out);
        ri.Printf(PRINT_WARNING, "DWTR AI B2: failed to create GPU preview.\n");
        return;
    }

    s_dwtr.pixels = out;
    s_dwtr.width = outWidth;
    s_dwtr.height = outHeight;
    s_dwtr.previewBuilt = qtrue;
    DWTR_Show(qtrue);

    ri.Printf(PRINT_ALL,
              "DWTR AI B2: B2 ACTIVE %s %dx%d -> %dx%d using local %s.\n",
              s_dwtr.original->imgName, sourceWidth, sourceHeight,
              outWidth, outHeight, DWTR_AI_MODEL);
    ri.Printf(PRINT_ALL,
              "DWTR AI B2: /dw_tex_ab compares A ORIGINAL <-> B2 LOCAL AI; /dw_tex_save accepts B2.\n");
#else
    ri.Printf(PRINT_WARNING, "DWTR AI B2: Win64 test backend only.\n");
#endif
}

void R_DWTextureAIBackendInfo_f(void)
{
    char exe[MAX_OSPATH * 2], models[MAX_OSPATH * 2], workDir[MAX_OSPATH * 2];
    if (DWTRAI_FindBackend(exe, sizeof(exe), models, sizeof(models),
                           workDir, sizeof(workDir))) {
        ri.Printf(PRINT_ALL, "DWTR AI B2: backend READY.\n");
        ri.Printf(PRINT_ALL, "DWTR AI B2: model=%s scale=4 runtime=ncnn/Vulkan network=OFF telemetry=OFF.\n",
                  DWTR_AI_MODEL);
        ri.Printf(PRINT_ALL, "DWTR AI B2: exe=%s\n", exe);
        ri.Printf(PRINT_ALL, "DWTR AI B2: models=%s\n", models);
    }
}
