/*
 * DarkWolf AI Texture Studio V0.1 - opt-in renderer-side experiment.
 * This file is included at the END of SP/code/rend2/tr_image.c by apply.py.
 * No stock shader, BSP, lightmap, shadow, SSGI or post-process code is modified.
 * Single-player / world BSP selection only in this initial implementation.
 */
#define DW_TEX_SLOT_LIMIT 48
#define DW_TEX_UPLOAD_LIMIT 384
#define DW_TEX_PICK_DIST 2048.0f

typedef struct {
    image_t *image;
    GLuint originalTexnum;
    int width, height, uploadWidth, uploadHeight, internalFormat;
    qboolean active;
} dwTexSlot_t;

static dwTexSlot_t dwTexSlots[DW_TEX_SLOT_LIMIT];
static cvar_t *dwTexStudio;
static image_t *dwTexPicked;
static char dwTexPickedShader[MAX_QPATH];
static char dwTexPickedMap[MAX_QPATH];
static float dwTexPickedUV[2];
static unsigned int dwTexRequestId;
static unsigned int dwTexLastReadyId;
static int dwTexLastPoll;
static int dwTexUploadCount;

static qboolean DW_TexAllowed( void ) {
    if ( !dwTexStudio || !dwTexStudio->integer ) {
        ri.Printf( PRINT_ALL, "DW Texture Studio disabled: /set r_dwTexStudio 1\n" );
        return qfalse;
    }
    return qtrue;
}

static qboolean DW_TexSafePath( const char *s ) {
    size_t i, n;
    if ( !s || Q_stricmpn( s, "dwtex/", 6 ) )
        return qfalse;
    n = strlen(s);
    if ( n <= 10 || n >= MAX_QPATH || Q_stricmp(s + n - 4, ".png") )
        return qfalse;
    if ( strstr(s, "..") )
        return qfalse;
    for ( i = 6; i < n; ++i ) {
        int c = (unsigned char)s[i];
        if ( !(c >= 'a' && c <= 'z') &&
             !(c >= 'A' && c <= 'Z') &&
             !(c >= '0' && c <= '9') &&
             c != '_' && c != '-' && c != '.' )
            return qfalse;
    }
    return qtrue;
}

/* Positive, double-sided Moller-Trumbore test; result is in world units. */
static qboolean DW_TexRayTriangle( const vec3_t origin, const vec3_t ray,
    const srfVert_t *a, const srfVert_t *b, const srfVert_t *c,
    float *distance, float *u, float *v ) {
    vec3_t e1, e2, p, t, q;
    float det, invDet, ub, vb, d;
    VectorSubtract(b->xyz, a->xyz, e1);
    VectorSubtract(c->xyz, a->xyz, e2);
    CrossProduct(ray, e2, p);
    det = DotProduct(e1, p);
    if ( det > -0.00001f && det < 0.00001f ) return qfalse;
    invDet = 1.0f / det;
    VectorSubtract(origin, a->xyz, t);
    ub = DotProduct(t, p) * invDet;
    if ( ub < 0.0f || ub > 1.0f ) return qfalse;
    CrossProduct(t, e1, q);
    vb = DotProduct(ray, q) * invDet;
    if ( vb < 0.0f || ub + vb > 1.0f ) return qfalse;
    d = DotProduct(e2, q) * invDet;
    if ( d < 0.001f || d >= *distance ) return qfalse;
    *distance = d;
    *u = ub;
    *v = vb;
    return qtrue;
}

static image_t *DW_TexDiffuseImage( const shader_t *shader ) {
    int i;
    if ( !shader || shader->isSky || shader->isPortal || shader->defaultShader )
        return NULL;
    for ( i = 0; i < shader->numUnfoggedPasses; ++i ) {
        const shaderStage_t *stage = shader->stages[i];
        const textureBundle_t *bundle;
        image_t *img;
        if ( !stage || !stage->active ) continue;
        bundle = &stage->bundle[TB_DIFFUSEMAP];
        if ( bundle->isLightmap || bundle->isVideoMap || bundle->numImageAnimations != 1 )
            continue;
        img = bundle->image[0];
        if ( !img || img->imgName[0] == '*' || img->type != IMGTYPE_COLORALPHA ||
             (img->flags & IMGFLAG_CUBEMAP) ) continue;
        return img;
    }
    return NULL;
}

