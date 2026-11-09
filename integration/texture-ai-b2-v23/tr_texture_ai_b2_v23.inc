/* DARKWOLF_TEXTURE_AI_B2_V23
 * Single cumulative PK3 persistence.
 *
 * First accepted texture creates:
 *   zzzzzz_DW_TextureRestoration.pk3
 *
 * Every later /dw_tex_save atomically rebuilds that same PK3, preserving all
 * previous entries, replacing an existing texture qpath when re-saved, and
 * adding a new texture qpath when first accepted.
 *
 * Existing V2/V2.1/V2.2 per-texture DWTR PK3 files are migrated on save and
 * removed only after the cumulative pack has been written successfully.
 */

#define DWTRV23_PACK_NAME "zzzzzz_DW_TextureRestoration.pk3"
#define DWTRV23_MAX_ENTRIES 8192
#define DWTRV23_COPY_CHUNK (64 * 1024)

typedef struct {
    char name[MAX_QPATH];
    byte bytes[46 + MAX_QPATH];
    int len;
} dwtrV23Central_t;

#ifdef _WIN32
static unsigned short DWTRV23_Get16(const byte *p)
{
    return (unsigned short)(p[0] | ((unsigned short)p[1] << 8));
}

static unsigned int DWTRV23_Get32(const byte *p)
{
    return (unsigned int)p[0]
         | ((unsigned int)p[1] << 8)
         | ((unsigned int)p[2] << 16)
         | ((unsigned int)p[3] << 24);
}

static qboolean DWTRV23_ReadExact(HANDLE h, void *data, DWORD size)
{
    byte *p = (byte *)data;
    DWORD done = 0;

    while (done < size) {
        DWORD got = 0;
        if (!ReadFile(h, p + done, size - done, &got, NULL) || got == 0) {
            return qfalse;
        }
        done += got;
    }
    return qtrue;
}

static qboolean DWTRV23_SeekForward(HANDLE h, DWORD amount)
{
    LARGE_INTEGER d;
    d.QuadPart = (LONGLONG)amount;
    return SetFilePointerEx(h, d, NULL, FILE_CURRENT) ? qtrue : qfalse;
}

static qboolean DWTRV23_NameExists(dwtrV23Central_t *central, int count,
                                   const char *name)
{
    int i;
    for (i = 0; i < count; ++i) {
        if (!Q_stricmp(central[i].name, name)) {
            return qtrue;
        }
    }
    return qfalse;
}

static qboolean DWTRV23_BuildCentral(dwtrV23Central_t *cent,
                                     const char *name,
                                     unsigned int crc,
                                     unsigned int size,
                                     DWORD localOffset)
{
    int nameLen = (int)strlen(name);

    if (!cent || nameLen <= 0 || nameLen >= MAX_QPATH) {
        return qfalse;
    }

    Com_Memset(cent, 0, sizeof(*cent));
    Q_strncpyz(cent->name, name, sizeof(cent->name));

    DWTR_Put32(cent->bytes + 0, 0x02014b50);
    DWTR_Put16(cent->bytes + 4, 20);
    DWTR_Put16(cent->bytes + 6, 20);
    DWTR_Put16(cent->bytes + 8, 0);
    DWTR_Put16(cent->bytes + 10, 0); /* stored */
    DWTR_Put32(cent->bytes + 16, crc);
    DWTR_Put32(cent->bytes + 20, size);
    DWTR_Put32(cent->bytes + 24, size);
    DWTR_Put16(cent->bytes + 28, (unsigned int)nameLen);
    DWTR_Put32(cent->bytes + 42, (unsigned int)localOffset);
    Com_Memcpy(cent->bytes + 46, name, nameLen);
    cent->len = 46 + nameLen;
    return qtrue;
}

