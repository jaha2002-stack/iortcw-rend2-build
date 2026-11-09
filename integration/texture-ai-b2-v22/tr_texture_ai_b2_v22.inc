/* DARKWOLF_TEXTURE_AI_B2_V22
 * 1) deterministic one-PK3-per-texture persistence with legacy duplicate cleanup
 * 2) texture picking for WORLD BSP and inline BRUSH model entities (doors/lifts/etc.)
 */

static int s_dwtrv22PickEntity = REFENTITYNUM_WORLD;
static char s_dwtrv22PickModel[MAX_QPATH] = "WORLD";

static void DWTRV22_WorldRayToEntity(const trRefEntity_t *ent,
                                     const vec3_t worldOrigin,
                                     const vec3_t worldDir,
                                     vec3_t localOrigin,
                                     vec3_t localDir)
{
    vec3_t delta;
    int k;
    VectorSubtract(worldOrigin, ent->e.origin, delta);
    for (k = 0; k < 3; ++k) {
        localOrigin[k] = DotProduct(delta, ent->e.axis[k]);
        localDir[k] = DotProduct(worldDir, ent->e.axis[k]);
    }
}

void R_DWTextureV22CleanupLegacyPaks(const char *home, const char *game,
                                     unsigned int hash, const char *keepPhysical)
{
#ifdef _WIN32
    int zcount, i;
    char prefix[16];
    char name[MAX_QPATH];
    char path[MAX_OSPATH * 2];

    if (!home || !home[0] || !game || !game[0]) return;

    for (zcount = 2; zcount <= 10; ++zcount) {
        for (i = 0; i < zcount && i < (int)sizeof(prefix) - 1; ++i) {
            prefix[i] = 'z';
        }
        prefix[i] = '\0';

        Com_sprintf(name, sizeof(name), "%s_dwtr_%08x.pk3", prefix, hash);
        DWTRAI_PhysicalPath(path, sizeof(path), home, game, name);

        if (keepPhysical && !Q_stricmp(path, keepPhysical)) {
            continue;
        }
        if (DWTRAI_IsFile(path)) {
            if (DeleteFileA(path)) {
                ri.Printf(PRINT_ALL,
                          "DWTR AI B2 V2.2: removed legacy duplicate %s\n", path);
            } else {
                ri.Printf(PRINT_WARNING,
                          "DWTR AI B2 V2.2: could not remove legacy duplicate %s winerr=%lu\n",
                          path, (unsigned long)GetLastError());
            }
        }
    }
#else
    (void)home; (void)game; (void)hash; (void)keepPhysical;
#endif
}