static void DW_TexPick_f( void ) {
    int i, j, count = 0;
    float best = DW_TEX_PICK_DIST, hitU = 0, hitV = 0;
    msurface_t *found = NULL;
    srfBspSurface_t *foundMesh = NULL;
    int foundTri = -1;
    if ( !DW_TexAllowed() ) return;
    if ( !tr.registered || !tr.world || tr.world->numWorldSurfaces <= 0 ) {
        ri.Printf(PRINT_ALL, "DW Texture Studio: no BSP world available.\n");
        return;
    }
    dwTexPicked = NULL;
    for ( i = 0; i < tr.world->numWorldSurfaces; ++i ) {
        msurface_t *surf = &tr.world->surfaces[i];
        srfBspSurface_t *mesh;
        surfaceType_t type;
        image_t *candidate;
        if ( !surf->data || !surf->shader ) continue;
        type = *surf->data;
        if ( type != SF_FACE && type != SF_GRID && type != SF_TRIANGLES )
            continue;
        candidate = DW_TexDiffuseImage(surf->shader);
        if ( !candidate ) continue;
        mesh = (srfBspSurface_t *)surf->data;
        if ( !mesh->verts || !mesh->indexes || mesh->numIndexes < 3 ) continue;
        for ( j = 0; j + 2 < mesh->numIndexes; j += 3 ) {
            glIndex_t ia = mesh->indexes[j], ib = mesh->indexes[j+1], ic = mesh->indexes[j+2];
            float dist = best, u, v;
            if ( ia >= mesh->numVerts || ib >= mesh->numVerts || ic >= mesh->numVerts )
                continue;
            if ( DW_TexRayTriangle(tr.refdef.vieworg, tr.refdef.viewaxis[0],
                &mesh->verts[ia], &mesh->verts[ib], &mesh->verts[ic], &dist, &u, &v) ) {
                best = dist;
                hitU = u;
                hitV = v;
                found = surf;
                foundMesh = mesh;
                foundTri = j;
            }
        }
        ++count;
    }
    if ( !found || !foundMesh || foundTri < 0 ) {
        ri.Printf(PRINT_ALL, "DW Texture Studio: no supported BSP material under the crosshair.\n");
        return;
    }
    dwTexPicked = DW_TexDiffuseImage(found->shader);
    if ( !dwTexPicked ) return;
    Q_strncpyz(dwTexPickedShader, found->shader->name, sizeof(dwTexPickedShader));
    Q_strncpyz(dwTexPickedMap, tr.world->baseName, sizeof(dwTexPickedMap));
    {
        const srfVert_t *a = &foundMesh->verts[foundMesh->indexes[foundTri]];
        const srfVert_t *b = &foundMesh->verts[foundMesh->indexes[foundTri+1]];
        const srfVert_t *c = &foundMesh->verts[foundMesh->indexes[foundTri+2]];
        float w = 1.0f - hitU - hitV;
        dwTexPickedUV[0] = w * a->st[0] + hitU * b->st[0] + hitV * c->st[0];
        dwTexPickedUV[1] = w * a->st[1] + hitU * b->st[1] + hitV * c->st[1];
    }
    ri.Printf(PRINT_ALL,
        "DW Texture PICK map=%s shader=%s diffuse=%s original=%dx%d hit=%.1f UV=(%.3f,%.3f) checked=%d\n",
        dwTexPickedMap, dwTexPickedShader, dwTexPicked->imgName,
        dwTexPicked->width, dwTexPicked->height, best,
        dwTexPickedUV[0], dwTexPickedUV[1], count);
}

