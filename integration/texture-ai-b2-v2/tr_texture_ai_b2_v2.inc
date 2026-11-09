/* DARKWOLF_TEXTURE_AI_B2_V2
 * Stage 1: crash-free physical PK3 save + orientation-safe AI round trip.
 * Stage 2: Faithful/Balanced/Strong variants + next/prev.
 */
#define DWTRV2_CANDIDATE_COUNT 3

typedef struct {
    image_t *image;
    byte *pixels;
    int width;
    int height;
    const char *label;
    int aiPercent;
} dwtrV2Candidate_t;

typedef struct {
    dwtrV2Candidate_t c[DWTRV2_CANDIDATE_COUNT];
    int count;
    int current;
} dwtrV2State_t;

static dwtrV2State_t s_dwtrv2;

static int DWTRV2_ClampI(int v, int lo, int hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

void R_DWTextureV2ResetCandidates(void)
{
    int i;
    for (i = 0; i < DWTRV2_CANDIDATE_COUNT; ++i) {
        if (s_dwtrv2.c[i].pixels) {
            if (s_dwtr.pixels == s_dwtrv2.c[i].pixels) {
                s_dwtr.pixels = NULL;
            }
            ri.Free(s_dwtrv2.c[i].pixels);
            s_dwtrv2.c[i].pixels = NULL;
        }
        s_dwtrv2.c[i].image = NULL;
    }
    Com_Memset(&s_dwtrv2, 0, sizeof(s_dwtrv2));
}

static void DWTRV2_FlipRGB(byte *dst, const byte *src, int w, int h)
{
    int y;
    int row = w * 3;
    for (y = 0; y < h; ++y) {
        Com_Memcpy(dst + y * row, src + (h - 1 - y) * row, row);
    }
}

/* RE_SaveJPG() already traverses source rows bottom->top.
 * Feed it a pre-flipped RGB buffer so the JPEG presented to Real-ESRGAN is
 * canonical top-down. This fixes the asymmetric window/wood upside-down bug. */
static qboolean DWTRV2_OriginalToJPG(image_t *source, const char *qpath,
                                     int *sourceWidth, int *sourceHeight)
{
    byte *pic = NULL;
    byte *rgb = NULL;
    byte *flipped = NULL;
    int width = 0, height = 0, mips = 0, i;
    GLenum fmt = GL_RGBA8;

    R_LoadImage(source->imgName, &pic, &width, &height, &fmt, &mips);
    if (!pic || width <= 0 || height <= 0) {
        if (pic) ri.Free(pic);
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: cannot read %s.\n", source->imgName);
        return qfalse;
    }
    if (fmt != GL_RGBA8 && fmt != GL_SRGB8_ALPHA8_EXT) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: compressed/non-RGBA source refused.\n");
        ri.Free(pic);
        return qfalse;
    }

    for (i = 0; i < width * height; ++i) {
        if (pic[i * 4 + 3] < 250) {
            ri.Printf(PRINT_WARNING,
                      "DWTR AI B2 V2: alpha/cutout texture refused (%s).\n",
                      source->imgName);
            ri.Free(pic);
            return qfalse;
        }
    }

    rgb = (byte *)ri.Z_Malloc(width * height * 3);
    flipped = (byte *)ri.Z_Malloc(width * height * 3);
    for (i = 0; i < width * height; ++i) {
        rgb[i * 3 + 0] = pic[i * 4 + 0];
        rgb[i * 3 + 1] = pic[i * 4 + 1];
        rgb[i * 3 + 2] = pic[i * 4 + 2];
    }
    ri.Free(pic);

    DWTRV2_FlipRGB(flipped, rgb, width, height);
    ri.Free(rgb);

    RE_SaveJPG((char *)qpath, 100, width, height, flipped, 0);
    ri.Free(flipped);

    if (!ri.FS_FileExists(qpath)) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: failed to write AI input %s.\n", qpath);
        return qfalse;
    }

    *sourceWidth = width;
    *sourceHeight = height;
    return qtrue;
}