static qboolean DWTRV23_WriteStoredHeader(HANDLE out,
                                          const char *name,
                                          unsigned int crc,
                                          unsigned int size,
                                          DWORD *offset,
                                          dwtrV23Central_t *cent)
{
    byte local[30];
    int nameLen = (int)strlen(name);
    DWORD localOffset;

    if (!out || !offset || !cent ||
        nameLen <= 0 || nameLen >= MAX_QPATH) {
        return qfalse;
    }

    localOffset = *offset;
    Com_Memset(local, 0, sizeof(local));
    DWTR_Put32(local + 0, 0x04034b50);
    DWTR_Put16(local + 4, 20);
    DWTR_Put16(local + 6, 0);
    DWTR_Put16(local + 8, 0); /* stored */
    DWTR_Put32(local + 14, crc);
    DWTR_Put32(local + 18, size);
    DWTR_Put32(local + 22, size);
    DWTR_Put16(local + 26, (unsigned int)nameLen);

    if (!DWTRV2_WriteAll(out, local, sizeof(local)) ||
        !DWTRV2_WriteAll(out, name, (DWORD)nameLen)) {
        return qfalse;
    }

    if (!DWTRV23_BuildCentral(cent, name, crc, size, localOffset)) {
        return qfalse;
    }

    *offset += (DWORD)(sizeof(local) + nameLen);
    return qtrue;
}

static qboolean DWTRV23_WriteMemoryEntry(HANDLE out,
                                         const char *name,
                                         const byte *data,
                                         int len,
                                         DWORD *offset,
                                         dwtrV23Central_t *central,
                                         int *count)
{
    unsigned int crc;

    if (!out || !name || !data || len < 0 || !offset || !central || !count) {
        return qfalse;
    }
    if (*count >= DWTRV23_MAX_ENTRIES) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.3: cumulative PK3 entry limit reached (%d).\n",
                  DWTRV23_MAX_ENTRIES);
        return qfalse;
    }

    crc = DWTR_CRC32(data, len);
    if (!DWTRV23_WriteStoredHeader(out, name, crc, (unsigned int)len,
                                   offset, &central[*count])) {
        return qfalse;
    }
    if (len > 0 && !DWTRV2_WriteAll(out, data, (DWORD)len)) {
        return qfalse;
    }

    *offset += (DWORD)len;
    (*count)++;
    return qtrue;
}

static qboolean DWTRV23_CopyStoredData(HANDLE in, HANDLE out, DWORD size)
{
    byte *buffer;
    DWORD left = size;
    qboolean ok = qtrue;

    buffer = (byte *)ri.Z_Malloc(DWTRV23_COPY_CHUNK);
    while (left > 0) {
        DWORD n = left > DWTRV23_COPY_CHUNK ? DWTRV23_COPY_CHUNK : left;
        if (!DWTRV23_ReadExact(in, buffer, n) ||
            !DWTRV2_WriteAll(out, buffer, n)) {
            ok = qfalse;
            break;
        }
        left -= n;
    }
    ri.Free(buffer);
    return ok;
}

/* Copies only store-method entries. All DarkWolf-generated texture packs use
 * store mode; refusing an unexpected compressed/data-descriptor archive avoids
 * silently corrupting an unknown third-party PK3. */