void R_DWTexturePickV22_f(void)
{
    int i, bestSurface = -1, bestEntity = REFENTITYNUM_WORLD;
    float best = 8192.0f;
    shader_t *bestShader = NULL;
    shaderStage_t *bestStage = NULL;
    image_t *bestImage = NULL;
    const char *bestModelName = "WORLD";
    vec3_t worldOrigin, worldDir;

    R_IssuePendingRenderCommands();

    if (!tr.world || !tr.world->surfaces || tr.world->numWorldSurfaces <= 0) {
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2.2: no world loaded.\n");
        return;
    }

    VectorCopy(tr.refdef.vieworg, worldOrigin);
    VectorCopy(tr.refdef.viewaxis[0], worldDir);

    /* Pass 1: static WORLD BSP. */
    for (i = 0; i < tr.world->numWorldSurfaces; ++i) {
        float t = best;
        shader_t *candidateShader;
        shaderStage_t *candidateStage;
        image_t *candidateImage = NULL;

        if (!DWTR_RaySurface(&tr.world->surfaces[i], worldOrigin, worldDir, &t) ||
            t >= best) {
            continue;
        }

        candidateShader = tr.world->surfaces[i].shader;
        candidateStage = DWTR_DiffuseStage(candidateShader, &candidateImage);
        if (!candidateStage || !candidateImage) {
            continue;
        }

        best = t;
        bestSurface = i;
        bestEntity = REFENTITYNUM_WORLD;
        bestShader = candidateShader;
        bestStage = candidateStage;
        bestImage = candidateImage;
        bestModelName = "WORLD";
    }

    /* Pass 2: RT_MODEL / MOD_BRUSH entities.
     * func_door, func_door_rotating, lifts and other inline BSP entities are
     * not part of the static world ray test. Transform the camera ray into
     * each brush entity's local space and test its real BSP triangles. */
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

        /* Scaled brush entities are not expected for RTCW doors; avoiding
         * non-normalized axes keeps ray distance comparable with WORLD t. */
        if (ent->e.nonNormalizedAxes) {
            continue;
        }

        bmodel = model->bmodel;
        DWTRV22_WorldRayToEntity(ent, worldOrigin, worldDir,
                                 localOrigin, localDir);

        for (s = 0; s < bmodel->numSurfaces; ++s) {
            int surfIndex = bmodel->firstSurface + s;
            msurface_t *surf;
            shader_t *candidateShader;
            shaderStage_t *candidateStage;
            image_t *candidateImage = NULL;
            float t = best;

            if (surfIndex < 0 || surfIndex >= tr.world->numWorldSurfaces) {
                continue;
            }

            surf = &tr.world->surfaces[surfIndex];
            if (!DWTR_RaySurface(surf, localOrigin, localDir, &t) || t >= best) {
                continue;
            }

            candidateShader = ent->e.customShader
                                ? R_GetShaderByHandle(ent->e.customShader)
                                : surf->shader;
            candidateStage = DWTR_DiffuseStage(candidateShader, &candidateImage);
            if (!candidateStage || !candidateImage) {
                continue;
            }

            best = t;
            bestSurface = surfIndex;
            bestEntity = i;
            bestShader = candidateShader;
            bestStage = candidateStage;
            bestImage = candidateImage;
            bestModelName = model->name;
        }
    }

    if (bestSurface < 0 || !bestStage || !bestImage) {
        ri.Printf(PRINT_WARNING,
                  "DWTR AI B2 V2.2: no restorable WORLD/BRUSH texture under crosshair.\n");
        return;
    }

    R_DWTextureRestoreReset();
    s_dwtr.selected = qtrue;
    s_dwtr.surfaceIndex = bestSurface;
    s_dwtr.shader = bestShader;
    s_dwtr.stage = bestStage;
    s_dwtr.original = bestImage;

    s_dwtrv22PickEntity = bestEntity;
    Q_strncpyz(s_dwtrv22PickModel, bestModelName, sizeof(s_dwtrv22PickModel));

    if (bestEntity == REFENTITYNUM_WORLD) {
        ri.Printf(PRINT_ALL,
                  "DWTR AI B2 V2.2: PICK source=WORLD surface=%d shader=%s texture=%s source=%dx%d distance=%.1f\n",
                  bestSurface,
                  bestShader ? bestShader->name : "?",
                  bestImage->imgName,
                  bestImage->width, bestImage->height, best);
    } else {
        ri.Printf(PRINT_ALL,
                  "DWTR AI B2 V2.2: PICK source=BRUSH entity=%d model=%s surface=%d shader=%s texture=%s source=%dx%d distance=%.1f\n",
                  bestEntity, s_dwtrv22PickModel, bestSurface,
                  bestShader ? bestShader->name : "?",
                  bestImage->imgName,
                  bestImage->width, bestImage->height, best);
    }

    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2.2: /dw_tex_ai_build -> BALANCED; /dw_tex_next /dw_tex_prev; /dw_tex_save.\n");
}

void R_DWTextureInfoV22_f(void)
{
    const char *source = (s_dwtrv22PickEntity == REFENTITYNUM_WORLD) ? "WORLD" : "BRUSH";

    if (!s_dwtr.selected) {
        ri.Printf(PRINT_ALL, "DWTR AI B2 V2.2: nothing selected. /dw_tex_pick\n");
        return;
    }

    if (s_dwtrv2.count <= 0) {
        ri.Printf(PRINT_ALL,
                  "DWTR AI B2 V2.2: pick=%s entity=%d model=%s texture=%s source=%dx%d candidates=0. /dw_tex_ai_build\n",
                  source, s_dwtrv22PickEntity, s_dwtrv22PickModel,
                  s_dwtr.original->imgName,
                  s_dwtr.original->width, s_dwtr.original->height);
        return;
    }

    ri.Printf(PRINT_ALL,
              "DWTR AI B2 V2.2: pick=%s entity=%d model=%s texture=%s source=%dx%d output=%dx%d candidate=%d/%d %s ai=%d%% showing=%s\n",
              source, s_dwtrv22PickEntity, s_dwtrv22PickModel,
              s_dwtr.original->imgName,
              s_dwtr.original->width, s_dwtr.original->height,
              s_dwtr.width, s_dwtr.height,
              s_dwtrv2.current + 1, s_dwtrv2.count,
              s_dwtrv2.c[s_dwtrv2.current].label,
              s_dwtrv2.c[s_dwtrv2.current].aiPercent,
              s_dwtr.showingB ? "B" : "A");
}
