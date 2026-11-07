/* DarkWolf Original Texture Restoration V1 - image-side offline 4x restoration.
 * Intentionally no network, no telemetry, no shader/material changes. */
static void DWTR_ClampDetail(byte *p, int n)
{
    int i, x, y, c;
    byte *copy;
    if (!p || n <= 2) return;
    copy = (byte *)ri.Z_Malloc(n * n * 4);
    Com_Memcpy(copy, p, n * n * 4);
    for (y = 1; y < n - 1; ++y) {
        for (x = 1; x < n - 1; ++x) {
            int at = (y * n + x) * 4;
            for (c = 0; c < 3; ++c) {
                int center = copy[at+c];
                int avg = (copy[at-4+c] + copy[at+4+c] +
                           copy[at-n*4+c] + copy[at+n*4+c] + 2) >> 2;
                int delta = (center - avg) * 22 / 100;
                if (delta > 10) delta = 10;
                if (delta < -10) delta = -10;
                p[at+c] = (byte)CLAMP(center + delta, 0, 255);
            }
        }
    }
    ri.Free(copy);
}

static void DWTR_ClampDetailRect(byte *p, int w, int h)
{
    int x, y, c;
    byte *copy;
    if (!p || w <= 2 || h <= 2) return;
    copy = (byte *)ri.Z_Malloc(w * h * 4);
    Com_Memcpy(copy, p, w * h * 4);
    for (y = 1; y < h - 1; ++y) {
        for (x = 1; x < w - 1; ++x) {
            int at = (y * w + x) * 4;
            for (c = 0; c < 3; ++c) {
                int center = copy[at+c];
                int avg = (copy[at-4+c] + copy[at+4+c] +
                           copy[at-w*4+c] + copy[at+w*4+c] + 2) >> 2;
                int delta = (center - avg) * 22 / 100;
                if (delta > 10) delta = 10;
                if (delta < -10) delta = -10;
                p[at+c] = (byte)CLAMP(center + delta, 0, 255);
            }
        }
    }
    ri.Free(copy);
}

qboolean R_DWTextureRestoreBuild(image_t *source, image_t **outImage,
                                 byte **outPixels, int *outWidth, int *outHeight)
{
    byte *pic = NULL, *work = NULL;
    int width = 0, height = 0, numMips = 0, finalWidth, finalHeight;
    GLenum picFormat = GL_RGBA8;
    imgFlags_t flags;
    static unsigned int serial = 0;
    char name[MAX_QPATH];

    if (!source || !outImage || !outPixels || !outWidth || !outHeight) return qfalse;
    *outImage = NULL; *outPixels = NULL; *outWidth = *outHeight = 0;
    if (!source->imgName[0] || source->imgName[0] == '*') return qfalse;

    R_LoadImage(source->imgName, &pic, &width, &height, &picFormat, &numMips);
    if (!pic || width < 2 || height < 2) {
        if (pic) ri.Free(pic);
        return qfalse;
    }
    if (picFormat != GL_RGBA8 && picFormat != GL_SRGB8_ALPHA8_EXT) {
        ri.Printf(PRINT_WARNING, "DWTR: %s is not an RGBA source image; restore refused.\n", source->imgName);
        ri.Free(pic);
        return qfalse;
    }

    finalWidth = width * 4;
    finalHeight = height * 4;
    if (finalWidth > glConfig.maxTextureSize || finalHeight > glConfig.maxTextureSize) {
        ri.Printf(PRINT_WARNING, "DWTR: 4x %dx%d exceeds GPU max %d for %s.\n",
                  finalWidth, finalHeight, glConfig.maxTextureSize, source->imgName);
        ri.Free(pic);
        return qfalse;
    }

    work = (byte *)ri.Z_Malloc(finalWidth * finalHeight * 4);
    Com_Memset(work, 0, finalWidth * finalHeight * 4);
    Com_Memcpy(work, pic, width * height * 4);
    ri.Free(pic);

    /* Reuse Rend2's edge-directed FCBI path, but only for the selected texture.
     * YCoCg keeps chroma stable while geometry/detail is reconstructed. */
    RGBAtoYCoCgA(work, work, width, height);
    FCBIByBlock(work, width * 2, height * 2,
                (source->flags & IMGFLAG_CLAMPTOEDGE) ? qtrue : qfalse, qfalse);
    FCBIByBlock(work, finalWidth, finalHeight,
                (source->flags & IMGFLAG_CLAMPTOEDGE) ? qtrue : qfalse, qfalse);
    YCoCgAtoRGBA(work, work, finalWidth, finalHeight);

    /* Hybrid restoration: only a restrained high-frequency recovery pass.
     * It cannot repaint structure, hue, dirt, cracks or artwork. */
    DWTR_ClampDetailRect(work, finalWidth, finalHeight);

    flags = source->flags;
    flags |= IMGFLAG_NO_COMPRESSION;
    flags &= ~(IMGFLAG_PICMIP | IMGFLAG_GENNORMALMAP);
    Com_sprintf(name, sizeof(name), "*dwtr_preview_%u", ++serial);
    *outImage = R_CreateImageExt2(name, work, finalWidth, finalHeight,
                                  GL_RGBA8, 0, source->type, flags, 0, source->characterMIP);
    if (!*outImage) {
        ri.Free(work);
        return qfalse;
    }

    *outPixels = work;
    *outWidth = finalWidth;
    *outHeight = finalHeight;
    return qtrue;
}