static qboolean DWTRV23_CopyArchiveEntries(const char *sourcePath,
                                           HANDLE out,
                                           const char *replaceTexture,
                                           const char *replaceManifest,
                                           dwtrV23Central_t *central,
                                           int *count,
                                           DWORD *offset,
                                           int *copiedEntries)
{
    HANDLE in;
    qboolean ok = qtrue;

    if (copiedEntries) *copiedEntries = 0;
    if (!DWTRAI_IsFile(sourcePath)) {
        return qtrue;
    }

    in = CreateFileA(sourcePath, GENERIC_READ, FILE_SHARE_READ, NULL,
                     OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (in == INVALID_HANDLE_VALUE) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.3: cannot open existing pack %s winerr=%lu.\n",
                  sourcePath, (unsigned long)GetLastError());
        return qfalse;
    }

    for (;;) {
        byte sigBytes[4];
        byte rest[26];
        unsigned int sig;
        unsigned short flags, method, nameLen, extraLen;
        unsigned int crc, compSize, uncompSize;
        char name[MAX_QPATH];
        qboolean skip;

        {
            DWORD got = 0;
            if (!ReadFile(in, sigBytes, 4, &got, NULL)) {
                ok = qfalse;
                break;
            }
            if (got == 0) {
                break;
            }
            if (got != 4) {
                ok = qfalse;
                break;
            }
        }

        sig = DWTRV23_Get32(sigBytes);
        if (sig == 0x02014b50 || sig == 0x06054b50) {
            break; /* central directory / EOCD */
        }
        if (sig != 0x04034b50) {
            ri.Printf(PRINT_WARNING,
                      "DWTR AI B2 V2.3: unsupported ZIP structure in %s.\n",
                      sourcePath);
            ok = qfalse;
            break;
        }

        if (!DWTRV23_ReadExact(in, rest, sizeof(rest))) {
            ok = qfalse;
            break;
        }

        flags = DWTRV23_Get16(rest + 2);
        method = DWTRV23_Get16(rest + 4);
        crc = DWTRV23_Get32(rest + 10);
        compSize = DWTRV23_Get32(rest + 14);
        uncompSize = DWTRV23_Get32(rest + 18);
        nameLen = DWTRV23_Get16(rest + 22);
        extraLen = DWTRV23_Get16(rest + 24);

        if ((flags & 8) || method != 0 || compSize != uncompSize ||
            nameLen <= 0 || nameLen >= MAX_QPATH) {
            ri.Printf(PRINT_WARNING,
                      "DWTR AI B2 V2.3: %s contains an unsupported ZIP entry; migration/update aborted safely.\n",
                      sourcePath);
            ok = qfalse;
            break;
        }

        if (!DWTRV23_ReadExact(in, name, nameLen)) {
            ok = qfalse;
            break;
        }
        name[nameLen] = '\0';

        if (extraLen && !DWTRV23_SeekForward(in, extraLen)) {
            ok = qfalse;
            break;
        }

        skip = qfalse;
        if (replaceTexture && !Q_stricmp(name, replaceTexture)) skip = qtrue;
        if (replaceManifest && !Q_stricmp(name, replaceManifest)) skip = qtrue;
        if (DWTRV23_NameExists(central, *count, name)) skip = qtrue;

        if (skip) {
            if (compSize && !DWTRV23_SeekForward(in, compSize)) {
                ok = qfalse;
                break;
            }
            continue;
        }

        if (*count >= DWTRV23_MAX_ENTRIES) {
            ri.Printf(PRINT_WARNING,
                      "DWTR AI B2 V2.3: cumulative PK3 entry limit reached.\n");
            ok = qfalse;
            break;
        }

        if (!DWTRV23_WriteStoredHeader(out, name, crc, compSize,
                                       offset, &central[*count])) {
            ok = qfalse;
            break;
        }
        if (compSize && !DWTRV23_CopyStoredData(in, out, compSize)) {
            ok = qfalse;
            break;
        }

        *offset += compSize;
        (*count)++;
        if (copiedEntries) (*copiedEntries)++;
    }

    CloseHandle(in);
    return ok;
}

static void DWTRV23_MakeLegacyPattern(char *out, int outSize,
                                      const char *home, const char *game,
                                      int zcount)
{
    char prefix[16];
    int i;

    for (i = 0; i < zcount && i < (int)sizeof(prefix) - 1; ++i) {
        prefix[i] = 'z';
    }
    prefix[i] = '\0';
    Com_sprintf(out, outSize, "%s\\%s\\%s_dwtr_*.pk3",
                home, game, prefix);
    DWTRAI_Slashes(out);
}

static qboolean DWTRV23_CopyLegacyPaks(const char *home, const char *game,
                                       HANDLE out,
                                       const char *replaceTexture,
                                       const char *replaceManifest,
                                       dwtrV23Central_t *central,
                                       int *count, DWORD *offset,
                                       int *legacyFiles, int *legacyEntries)
{
    int zcount;

    if (legacyFiles) *legacyFiles = 0;
    if (legacyEntries) *legacyEntries = 0;

    /* Highest-z names first: this preserves the user's manually repaired
     * working pack if older zz_/zzz_ duplicates of the same texture exist. */
    for (zcount = 10; zcount >= 2; --zcount) {
        char pattern[MAX_OSPATH * 2];
        WIN32_FIND_DATAA fd;
        HANDLE find;

        DWTRV23_MakeLegacyPattern(pattern, sizeof(pattern),
                                  home, game, zcount);
        find = FindFirstFileA(pattern, &fd);
        if (find == INVALID_HANDLE_VALUE) {
            continue;
        }

        do {
            char path[MAX_OSPATH * 2];
            int copied = 0;

            if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                continue;
            }

            Com_sprintf(path, sizeof(path), "%s\\%s\\%s",
                        home, game, fd.cFileName);
            DWTRAI_Slashes(path);

            if (!DWTRV23_CopyArchiveEntries(path, out,
                                            replaceTexture, replaceManifest,
                                            central, count, offset, &copied)) {
                FindClose(find);
                return qfalse;
            }

            if (legacyFiles) (*legacyFiles)++;
            if (legacyEntries) (*legacyEntries) += copied;
        } while (FindNextFileA(find, &fd));

        FindClose(find);
    }

    return qtrue;
}