static dwTexSlot_t *DW_TexSlot( image_t *image ) {
    int i;
    dwTexSlot_t *freeSlot = NULL;
    for ( i = 0; i < DW_TEX_SLOT_LIMIT; ++i ) {
        if ( dwTexSlots[i].image == image ) return &dwTexSlots[i];
        if ( !dwTexSlots[i].image && !freeSlot ) freeSlot = &dwTexSlots[i];
    }
    if ( freeSlot ) freeSlot->image = image;
    return freeSlot;
}

static void DW_TexRevertSlot( dwTexSlot_t *s ) {
    GLuint transient;
    if ( !s || !s->active || !s->image ) return;
    transient = s->image->texnum;
    s->image->texnum = s->originalTexnum;
    s->image->width = s->width;
    s->image->height = s->height;
    s->image->uploadWidth = s->uploadWidth;
    s->image->uploadHeight = s->uploadHeight;
    s->image->internalFormat = s->internalFormat;
    s->originalTexnum = 0;
    s->active = qfalse;
    qglDeleteTextures(1, &transient);
    GL_BindNullTextures();
}

static qboolean DW_TexPreview( image_t *target, const char *path ) {
    int width, height, mips;
    GLenum format;
    byte *pixels = NULL;
    image_t *created;
    dwTexSlot_t *slot;
    GLuint previous;
    char tag[MAX_QPATH];
    int originalW, originalH;
    if ( !DW_TexAllowed() || !target || !DW_TexSafePath(path) ) {
        ri.Printf(PRINT_ALL,"DW Texture Studio: invalid target or preview path (dwtex/*.png only).\n");
        return qfalse;
    }
    if ( !tr.registered || target->type != IMGTYPE_COLORALPHA ||
         (target->flags & IMGFLAG_CUBEMAP) || target->imgName[0] == '*' )
        return qfalse;
    slot = DW_TexSlot(target);
    if ( !slot || tr.numImages >= MAX_DRAWIMAGES - 8 ||
         dwTexUploadCount >= DW_TEX_UPLOAD_LIMIT ) {
        ri.Printf(PRINT_ALL,"DW Texture Studio: session preview budget exhausted; originals unchanged.\n");
        return qfalse;
    }
    R_LoadImage(path, &pixels, &width, &height, &format, &mips);
    if ( !pixels ) {
        ri.Printf(PRINT_ALL,"DW Texture Studio: candidate not found: %s\n", path);
        return qfalse;
    }
    originalW = slot->active ? slot->width : target->width;
    originalH = slot->active ? slot->height : target->height;
    if ( format != GL_RGBA8 || mips > 1 || width <= 0 || height <= 0 ||
         width > glConfig.maxTextureSize || height > glConfig.maxTextureSize ||
         (long long)width * originalH != (long long)height * originalW ) {
        ri.Printf(PRINT_ALL,"DW Texture Studio: rejected %dx%d candidate (must be RGBA, within GPU limit, exact aspect ratio %dx%d).\n",
            width, height, originalW, originalH);
        ri.Free(pixels);
        return qfalse;
    }
    R_IssuePendingRenderCommands();
    Com_sprintf(tag, sizeof(tag), "*dw_ai_preview_%d", dwTexUploadCount + 1);
    created = R_CreateImageExt2(tag, pixels, width, height, GL_RGBA8, 0,
         target->type, target->flags & ~IMGFLAG_GENNORMALMAP, 0, target->characterMIP);
    ri.Free(pixels);
    if ( !created ) return qfalse;

    if ( !slot->active ) {
        slot->width = target->width;
        slot->height = target->height;
        slot->uploadWidth = target->uploadWidth;
        slot->uploadHeight = target->uploadHeight;
        slot->internalFormat = target->internalFormat;
        slot->originalTexnum = target->texnum;
    }
    previous = target->texnum;
    target->texnum = created->texnum;
    target->width = created->width;
    target->height = created->height;
    target->uploadWidth = created->uploadWidth;
    target->uploadHeight = created->uploadHeight;
    target->internalFormat = created->internalFormat;
    created->texnum = 0;  /* retained hunk record is deliberately unbound */
    if ( slot->active ) qglDeleteTextures(1, &previous);
    slot->active = qtrue;
    ++dwTexUploadCount;
    GL_BindNullTextures();
    ri.Printf(PRINT_ALL,"DW Texture Studio: LIVE GPU preview %s -> %s (%dx%d), no vid_restart. /dw_tex_revert to undo.\n",
         target->imgName, path, width, height);
    return qtrue;
}