static void DWTRV2_BlendCandidate(const byte *base, const byte *ai, byte *dst,
                                  int pixels, int lumaPercent,
                                  int chromaPercent, int maxLumaDelta)
{
    int i, c;
    for (i = 0; i < pixels; ++i) {
        int bi = i * 4;
        int by = (77 * base[bi+0] + 150 * base[bi+1] + 29 * base[bi+2]) >> 8;
        int ay = (77 * ai[bi+0] + 150 * ai[bi+1] + 29 * ai[bi+2]) >> 8;
        int dy = DWTRV2_ClampI(ay - by, -maxLumaDelta, maxLumaDelta);
        int ny = by + (dy * lumaPercent) / 100;

        for (c = 0; c < 3; ++c) {
            int bc = (int)base[bi+c] - by;
            int ac = (int)ai[bi+c] - ay;
            int dc = DWTRV2_ClampI(ac - bc, -40, 40);
            int nc = bc + (dc * chromaPercent) / 100;
            dst[bi+c] = (byte)DWTRV2_ClampI(ny + nc, 0, 255);
        }
        dst[bi+3] = base[bi+3];
    }
}

static qboolean DWTRV2_CreateCandidate(int slot, const char *label,
                                       const byte *base, const byte *ai,
                                       int w, int h,
                                       int lumaPercent, int chromaPercent,
                                       int maxLumaDelta, imgType_t type,
                                       imgFlags_t flags, int characterMIP)
{
    char name[MAX_QPATH];
    byte *pixels;
    static unsigned int serial = 0;

    if (slot < 0 || slot >= DWTRV2_CANDIDATE_COUNT) return qfalse;

    pixels = (byte *)ri.Z_Malloc(w * h * 4);
    DWTRV2_BlendCandidate(base, ai, pixels, w * h,
                          lumaPercent, chromaPercent, maxLumaDelta);

    Com_sprintf(name, sizeof(name), "*dwtr_b2v2_%d_%u", slot, ++serial);
    s_dwtrv2.c[slot].image = R_CreateImage(name, pixels, w, h, type, flags, characterMIP);
    if (!s_dwtrv2.c[slot].image) {
        ri.Free(pixels);
        return qfalse;
    }

    s_dwtrv2.c[slot].pixels = pixels;
    s_dwtrv2.c[slot].width = w;
    s_dwtrv2.c[slot].height = h;
    s_dwtrv2.c[slot].label = label;
    s_dwtrv2.c[slot].aiPercent = lumaPercent;
    return qtrue;
}

static void DWTRV2_Activate(int slot)
{
    if (slot < 0 || slot >= s_dwtrv2.count) return;
    s_dwtrv2.current = slot;
    s_dwtr.preview = s_dwtrv2.c[slot].image;
    s_dwtr.pixels = s_dwtrv2.c[slot].pixels;
    s_dwtr.width = s_dwtrv2.c[slot].width;
    s_dwtr.height = s_dwtrv2.c[slot].height;
    s_dwtr.previewBuilt = qtrue;
    DWTR_Show(qtrue);
}

