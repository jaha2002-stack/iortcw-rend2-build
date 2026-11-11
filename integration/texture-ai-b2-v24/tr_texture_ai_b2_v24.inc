/* DARKWOLF_TEXTURE_AI_B2_V24
 * Universal Texture Picker.
 *
 * Scope is intentionally narrow:
 * - preserve B2 V2.3 AI generation and cumulative PK3 byte-for-byte at source level;
 * - extend /dw_tex_pick to WORLD, inline BRUSH (including scaled axes), and
 *   vertex-animated MOD_MESH (MD3/MDC) entities;
 * - resolve customShader/customSkin for model surfaces;
 * - keep sky, water and other liquid/portal surfaces outside the supported set.
 *
 * Skeletal MOD_MDS/MOD_MDR/MOD_IQM are deliberately not enabled in V2.4.
 */

static int s_dwtrv24PickEntity = REFENTITYNUM_WORLD;
static char s_dwtrv24PickModel[MAX_QPATH] = "WORLD";
static char s_dwtrv24PickSource[16] = "WORLD";
static char s_dwtrv24PickSurface[MAX_QPATH] = "";
static char s_dwtrv24PickModelType[24] = "WORLD";

static shader_t *DWTRV24_ResolveShader(shader_t *sh)
{
    if (!sh) {
        return NULL;
    }
    if (sh->remappedShader && sh->remappedShader != sh) {
        sh = sh->remappedShader;
    }
    return sh;
}

static qboolean DWTRV24_ShaderAllowed(shader_t *shader, const char **reason)
{
    shader = DWTRV24_ResolveShader(shader);
    if (reason) *reason = "OK";

    if (!shader) {
        if (reason) *reason = "NO_SHADER";
        return qfalse;
    }
    if (shader->isSky) {
        if (reason) *reason = "SKY_EXCLUDED";
        return qfalse;
    }
    if (shader->contentFlags & CONTENTS_WATER) {
        if (reason) *reason = "WATER_EXCLUDED";
        return qfalse;
    }
    if (shader->contentFlags & (CONTENTS_SLIME | CONTENTS_LAVA)) {
        if (reason) *reason = "LIQUID_EXCLUDED";
        return qfalse;
    }
    if (shader->isPortal || shader->sort == SS_PORTAL) {
        if (reason) *reason = "PORTAL_EXCLUDED";
        return qfalse;
    }

    return qtrue;
}

static shaderStage_t *DWTRV24_DiffuseStage(shader_t *shader,
                                            image_t **outImage,
                                            const char **reason)
{
    shaderStage_t *stage;
    shader = DWTRV24_ResolveShader(shader);

    if (outImage) *outImage = NULL;
    if (!DWTRV24_ShaderAllowed(shader, reason)) {
        return NULL;
    }

    stage = DWTR_DiffuseStage(shader, outImage);
    if (!stage || !outImage || !*outImage) {
        if (reason) *reason = "NO_DISK_DIFFUSE";
        return NULL;
    }

    return stage;
}

/* refEntity axis vectors may contain scale when nonNormalizedAxes is set.
 * RTCW entity axes remain orthogonal, so dot(axis)/dot(axis,axis) is the
 * correct inverse transform and keeps ray parameter t comparable to WORLD. */
static qboolean DWTRV24_WorldRayToEntity(const trRefEntity_t *ent,
                                          const vec3_t worldOrigin,
                                          const vec3_t worldDir,
                                          vec3_t localOrigin,
                                          vec3_t localDir)
{
    vec3_t delta;
    int k;

    if (!ent) {
        return qfalse;
    }

    VectorSubtract(worldOrigin, ent->e.origin, delta);
    for (k = 0; k < 3; ++k) {
        float denom = DotProduct(ent->e.axis[k], ent->e.axis[k]);
        if (denom < 0.000001f) {
            return qfalse;
        }
        localOrigin[k] = DotProduct(delta, ent->e.axis[k]) / denom;
        localDir[k] = DotProduct(worldDir, ent->e.axis[k]) / denom;
    }

    return qtrue;
}