static void DW_TexPreview_f( void ) {
    if ( ri.Cmd_Argc() != 2 ) {
        ri.Printf(PRINT_ALL, "Usage: /dw_tex_preview dwtex/name.png (after /dw_tex_pick)\n");
        return;
    }
    if ( !dwTexPicked || !tr.world || Q_stricmp(dwTexPickedMap,tr.world->baseName) ) {
        ri.Printf(PRINT_ALL,"DW Texture Studio: pick a supported material on this map first.\n");
        return;
    }
    DW_TexPreview(dwTexPicked, ri.Cmd_Argv(1));
}

static void DW_TexRevert_f( void ) {
    dwTexSlot_t *slot;
    if ( !DW_TexAllowed() || !dwTexPicked ) return;
    slot = DW_TexSlot(dwTexPicked);
    if ( !slot || !slot->active ) {
        ri.Printf(PRINT_ALL,"DW Texture Studio: selected texture already original.\n");
        return;
    }
    R_IssuePendingRenderCommands();
    DW_TexRevertSlot(slot);
    ri.Printf(PRINT_ALL,"DW Texture Studio: original restored: %s\n",dwTexPicked->imgName);
}

static void DW_TexRevertAll_f( void ) {
    int i, count=0;
    if ( !DW_TexAllowed() ) return;
    R_IssuePendingRenderCommands();
    for ( i = 0; i < DW_TEX_SLOT_LIMIT; ++i ) {
        if ( dwTexSlots[i].active ) {
            DW_TexRevertSlot(&dwTexSlots[i]);
            ++count;
        }
    }
    ri.Printf(PRINT_ALL,"DW Texture Studio: reverted %d overrides.\n",count);
}

static void DW_TexRequest_f( void ) {
    char job[1024];
    const char *mode = ri.Cmd_Argc() > 1 ? ri.Cmd_Argv(1) : "original";
    int scale = ri.Cmd_Argc() > 2 ? atoi(ri.Cmd_Argv(2)) : 2;
    int n;
    if ( !DW_TexAllowed() ) return;
    if ( !dwTexPicked || !tr.world || Q_stricmp(dwTexPickedMap,tr.world->baseName) ) {
        ri.Printf(PRINT_ALL,"DW Texture Studio: use /dw_tex_pick before requesting AI.\n");
        return;
    }
    if ( (Q_stricmp(mode,"original") && Q_stricmp(mode,"art")) ||
         (scale != 2 && scale != 4) ) {
        ri.Printf(PRINT_ALL,"Usage: /dw_tex_generate original|art 2|4\n");
        return;
    }
    ++dwTexRequestId;
    Com_sprintf(job,sizeof(job),
        "{\"version\":1,\"id\":%u,\"map\":\"%s\",\"shader\":\"%s\","
        "\"texture\":\"%s\",\"width\":%d,\"height\":%d,"
        "\"mode\":\"%s\",\"scale\":%d,\"hit_uv\":[%.6f,%.6f]}\n",
        dwTexRequestId,dwTexPickedMap,dwTexPickedShader,
        dwTexPicked->imgName,dwTexPicked->width,dwTexPicked->height,
        mode,scale,dwTexPickedUV[0],dwTexPickedUV[1]);
    n = (int)strlen(job);
    if (n <= 0 || n >= (int)sizeof(job) - 1) {
        ri.Printf(PRINT_ALL,"DW Texture Studio: request too large.\n");
        return;
    }
    ri.FS_WriteFile("dwtex/request.json",job,n);
    ri.Printf(PRINT_ALL,"DW Texture Studio: request %u (%s x%d) written; local AI worker can process it while the game runs.\n",
        dwTexRequestId,mode,scale);
}