void R_DWTextureAIBuildV2_f(void)
{
#ifdef _WIN32
    char exe[MAX_OSPATH * 2], models[MAX_OSPATH * 2], workDir[MAX_OSPATH * 2];
    char inputQ[MAX_QPATH], outputQ[MAX_QPATH];
    char inputPhysical[MAX_OSPATH * 2], outputPhysical[MAX_OSPATH * 2];
    const char *home, *game;
    byte *ai = NULL;
    byte *basePixels = NULL;
    image_t *baseImage = NULL;
    int aiW = 0, aiH = 0, aiMips = 0;
    int baseW = 0, baseH = 0;
    int sourceW = 0, sourceH = 0;
    GLenum aiFmt = GL_RGBA8;
    imgFlags_t flags;
    unsigned int hash;

    if (!s_dwtr.selected || !s_dwtr.original) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: select a texture first with /dw_tex_pick.\n");
        return;
    }
    if (s_dwtrv2.count == DWTRV2_CANDIDATE_COUNT) {
        DWTRV2_Activate(1);
        ri.Printf(PRINT_ALL, "DWTR AI B2 V2: existing BALANCED candidate activated.\n");
        return;
    }

    R_IssuePendingRenderCommands();
    R_DWTextureV2ResetCandidates();

    if (!DWTRAI_FindBackend(exe, sizeof(exe), models, sizeof(models),
                            workDir, sizeof(workDir))) {
        return;
    }

    hash = DWTR_HashPath(s_dwtr.original->imgName);
    Com_sprintf(inputQ, sizeof(inputQ), "texture_restoration/b2v2_%08x_input.jpg", hash);
    Com_sprintf(outputQ, sizeof(outputQ), "texture_restoration/b2v2_%08x_ai.png", hash);

    if (!DWTRV2_OriginalToJPG(s_dwtr.original, inputQ, &sourceW, &sourceH)) {
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

    R_LoadImage(outputQ, &ai, &aiW, &aiH, &aiFmt, &aiMips);
    if (!ai || aiW != sourceW * 4 || aiH != sourceH * 4) {
        if (ai) ri.Free(ai);
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2: invalid AI output; expected %dx%d.\n",
                  sourceW * 4, sourceH * 4);
        return;
    }
    if (aiFmt != GL_RGBA8 && aiFmt != GL_SRGB8_ALPHA8_EXT) {
        ri.Free(ai);
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: unexpected AI output format.\n");
        return;
    }
    if (aiW > glConfig.maxTextureSize || aiH > glConfig.maxTextureSize) {
        ri.Free(ai);
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: %dx%d exceeds GPU max %d.\n",
                  aiW, aiH, glConfig.maxTextureSize);
        return;
    }

    /* Build a deterministic 4x structural reference from the original.
     * Candidates retain this structure and borrow bounded detail from AI. */
    if (!R_DWTextureRestoreBuild(s_dwtr.original, &baseImage,
                                 &basePixels, &baseW, &baseH) ||
        !basePixels || baseW != aiW || baseH != aiH) {
        if (ai) ri.Free(ai);
        if (basePixels) ri.Free(basePixels);
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: 4x original reference build failed.\n");
        return;
    }

    flags = s_dwtr.original->flags;
    flags |= IMGFLAG_NO_COMPRESSION;
    flags &= ~(IMGFLAG_PICMIP | IMGFLAG_GENNORMALMAP);

    /* Three visibly distinct but identity-guarded candidates.
     * Chroma is restrained more strongly than luma to keep RTCW palette. */
    if (!DWTRV2_CreateCandidate(0, "FAITHFUL", basePixels, ai, aiW, aiH,
                                35, 10, 36, s_dwtr.original->type, flags,
                                s_dwtr.original->characterMIP) ||
        !DWTRV2_CreateCandidate(1, "BALANCED", basePixels, ai, aiW, aiH,
                                55, 20, 56, s_dwtr.original->type, flags,
                                s_dwtr.original->characterMIP) ||
        !DWTRV2_CreateCandidate(2, "STRONG", basePixels, ai, aiW, aiH,
                                80, 35, 88, s_dwtr.original->type, flags,
                                s_dwtr.original->characterMIP)) {
        ri.Free(ai);
        ri.Free(basePixels);
        R_DWTextureV2ResetCandidates();
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: candidate GPU creation failed.\n");
        return;
    }

    ri.Free(ai);
    ri.Free(basePixels);

    s_dwtrv2.count = DWTRV2_CANDIDATE_COUNT;
    DWTRV2_Activate(1); /* RTCW default = BALANCED */

    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2: built 3 candidates for %s %dx%d -> %dx%d.\n",
              s_dwtr.original->imgName, sourceW, sourceH, aiW, aiH);
    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2: current=BALANCED; /dw_tex_next /dw_tex_prev, /dw_tex_ab, /dw_tex_save.\n");
#else
    ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: Win64 test backend only.\n");
#endif
}

void R_DWTextureNext_f(void)
{
    int next;
    if (s_dwtrv2.count <= 0) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: build candidates first with /dw_tex_ai_build.\n");
        return;
    }
    next = (s_dwtrv2.current + 1) % s_dwtrv2.count;
    DWTRV2_Activate(next);
    ri.Printf(PRINT_ALL, "DWTR AI B2 V2: variant %d/%d = %s (%d%% AI detail).\n",
              next + 1, s_dwtrv2.count, s_dwtrv2.c[next].label,
              s_dwtrv2.c[next].aiPercent);
}