static int DWTRV24_NormalizeFrame(int frame, int numFrames, qboolean wrap)
{
    if (numFrames <= 0) {
        return 0;
    }
    if (wrap) {
        frame %= numFrames;
        if (frame < 0) frame += numFrames;
        return frame;
    }
    if (frame < 0 || frame >= numFrames) {
        return 0;
    }
    return frame;
}

static void DWTRV24_LerpMDVPoint(const mdvVertex_t *newVert,
                                  const mdvVertex_t *oldVert,
                                  float backlerp,
                                  vec3_t out)
{
    float frontlerp = 1.0f - backlerp;
    out[0] = newVert->xyz[0] * frontlerp + oldVert->xyz[0] * backlerp;
    out[1] = newVert->xyz[1] * frontlerp + oldVert->xyz[1] * backlerp;
    out[2] = newVert->xyz[2] * frontlerp + oldVert->xyz[2] * backlerp;
}

static qboolean DWTRV24_RayMDVSurface(const mdvModel_t *mdv,
                                      const mdvSurface_t *surf,
                                      const trRefEntity_t *ent,
                                      const vec3_t localOrigin,
                                      const vec3_t localDir,
                                      float *best)
{
    const mdvVertex_t *newVerts;
    const mdvVertex_t *oldVerts;
    int frame, oldframe;
    float backlerp;
    int i;
    qboolean hit = qfalse;

    if (!mdv || !surf || !ent || !best ||
        !surf->verts || !surf->indexes ||
        surf->numVerts < 3 || surf->numIndexes < 3 ||
        mdv->numFrames <= 0) {
        return qfalse;
    }

    frame = DWTRV24_NormalizeFrame(ent->e.frame, mdv->numFrames,
                                   (ent->e.renderfx & RF_WRAP_FRAMES) ? qtrue : qfalse);
    oldframe = DWTRV24_NormalizeFrame(ent->e.oldframe, mdv->numFrames,
                                      (ent->e.renderfx & RF_WRAP_FRAMES) ? qtrue : qfalse);
    backlerp = (frame == oldframe) ? 0.0f : ent->e.backlerp;
    if (backlerp < 0.0f) backlerp = 0.0f;
    if (backlerp > 1.0f) backlerp = 1.0f;

    newVerts = surf->verts + frame * surf->numVerts;
    oldVerts = surf->verts + oldframe * surf->numVerts;

    for (i = 0; i + 2 < surf->numIndexes; i += 3) {
        int ia = (int)surf->indexes[i + 0];
        int ib = (int)surf->indexes[i + 1];
        int ic = (int)surf->indexes[i + 2];
        vec3_t a, b, c;
        float t;

        if (ia < 0 || ib < 0 || ic < 0 ||
            ia >= surf->numVerts || ib >= surf->numVerts || ic >= surf->numVerts) {
            continue;
        }

        DWTRV24_LerpMDVPoint(&newVerts[ia], &oldVerts[ia], backlerp, a);
        DWTRV24_LerpMDVPoint(&newVerts[ib], &oldVerts[ib], backlerp, b);
        DWTRV24_LerpMDVPoint(&newVerts[ic], &oldVerts[ic], backlerp, c);

        t = *best;
        if (DWTR_RayTriangle(localOrigin, localDir, a, b, c, &t) && t < *best) {
            *best = t;
            hit = qtrue;
        }
    }

    return hit;
}

static shader_t *DWTRV24_MDVShader(const trRefEntity_t *ent,
                                    const mdvSurface_t *surface)
{
    int j;

    if (!ent || !surface) {
        return NULL;
    }

    if (ent->e.customShader) {
        return R_GetShaderByHandle(ent->e.customShader);
    }

    if (ent->e.customSkin > 0 && ent->e.customSkin < tr.numSkins) {
        skin_t *skin = R_GetSkinByHandle(ent->e.customSkin);
        shader_t *shader = tr.defaultShader;

        if (!skin) {
            return shader;
        }

        for (j = 0; j < skin->numSurfaces; ++j) {
            if (!strcmp(skin->surfaces[j].name, surface->name)) {
                shader = skin->surfaces[j].shader;
                break;
            }
        }
        return shader;
    }

    if (surface->numShaderIndexes <= 0 || !surface->shaderIndexes) {
        return tr.defaultShader;
    }

    {
        int skinNum = ent->e.skinNum;
        if (skinNum < 0) skinNum = -skinNum;
        return tr.shaders[surface->shaderIndexes[skinNum % surface->numShaderIndexes]];
    }
}