static void DWTRV23_DeleteLegacyPaks(const char *home, const char *game)
{
    int zcount;

    for (zcount = 2; zcount <= 10; ++zcount) {
        char pattern[MAX_OSPATH * 2];
        WIN32_FIND_DATAA fd;
        HANDLE find;

        DWTRV23_MakeLegacyPattern(pattern, sizeof(pattern),
                                  home, game, zcount);
        find = FindFirstFileA(pattern, &fd);
        if (find == INVALID_HANDLE_VALUE) {
            continue;
        }

        do {
            char path[MAX_OSPATH * 2];

            if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                continue;
            }

            Com_sprintf(path, sizeof(path), "%s\\%s\\%s",
                        home, game, fd.cFileName);
            DWTRAI_Slashes(path);

            if (DeleteFileA(path)) {
                ri.Printf(PRINT_ALL,
                          "DWTR AI B2 V2.3: migrated+removed legacy pack %s\n",
                          path);
            } else {
                ri.Printf(PRINT_WARNING,
                          "DWTR AI B2 V2.3: legacy pack retained (delete failed) %s winerr=%lu\n",
                          path, (unsigned long)GetLastError());
            }
        } while (FindNextFileA(find, &fd));

        FindClose(find);
    }
}

static qboolean DWTRV23_WriteCumulativePK3(const char *sourcePhysical,
                                           const char *targetPhysical,
                                           const char *home,
                                           const char *game,
                                           const char *texturePath,
                                           const byte *textureData,
                                           int textureLen,
                                           const char *manifestPath,
                                           const byte *manifestData,
                                           int manifestLen,
                                           int *finalEntries,
                                           int *migratedPaks)
{
    char tmpPath[MAX_OSPATH * 2];
    HANDLE out = INVALID_HANDLE_VALUE;
    dwtrV23Central_t *central = NULL;
    int count = 0;
    DWORD offset = 0;
    int copied = 0;
    int legacyFiles = 0;
    int legacyEntries = 0;
    int i;
    DWORD centralOffset, centralSize = 0;
    byte end[22];
    qboolean ok = qfalse;

    if (finalEntries) *finalEntries = 0;
    if (migratedPaks) *migratedPaks = 0;

    central = (dwtrV23Central_t *)ri.Z_Malloc(
        sizeof(dwtrV23Central_t) * DWTRV23_MAX_ENTRIES);
    Com_Memset(central, 0,
               sizeof(dwtrV23Central_t) * DWTRV23_MAX_ENTRIES);

    Com_sprintf(tmpPath, sizeof(tmpPath), "%s.tmp", targetPhysical);
    out = CreateFileA(tmpPath, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                      FILE_ATTRIBUTE_NORMAL, NULL);
    if (out == INVALID_HANDLE_VALUE) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.3: cannot create cumulative temp pack %s winerr=%lu.\n",
                  tmpPath, (unsigned long)GetLastError());
        goto done;
    }

    /* Existing cumulative pack has first priority. The texture/manifest being
     * saved now are intentionally omitted and re-added at the end. */
    if (sourcePhysical && sourcePhysical[0] &&
        !DWTRV23_CopyArchiveEntries(sourcePhysical, out,
                                    texturePath, manifestPath,
                                    central, &count, &offset, &copied)) {
        goto done;
    }

    /* One-time transparent migration of old one-texture-per-PK3 files. */
    if (!DWTRV23_CopyLegacyPaks(home, game, out,
                                texturePath, manifestPath,
                                central, &count, &offset,
                                &legacyFiles, &legacyEntries)) {
        goto done;
    }

    if (!DWTRV23_WriteMemoryEntry(out, texturePath,
                                  textureData, textureLen,
                                  &offset, central, &count) ||
        !DWTRV23_WriteMemoryEntry(out, manifestPath,
                                  manifestData, manifestLen,
                                  &offset, central, &count)) {
        goto done;
    }

    centralOffset = offset;
    for (i = 0; i < count; ++i) {
        if (!DWTRV2_WriteAll(out, central[i].bytes,
                             (DWORD)central[i].len)) {
            goto done;
        }
        centralSize += (DWORD)central[i].len;
    }

    Com_Memset(end, 0, sizeof(end));
    DWTR_Put32(end + 0, 0x06054b50);
    DWTR_Put16(end + 8, (unsigned int)count);
    DWTR_Put16(end + 10, (unsigned int)count);
    DWTR_Put32(end + 12, centralSize);
    DWTR_Put32(end + 16, centralOffset);

    if (!DWTRV2_WriteAll(out, end, sizeof(end))) {
        goto done;
    }

    FlushFileBuffers(out);
    CloseHandle(out);
    out = INVALID_HANDLE_VALUE;

    if (!MoveFileExA(tmpPath, targetPhysical,
                     MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.3: cumulative PK3 atomic replace failed winerr=%lu.\n",
                  (unsigned long)GetLastError());
        DeleteFileA(tmpPath);
        goto done;
    }

    /* Delete old per-texture packs only after the new cumulative archive has
     * been completely written, closed, flushed and atomically installed. */
    if (legacyFiles > 0) {
        DWTRV23_DeleteLegacyPaks(home, game);
    }

    if (finalEntries) *finalEntries = count;
    if (migratedPaks) *migratedPaks = legacyFiles;
    ok = qtrue;