void R_DWTexturePrev_f(void)
{
    int prev;
    if (s_dwtrv2.count <= 0) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: build candidates first with /dw_tex_ai_build.\n");
        return;
    }
    prev = (s_dwtrv2.current + s_dwtrv2.count - 1) % s_dwtrv2.count;
    DWTRV2_Activate(prev);
    ri.Printf(PRINT_ALL, "DWTR AI B2 V2: variant %d/%d = %s (%d%% AI detail).\n",
              prev + 1, s_dwtrv2.count, s_dwtrv2.c[prev].label,
              s_dwtrv2.c[prev].aiPercent);
}

void R_DWTextureABV2_f(void)
{
    if (s_dwtrv2.count <= 0 || !s_dwtr.previewBuilt) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: build candidates first with /dw_tex_ai_build.\n");
        return;
    }
    R_IssuePendingRenderCommands();
    DWTR_Show(s_dwtr.showingB ? qfalse : qtrue);
    if (s_dwtr.showingB) {
        ri.Printf(PRINT_ALL, "DWTR AI B2 V2: B=%s active for %s.\n",
                  s_dwtrv2.c[s_dwtrv2.current].label, s_dwtr.original->imgName);
    } else {
        ri.Printf(PRINT_ALL, "DWTR AI B2 V2: A=ORIGINAL active for %s.\n",
                  s_dwtr.original->imgName);
    }
}

void R_DWTextureInfoV2_f(void)
{
    if (!s_dwtr.selected) {
        ri.Printf(PRINT_ALL, "DWTR AI B2 V2: nothing selected. /dw_tex_pick\n");
        return;
    }
    if (s_dwtrv2.count <= 0) {
        ri.Printf(PRINT_ALL,
                  "DWTR AI B2 V2: texture=%s source=%dx%d candidates=0. /dw_tex_ai_build\n",
                  s_dwtr.original->imgName, s_dwtr.original->width, s_dwtr.original->height);
        return;
    }
    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2: texture=%s source=%dx%d output=%dx%d candidate=%d/%d %s ai=%d%% showing=%s\n",
              s_dwtr.original->imgName, s_dwtr.original->width, s_dwtr.original->height,
              s_dwtr.width, s_dwtr.height,
              s_dwtrv2.current + 1, s_dwtrv2.count,
              s_dwtrv2.c[s_dwtrv2.current].label,
              s_dwtrv2.c[s_dwtrv2.current].aiPercent,
              s_dwtr.showingB ? "B" : "A");
}

#ifdef _WIN32
static qboolean DWTRV2_WriteAll(HANDLE h, const void *data, DWORD size)
{
    const byte *p = (const byte *)data;
    DWORD done = 0;
    while (done < size) {
        DWORD wrote = 0;
        if (!WriteFile(h, p + done, size - done, &wrote, NULL) || wrote == 0) {
            return qfalse;
        }
        done += wrote;
    }
    return qtrue;
}

static qboolean DWTRV2_WriteZipEntry(HANDLE h, const char *name,
                                     const byte *data, int len,
                                     DWORD *offset, byte *central, int *centralLen)
{
    byte local[30];
    byte *cent = central;
    int nameLen = (int)strlen(name);
    unsigned int crc = DWTR_CRC32(data, len);
    DWORD localOffset = *offset;

    if (nameLen <= 0 || nameLen >= MAX_QPATH) return qfalse;

    Com_Memset(local, 0, sizeof(local));
    DWTR_Put32(local+0, 0x04034b50);
    DWTR_Put16(local+4, 20);
    DWTR_Put16(local+6, 0);
    DWTR_Put16(local+8, 0);
    DWTR_Put32(local+14, crc);
    DWTR_Put32(local+18, (unsigned int)len);
    DWTR_Put32(local+22, (unsigned int)len);
    DWTR_Put16(local+26, (unsigned int)nameLen);

    if (!DWTRV2_WriteAll(h, local, sizeof(local)) ||
        !DWTRV2_WriteAll(h, name, (DWORD)nameLen) ||
        !DWTRV2_WriteAll(h, data, (DWORD)len)) {
        return qfalse;
    }
    *offset += (DWORD)(sizeof(local) + nameLen + len);

    Com_Memset(cent, 0, 46 + MAX_QPATH);
    DWTR_Put32(cent+0, 0x02014b50);
    DWTR_Put16(cent+4, 20);
    DWTR_Put16(cent+6, 20);
    DWTR_Put16(cent+8, 0);
    DWTR_Put16(cent+10, 0);
    DWTR_Put32(cent+16, crc);
    DWTR_Put32(cent+20, (unsigned int)len);
    DWTR_Put32(cent+24, (unsigned int)len);
    DWTR_Put16(cent+28, (unsigned int)nameLen);
    DWTR_Put32(cent+42, (unsigned int)localOffset);
    Com_Memcpy(cent+46, name, nameLen);
    *centralLen = 46 + nameLen;
    return qtrue;
}