static mdvModel_t *DWTRV24_GetMDV0(model_t *model)
{
    int lod;

    if (!model || model->type != MOD_MESH) {
        return NULL;
    }

    for (lod = 0; lod < MD3_MAX_LODS; ++lod) {
        if (model->mdv[lod]) {
            return model->mdv[lod];
        }
    }

    return NULL;
}

static void DWTRV24_RecordBlocked(float t, float *blockedT,
                                   char *blockedReason, int blockedReasonSize,
                                   const char *reason)
{
    if (!blockedT || !blockedReason || blockedReasonSize <= 0 || !reason) {
        return;
    }
    if (t < *blockedT) {
        *blockedT = t;
        Q_strncpyz(blockedReason, reason, blockedReasonSize);
    }
}

void R_DWTexturePickV24_f(void)
{
    int i;
    int bestSurface = -1;
    int bestEntity = REFENTITYNUM_WORLD;
    float best = 8192.0f;
    float blockedT = 8192.0f;
    char blockedReason[64] = "";
    shader_t *bestShader = NULL;
    shaderStage_t *bestStage = NULL;
    image_t *bestImage = NULL;
    const char *bestModelName = "WORLD";
    const char *bestSource = "WORLD";
    const char *bestModelType = "WORLD";
    char bestSurfaceName[MAX_QPATH] = "";
    vec3_t worldOrigin, worldDir;

    R_IssuePendingRenderCommands();

    if (!tr.world || !tr.world->surfaces || tr.world->numWorldSurfaces <= 0) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2.4: no world loaded.\n");
        return;
    }

    VectorCopy(tr.refdef.vieworg, worldOrigin);
    VectorCopy(tr.refdef.viewaxis[0], worldDir);

    /* Pass 1: static WORLD BSP. */
    for (i = 0; i < tr.world->numWorldSurfaces; ++i) {
        float t = 8192.0f;
        shader_t *candidateShader;
        shader_t *resolvedShader;
        shaderStage_t *candidateStage;
        image_t *candidateImage = NULL;
        const char *reason = "OK";

        if (!DWTR_RaySurface(&tr.world->surfaces[i], worldOrigin, worldDir, &t)) {
            continue;
        }

        candidateShader = tr.world->surfaces[i].shader;
        resolvedShader = DWTRV24_ResolveShader(candidateShader);

        if (!DWTRV24_ShaderAllowed(resolvedShader, &reason)) {
            DWTRV24_RecordBlocked(t, &blockedT, blockedReason, sizeof(blockedReason), reason);
            continue;
        }

        candidateStage = DWTRV24_DiffuseStage(resolvedShader, &candidateImage, &reason);
        if (!candidateStage || !candidateImage || t >= best) {
            continue;
        }

        best = t;
        bestSurface = i;
        bestEntity = REFENTITYNUM_WORLD;
        bestShader = resolvedShader;
        bestStage = candidateStage;
        bestImage = candidateImage;
        bestModelName = "WORLD";
        bestSource = "WORLD";
        bestModelType = "WORLD";
        bestSurfaceName[0] = '\0';
    }

    /* Pass 2: inline BSP entities: doors, rotating doors, lifts and other
     * MOD_BRUSH objects. Unlike V2.2, scaled/non-normalized axes are supported. */
    for (i = 0; i < tr.refdef.num_entities; ++i) {
        trRefEntity_t *ent = &tr.refdef.entities[i];
        model_t *model;
        bmodel_t *bmodel;
        vec3_t localOrigin, localDir;
        int s;

        if (ent->e.reType != RT_MODEL) {
            continue;
        }

        model = R_GetModelByHandle(ent->e.hModel);
        if (!model || model->type != MOD_BRUSH || !model->bmodel) {
            continue;
        }

        if (!DWTRV24_WorldRayToEntity(ent, worldOrigin, worldDir,
                                      localOrigin, localDir)) {
            continue;
        }

        bmodel = model->bmodel;
        for (s = 0; s < bmodel->numSurfaces; ++s) {
            int surfIndex = bmodel->firstSurface + s;
            msurface_t *surf;
            float t = 8192.0f;
            shader_t *candidateShader;
            shader_t *resolvedShader;
            shaderStage_t *candidateStage;
            image_t *candidateImage = NULL;
            const char *reason = "OK";

            if (surfIndex < 0 || surfIndex >= tr.world->numWorldSurfaces) {
                continue;
            }

            surf = &tr.world->surfaces[surfIndex];
            if (!DWTR_RaySurface(surf, localOrigin, localDir, &t)) {
                continue;
            }

            candidateShader = ent->e.customShader
                                ? R_GetShaderByHandle(ent->e.customShader)
                                : surf->shader;
            resolvedShader = DWTRV24_ResolveShader(candidateShader);

            if (!DWTRV24_ShaderAllowed(resolvedShader, &reason)) {
                DWTRV24_RecordBlocked(t, &blockedT, blockedReason, sizeof(blockedReason), reason);
                continue;
            }

            candidateStage = DWTRV24_DiffuseStage(resolvedShader, &candidateImage, &reason);
            if (!candidateStage || !candidateImage || t >= best) {
                continue;
            }

            best = t;
            bestSurface = surfIndex;
            bestEntity = i;
            bestShader = resolvedShader;
            bestStage = candidateStage;
            bestImage = candidateImage;
            bestModelName = model->name;
            bestSource = "BRUSH";
            bestModelType = "MOD_BRUSH";
            Q_strncpyz(bestSurfaceName, resolvedShader ? resolvedShader->name : "",
                       sizeof(bestSurfaceName));
        }
    }

    /* Pass 3: MD3/MDC vertex models. This covers model-based doors and many
     * map objects that V2.2 treated as invisible to the picker. */
    for (i = 0; i < tr.refdef.num_entities; ++i) {
        trRefEntity_t *ent = &tr.refdef.entities[i];
        model_t *model;
        mdvModel_t *mdv;
        vec3_t localOrigin, localDir;
        int s;

        if (ent->e.reType != RT_MODEL) {
            continue;
        }

        model = R_GetModelByHandle(ent->e.hModel);
        if (!model || model->type != MOD_MESH) {
            continue;
        }

        mdv = DWTRV24_GetMDV0(model);
        if (!mdv || !mdv->surfaces || mdv->numSurfaces <= 0) {
            continue;
        }

        if (!DWTRV24_WorldRayToEntity(ent, worldOrigin, worldDir,
                                      localOrigin, localDir)) {
            continue;
        }

        for (s = 0; s < mdv->numSurfaces; ++s) {
            mdvSurface_t *surface = &mdv->surfaces[s];
            float t = 8192.0f;
            shader_t *candidateShader;
            shader_t *resolvedShader;
            shaderStage_t *candidateStage;
            image_t *candidateImage = NULL;
            const char *reason = "OK";

            if (!DWTRV24_RayMDVSurface(mdv, surface, ent,
                                       localOrigin, localDir, &t)) {
                continue;
            }

            candidateShader = DWTRV24_MDVShader(ent, surface);
            resolvedShader = DWTRV24_ResolveShader(candidateShader);

            if (!DWTRV24_ShaderAllowed(resolvedShader, &reason)) {
                DWTRV24_RecordBlocked(t, &blockedT, blockedReason, sizeof(blockedReason), reason);
                continue;
            }

            candidateStage = DWTRV24_DiffuseStage(resolvedShader, &candidateImage, &reason);
            if (!candidateStage || !candidateImage || t >= best) {
                continue;
            }

            best = t;
            bestSurface = s;
            bestEntity = i;
            bestShader = resolvedShader;
            bestStage = candidateStage;
            bestImage = candidateImage;
            bestModelName = model->name;
            bestSource = "MESH";
            bestModelType = "MOD_MESH_MD3_MDC";
            Q_strncpyz(bestSurfaceName, surface->name, sizeof(bestSurfaceName));
        }
    }

    /* Never select a texture hidden behind an explicitly excluded sky/liquid/
     * portal surface. This is safer than silently picking the wall behind it. */
    if (blockedReason[0] && blockedT + 0.01f < best) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.4: nearest surface excluded reason=%s distance=%.1f; sky/water/special surfaces are intentionally unsupported.\n",
                  blockedReason, blockedT);
        return;
    }

    if (bestSurface < 0 || !bestStage || !bestImage) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.4: no safe WORLD/BRUSH/MD3-MDC diffuse texture under crosshair.\n");
        return;
    }

    R_DWTextureRestoreReset();

    s_dwtr.selected = qtrue;
    s_dwtr.surfaceIndex = bestSurface;
    s_dwtr.shader = bestShader;
    s_dwtr.stage = bestStage;
    s_dwtr.original = bestImage;

    s_dwtrv24PickEntity = bestEntity;
    Q_strncpyz(s_dwtrv24PickModel, bestModelName, sizeof(s_dwtrv24PickModel));
    Q_strncpyz(s_dwtrv24PickSource, bestSource, sizeof(s_dwtrv24PickSource));
    Q_strncpyz(s_dwtrv24PickSurface, bestSurfaceName, sizeof(s_dwtrv24PickSurface));
    Q_strncpyz(s_dwtrv24PickModelType, bestModelType, sizeof(s_dwtrv24PickModelType));

    /* Keep V2.2 metadata coherent for any older helper code. */
    s_dwtrv22PickEntity = bestEntity;
    Q_strncpyz(s_dwtrv22PickModel, bestModelName, sizeof(s_dwtrv22PickModel));

    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2.4: PICK source=%s entity=%d modelType=%s model=%s surface=%d surfaceName=%s shader=%s texture=%s source=%dx%d distance=%.1f\n",
              s_dwtrv24PickSource, s_dwtrv24PickEntity,
              s_dwtrv24PickModelType, s_dwtrv24PickModel,
              bestSurface,
              s_dwtrv24PickSurface[0] ? s_dwtrv24PickSurface : "-",
              bestShader ? bestShader->name : "?",
              bestImage->imgName,
              bestImage->width, bestImage->height, best);

    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2.4: picker only expanded; AI variants and cumulative PK3 remain B2 V2.3. Use /dw_tex_ai_build.\n");
}