static void DW_TexStatus_f( void ) {
    int i, active=0;
    for (i=0;i<DW_TEX_SLOT_LIMIT;i++) active += !!dwTexSlots[i].active;
    ri.Printf(PRINT_ALL,"DW Texture Studio: %s; map=%s, selected=%s, shader=%s, overrides=%d, previews=%d/%d.\n",
        dwTexStudio && dwTexStudio->integer ? "enabled" : "disabled",
        tr.world ? tr.world->baseName : "none",
        dwTexPicked ? dwTexPicked->imgName : "none",
        dwTexPicked ? dwTexPickedShader : "none",
        active,dwTexUploadCount,DW_TEX_UPLOAD_LIMIT);
}

void R_DWTextureStudio_Tick( void ) {
    int now, len;
    void *buf = NULL;
    char path[MAX_QPATH];
    unsigned int id = 0;
    if ( !dwTexStudio || !dwTexStudio->integer || !dwTexPicked || !tr.world ||
         Q_stricmp(dwTexPickedMap,tr.world->baseName) ) return;
    now = ri.Milliseconds();
    if ( now - dwTexLastPoll < 500 ) return;
    dwTexLastPoll = now;
    len = ri.FS_ReadFile("dwtex/ready.txt",&buf);
    if ( len > 0 && buf ) {
        char local[160];
        if ( len >= (int)sizeof(local) ) len = sizeof(local)-1;
        memcpy(local,buf,len); local[len] = '\0';
        if ( sscanf(local,"%u %63s",&id,path) == 2 &&
             id == dwTexRequestId && id != dwTexLastReadyId &&
             DW_TexSafePath(path) ) {
            if ( DW_TexPreview(dwTexPicked,path) )
                dwTexLastReadyId = id;
        }
    }
    if ( buf ) ri.FS_FreeFile(buf);
}

void R_DWTextureStudio_Init( void ) {
    memset(dwTexSlots,0,sizeof(dwTexSlots));
    dwTexPicked = NULL;
    dwTexPickedShader[0] = '\0';
    dwTexPickedMap[0] = '\0';
    dwTexUploadCount = 0;
    dwTexLastPoll = 0;
    dwTexLastReadyId = 0;
    dwTexRequestId = 0;
    dwTexStudio = ri.Cvar_Get("r_dwTexStudio","0",CVAR_ARCHIVE);
    ri.Cmd_AddCommand("dw_tex_pick",DW_TexPick_f);
    ri.Cmd_AddCommand("dw_tex_generate",DW_TexRequest_f);
    ri.Cmd_AddCommand("dw_tex_preview",DW_TexPreview_f);
    ri.Cmd_AddCommand("dw_tex_revert",DW_TexRevert_f);
    ri.Cmd_AddCommand("dw_tex_revert_all",DW_TexRevertAll_f);
    ri.Cmd_AddCommand("dw_tex_status",DW_TexStatus_f);
}

void R_DWTextureStudio_Shutdown( void ) {
    int i;
    ri.Cmd_RemoveCommand("dw_tex_pick");
    ri.Cmd_RemoveCommand("dw_tex_generate");
    ri.Cmd_RemoveCommand("dw_tex_preview");
    ri.Cmd_RemoveCommand("dw_tex_revert");
    ri.Cmd_RemoveCommand("dw_tex_revert_all");
    ri.Cmd_RemoveCommand("dw_tex_status");
    if (tr.registered) {
        R_IssuePendingRenderCommands();
        for (i=0;i<DW_TEX_SLOT_LIMIT;i++) {
            if (dwTexSlots[i].active && dwTexSlots[i].originalTexnum) {
                qglDeleteTextures(1,&dwTexSlots[i].originalTexnum);
                dwTexSlots[i].originalTexnum = 0;
            }
        }
    }
    dwTexPicked = NULL;
    dwTexStudio = NULL;
}