static qboolean DWTRV2_WritePhysicalPK3(const char *finalPath,
                                        const char *texturePath,
                                        const byte *textureData, int textureLen,
                                        const char *manifestPath,
                                        const byte *manifestData, int manifestLen)
{
    char tmpPath[MAX_OSPATH * 2];
    HANDLE h;
    DWORD offset = 0;
    DWORD centralOffset;
    DWORD centralSize;
    byte central1[46 + MAX_QPATH];
    byte central2[46 + MAX_QPATH];
    int central1Len = 0, central2Len = 0;
    byte end[22];
    qboolean ok = qfalse;

    Com_sprintf(tmpPath, sizeof(tmpPath), "%s.tmp", finalPath);
    h = CreateFileA(tmpPath, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                    FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: CreateFile failed for %s winerr=%lu.\n",
                  tmpPath, (unsigned long)GetLastError());
        return qfalse;
    }

    if (!DWTRV2_WriteZipEntry(h, texturePath, textureData, textureLen,
                              &offset, central1, &central1Len) ||
        !DWTRV2_WriteZipEntry(h, manifestPath, manifestData, manifestLen,
                              &offset, central2, &central2Len)) {
        goto done;
    }

    centralOffset = offset;
    if (!DWTRV2_WriteAll(h, central1, (DWORD)central1Len) ||
        !DWTRV2_WriteAll(h, central2, (DWORD)central2Len)) {
        goto done;
    }
    centralSize = (DWORD)(central1Len + central2Len);

    Com_Memset(end, 0, sizeof(end));
    DWTR_Put32(end+0, 0x06054b50);
    DWTR_Put16(end+8, 2);
    DWTR_Put16(end+10, 2);
    DWTR_Put32(end+12, centralSize);
    DWTR_Put32(end+16, centralOffset);

    if (!DWTRV2_WriteAll(h, end, sizeof(end))) goto done;
    FlushFileBuffers(h);
    ok = qtrue;

done:
    CloseHandle(h);
    if (!ok) {
        DeleteFileA(tmpPath);
        return qfalse;
    }
    if (!MoveFileExA(tmpPath, finalPath,
                     MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: final PK3 rename failed winerr=%lu.\n",
                  (unsigned long)GetLastError());
        DeleteFileA(tmpPath);
        return qfalse;
    }
    return qtrue;
}
#endif

static byte *DWTRV2_EncodeJPGCorrect(const byte *rgba, int w, int h, int *outLen)
{
    byte *rgb;
    byte *flipped;
    byte *jpg;
    int i;
    size_t cap, got;

    rgb = (byte *)ri.Z_Malloc(w * h * 3);
    flipped = (byte *)ri.Z_Malloc(w * h * 3);
    for (i = 0; i < w * h; ++i) {
        rgb[i*3+0] = rgba[i*4+0];
        rgb[i*3+1] = rgba[i*4+1];
        rgb[i*3+2] = rgba[i*4+2];
    }
    DWTRV2_FlipRGB(flipped, rgb, w, h);
    ri.Free(rgb);

    cap = (size_t)w * h * 3;
    jpg = (byte *)ri.Z_Malloc((int)cap);
    got = RE_SaveJPGToBuffer(jpg, cap, 96, w, h, flipped, 0);
    ri.Free(flipped);
    if (!got) {
        ri.Free(jpg);
        return NULL;
    }
    *outLen = (int)got;
    return jpg;
}