done:
    if (out != INVALID_HANDLE_VALUE) {
        CloseHandle(out);
    }
    if (!ok) {
        DeleteFileA(tmpPath);
    }
    if (central) {
        ri.Free(central);
    }
    return ok;
}
#endif /* _WIN32 */

void R_DWTextureSaveV23_f(void)
{
#ifdef _WIN32
    char internal[MAX_QPATH];
    char finalPhysical[MAX_OSPATH * 2];
    char pendingPhysical[MAX_OSPATH * 2];
    char sourcePhysical[MAX_OSPATH * 2];
    char targetPhysical[MAX_OSPATH * 2];
    char manifestQ[MAX_QPATH];
    char manifestInternal[MAX_QPATH];
    char manifest[1600];
    const char *ext;
    const char *home;
    const char *game;
    byte *encoded = NULL;
    int encodedLen = 0;
    unsigned int hash;
    const dwtrV2Candidate_t *cand;
    int finalEntries = 0;
    int migratedPaks = 0;
    qboolean finalExists;
    qboolean pendingExists;
    qboolean usingPending = qfalse;

    if (!s_dwtr.selected || s_dwtrv2.count <= 0 || !s_dwtr.original) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.3: no candidate to save.\n");
        return;
    }

    cand = &s_dwtrv2.c[s_dwtrv2.current];
    if (!cand->pixels || !cand->image) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.3: current candidate is invalid.\n");
        return;
    }

    Q_strncpyz(internal, s_dwtr.original->imgName, sizeof(internal));
    ext = strrchr(internal, '.');
    if (!ext) {
        if ((int)strlen(internal) + 4 >= MAX_QPATH) {
            ri.Printf(PRINT_WARNING,
                      "DWTR AI B2 V2.3: texture path too long.\n");
            return;
        }
        Q_strcat(internal, sizeof(internal), ".tga");
        ext = ".tga";
    }

    if (!Q_stricmp(ext, ".tga")) {
        encoded = DWTR_EncodeTGA(cand->pixels, cand->width,
                                 cand->height, &encodedLen);
    } else if (!Q_stricmp(ext, ".jpg") || !Q_stricmp(ext, ".jpeg")) {
        encoded = DWTRV2_EncodeJPGCorrect(cand->pixels, cand->width,
                                          cand->height, &encodedLen);
    } else {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.3: cumulative save supports TGA/JPG source paths; %s refused.\n",
                  ext);
        return;
    }

    if (!encoded || encodedLen <= 0) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.3: candidate encoding failed.\n");
        return;
    }

    hash = DWTR_HashPath(internal);
    Com_sprintf(manifestQ, sizeof(manifestQ),
                "texture_restoration/dwtr_%08x_v23.txt", hash);
    Com_sprintf(manifestInternal, sizeof(manifestInternal),
                "dwtr/manifest_%08x.txt", hash);

    Com_sprintf(manifest, sizeof(manifest),
        "DarkWolf Local AI Texture Restoration B2 V2.3\n"
        "pack %s\n"
        "source %s\n"
        "replacement %s\n"
        "variant %s\n"
        "aiPercent %d\n"
        "size %d %d\n"
        "model %s\n"
        "orientation canonical_top_down_roundtrip\n"
        "persistence single_cumulative_pk3\n"
        "replacePolicy texture_qpath_unique\n"
        "network no\n"
        "telemetry no\n",
        DWTRV23_PACK_NAME,
        s_dwtr.original->imgName, internal,
        cand->label, cand->aiPercent,
        cand->width, cand->height, DWTR_AI_MODEL);

    home = DWTRAI_CvarString("fs_homepath");
    if (!home[0]) home = DWTRAI_CvarString("fs_basepath");
    game = DWTRAI_GameDir();
    DWTRAI_PhysicalPath(finalPhysical, sizeof(finalPhysical),
                        home, game, DWTRV23_PACK_NAME);
    Com_sprintf(pendingPhysical, sizeof(pendingPhysical),
                "%s.pending", finalPhysical);

    finalExists = DWTRAI_IsFile(finalPhysical);
    pendingExists = DWTRAI_IsFile(pendingPhysical);

    /* ioRTCW keeps loaded PK3 handles open. Never try to replace a pack that
     * may already be mounted. If a final cumulative pack exists, rebuild into
     * one non-PK3 pending file. Repeated saves in the same session update that
     * same pending archive. FS startup promotes it before scanning PK3 files. */
    if (pendingExists) {
        Q_strncpyz(sourcePhysical, pendingPhysical, sizeof(sourcePhysical));
        Q_strncpyz(targetPhysical, pendingPhysical, sizeof(targetPhysical));
        usingPending = qtrue;
    } else if (finalExists) {
        Q_strncpyz(sourcePhysical, finalPhysical, sizeof(sourcePhysical));
        Q_strncpyz(targetPhysical, pendingPhysical, sizeof(targetPhysical));
        usingPending = qtrue;
    } else {
        sourcePhysical[0] = '\0';
        Q_strncpyz(targetPhysical, finalPhysical, sizeof(targetPhysical));
    }

    if (!DWTRV23_WriteCumulativePK3(sourcePhysical, targetPhysical,
                                    home, game,
                                    internal, encoded, encodedLen,
                                    manifestInternal,
                                    (const byte *)manifest,
                                    (int)strlen(manifest),
                                    &finalEntries, &migratedPaks)) {
        ri.Free(encoded);
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.3: cumulative PK3 update failed safely; previous pack remains intact.\n");
        return;
    }

    ri.Free(encoded);
    ri.FS_WriteFile(manifestQ, manifest, (int)strlen(manifest));
    DWTRV2_Activate(s_dwtrv2.current);

    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2.3: SAVED %s variant=%s into cumulative %s.\n",
              internal, cand->label, DWTRV23_PACK_NAME);
    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2.3: cumulative PK3=%s entries=%d migratedLegacyPaks=%d.\n",
              targetPhysical, finalEntries, migratedPaks);
    if (usingPending) {
        ri.Printf(PRINT_ALL,
                  "DWTR AI B2 V2.3: main cumulative PK3 is currently mounted; update staged safely and will be promoted on next startup.\n");
    } else {
        ri.Printf(PRINT_ALL,
                  "DWTR AI B2 V2.3: first cumulative PK3 created; restart loads all saved replacements.\n");
    }
    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2.3: future accepted textures use this same cumulative pack; no per-texture PK3 files are created.\n");
#else
    ri.Printf(PRINT_WARNING,
              "DWTR AI B2 V2.3: Win64 cumulative save backend only.\n");
#endif
}