void R_DWTextureInfoV24_f(void)
{
    const dwtrV2Candidate_t *cand;

    if (!s_dwtr.selected) {
        ri.Printf(PRINT_ALL,
                  "DWTR AI B2 V2.4: nothing selected. /dw_tex_pick\n");
        return;
    }

    if (s_dwtrv2.count <= 0) {
        ri.Printf(PRINT_ALL,
                  "DWTR AI B2 V2.4: pick=%s entity=%d modelType=%s model=%s surfaceName=%s shader=%s texture=%s source=%dx%d candidates=0. /dw_tex_ai_build\n",
                  s_dwtrv24PickSource, s_dwtrv24PickEntity,
                  s_dwtrv24PickModelType, s_dwtrv24PickModel,
                  s_dwtrv24PickSurface[0] ? s_dwtrv24PickSurface : "-",
                  s_dwtr.shader ? s_dwtr.shader->name : "?",
                  s_dwtr.original ? s_dwtr.original->imgName : "?",
                  s_dwtr.original ? s_dwtr.original->width : 0,
                  s_dwtr.original ? s_dwtr.original->height : 0);
        return;
    }

    cand = &s_dwtrv2.c[s_dwtrv2.current];
    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2.4: pick=%s entity=%d modelType=%s model=%s surfaceName=%s texture=%s source=%dx%d output=%dx%d candidate=%d/%d %s ai=%d%% showing=%s\n",
              s_dwtrv24PickSource, s_dwtrv24PickEntity,
              s_dwtrv24PickModelType, s_dwtrv24PickModel,
              s_dwtrv24PickSurface[0] ? s_dwtrv24PickSurface : "-",
              s_dwtr.original ? s_dwtr.original->imgName : "?",
              s_dwtr.original ? s_dwtr.original->width : 0,
              s_dwtr.original ? s_dwtr.original->height : 0,
              cand->width, cand->height,
              s_dwtrv2.current + 1, s_dwtrv2.count,
              cand->label ? cand->label : "?",
              cand->aiPercent,
              s_dwtr.showingB ? "B" : "A");
}