void R_DWTextureSaveV2_f(void)
{
#ifdef _WIN32
    char internal[MAX_QPATH];
    char pk3Name[MAX_QPATH];
    char pk3Physical[MAX_OSPATH * 2];
    char manifestQ[MAX_QPATH];
    char manifestInternal[MAX_QPATH];
    char manifest[1400];
    const char *ext;
    const char *home;
    const char *game;
    byte *encoded = NULL;
    int encodedLen = 0;
    unsigned int hash;
    const dwtrV2Candidate_t *cand;

    if (!s_dwtr.selected || s_dwtrv2.count <= 0 || !s_dwtr.original) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: no candidate to save.\n");
        return;
    }
    cand = &s_dwtrv2.c[s_dwtrv2.current];
    if (!cand->pixels || !cand->image) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: current candidate is invalid.\n");
        return;
    }

    Q_strncpyz(internal, s_dwtr.original->imgName, sizeof(internal));
    ext = strrchr(internal, '.');
    if (!ext) {
        if ((int)strlen(internal) + 4 >= MAX_QPATH) {
            ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: texture path too long.\n");
            return;
        }
        Q_strcat(internal, sizeof(internal), ".tga");
        ext = ".tga";
    }

    if (!Q_stricmp(ext, ".tga")) {
        encoded = DWTR_EncodeTGA(cand->pixels, cand->width, cand->height, &encodedLen);
    } else if (!Q_stricmp(ext, ".jpg") || !Q_stricmp(ext, ".jpeg")) {
        encoded = DWTRV2_EncodeJPGCorrect(cand->pixels, cand->width, cand->height, &encodedLen);
    } else {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2: persistent save supports TGA/JPG source paths in this build; %s refused.\n",
                  ext);
        return;
    }
    if (!encoded || encodedLen <= 0) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: candidate encoding failed.\n");
        return;
    }

    hash = DWTR_HashPath(internal);
    Com_sprintf(pk3Name, sizeof(pk3Name), "zz_dwtr_%08x.pk3", hash);
    Com_sprintf(manifestQ, sizeof(manifestQ), "texture_restoration/dwtr_%08x_v2.txt", hash);
    Com_sprintf(manifestInternal, sizeof(manifestInternal),
                "dwtr/manifest_%08x.txt", hash);

    Com_sprintf(manifest, sizeof(manifest),
        "DarkWolf Local AI Texture Restoration B2 V2\n"
        "source %s\n"
        "replacement %s\n"
        "variant %s\n"
        "aiPercent %d\n"
        "size %d %d\n"
        "model %s\n"
        "orientation canonical_top_down_roundtrip\n"
        "save physical_zip_atomic\n"
        "network no\n"
        "telemetry no\n",
        s_dwtr.original->imgName, internal, cand->label, cand->aiPercent,
        cand->width, cand->height, DWTR_AI_MODEL);

    home = DWTRAI_CvarString("fs_homepath");
    if (!home[0]) home = DWTRAI_CvarString("fs_basepath");
    game = DWTRAI_GameDir();
    DWTRAI_PhysicalPath(pk3Physical, sizeof(pk3Physical), home, game, pk3Name);

    if (!DWTRV2_WritePhysicalPK3(pk3Physical, internal,
                                 encoded, encodedLen,
                                 manifestInternal,
                                 (const byte *)manifest, (int)strlen(manifest))) {
        ri.Free(encoded);
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: PK3 save failed; game remains running.\n");
        return;
    }
    ri.Free(encoded);

    /* Plain-text audit is safe through Q3 filesystem; PK3 itself bypasses the
     * extension guard via Win32 physical I/O above. */
    ri.FS_WriteFile(manifestQ, manifest, (int)strlen(manifest));
    DWTRV2_Activate(s_dwtrv2.current);

    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2: SAVED %s variant=%s. It will override %s after restart.\n",
              pk3Name, cand->label, internal);
    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2: save path uses physical ZIP writer; no FS_FOpenFileWrite(.pk3).\n");
#else
    ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: Win64 save backend only.\n");
#endif
}
