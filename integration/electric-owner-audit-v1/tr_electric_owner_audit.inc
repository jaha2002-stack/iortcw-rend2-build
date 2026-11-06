// DARKWOLF_ELECTRIC_PHYSICAL_OWNER_AUDIT_V1
// Read-only diagnostics for delivered StaticPromote electric lights.
// IMPORTANT: this code runs only after point-shadow allocation and never mutates
// dlights, shadow masks/slots, LocalVol state, fixture registries, or profiles.

#define EPOA_CURRENT_MERGE_RADIUS 16.0f
#define EPOA_DEFAULT_NEAR_RADIUS 64.0f

typedef enum {
    EPOA_GROUP_SHADOW = 0,
    EPOA_GROUP_LOCALVOL = 1
} eposaGroupKind_t;

static cvar_t *s_epoaMode;
static cvar_t *s_epoaIntervalMs;
static cvar_t *s_epoaFocusFixture;
static cvar_t *s_epoaNearRadius;
static cvar_t *s_epoaVolumetricLocal;
static cvar_t *s_epoaVolumetricLocalMode;
static cvar_t *s_epoaVolumetricActiveRadius;
static cvar_t *s_epoaUnifiedResidency;
static int s_epoaLastPrintMs = -1000000;
static int s_epoaLastRegistryGeneration = -1;
static int s_epoaLastRegistryFocus = -999999;

static void R_EPOA_EnsureCvars(void)
{
    if (s_epoaMode) return;
    s_epoaMode = ri.Cvar_Get("r_dwElectricOwnerAudit", "0", CVAR_ARCHIVE);
    s_epoaIntervalMs = ri.Cvar_Get("r_dwElectricOwnerAuditIntervalMs", "1000", CVAR_ARCHIVE);
    s_epoaFocusFixture = ri.Cvar_Get("r_dwElectricOwnerAuditFocus", "-1", CVAR_ARCHIVE);
    s_epoaNearRadius = ri.Cvar_Get("r_dwElectricOwnerAuditNearRadius", "64", CVAR_ARCHIVE);
    s_epoaVolumetricLocal = ri.Cvar_Get("r_volumetricLocal", "1", CVAR_ARCHIVE);
    s_epoaVolumetricLocalMode = ri.Cvar_Get("r_volumetricLocalMode", "5", CVAR_ARCHIVE);
    s_epoaVolumetricActiveRadius = ri.Cvar_Get("r_volumetricLocalLampActiveRadius", "1536", CVAR_ARCHIVE);
    s_epoaUnifiedResidency = ri.Cvar_Get("r_staticPromoteUnifiedResidency", "1", CVAR_ARCHIVE);
}

static qboolean R_EPOA_IsPromoted(const dlight_t *dl)
{
    return (dl && dl->staticPromoteFixtureId >= 0) ? qtrue : qfalse;
}

static qboolean R_EPOA_IsSynthetic(const dlight_t *dl)
{
    return (R_EPOA_IsPromoted(dl) && dl->staticPromoteFixtureId >= STATIC_PROMOTE_SYNTHETIC_ENTITY_BASE) ? qtrue : qfalse;
}

static const float *R_EPOA_ShadowColor(const dlight_t *dl)
{
    return (dl->iflcActive && !dl->iflcOptIn) ? dl->iflcBaseColor : dl->color;
}

static float R_EPOA_ShadowRadius(const dlight_t *dl)
{
    return (dl->iflcActive && !dl->iflcOptIn) ? dl->iflcBaseRadius : dl->radius;
}

static const float *R_EPOA_LocalVolColor(const dlight_t *dl)
{
    return dl->iflcActive ? dl->iflcBaseColor : dl->color;
}

static float R_EPOA_LocalVolRadius(const dlight_t *dl)
{
    return dl->iflcActive ? dl->iflcBaseRadius : dl->radius;
}

static qboolean R_EPOA_ShadowEligible(const dlight_t *dl)
{
    if (!R_EPOA_IsPromoted(dl) || dl->noDlightShadow) return qfalse;
    return (dl->shadowSourceClass == DWSHADOW_SOURCE_PERSISTENT_PHYSICAL ||
            dl->shadowSourceClass == DWSHADOW_SOURCE_PERSISTENT_FIRE) ? qtrue : qfalse;
}

static qboolean R_EPOA_LocalVolEligible(const dlight_t *dl)
{
    if (!R_EPOA_IsPromoted(dl)) return qfalse;
    return (s_epoaUnifiedResidency && s_epoaUnifiedResidency->integer) ? qtrue : qfalse;
}

static qboolean R_EPOA_Equivalent(const dlight_t *a, const dlight_t *b, eposaGroupKind_t kind)
{
    vec3_t delta, colorDelta;
    float radiusA, radiusB;
    const float *colorA, *colorB;
    if (!a || !b || a->staticPromoteFixtureId == b->staticPromoteFixtureId) return qfalse;

    if (kind == EPOA_GROUP_SHADOW)
    {
        if (!R_EPOA_ShadowEligible(a) || !R_EPOA_ShadowEligible(b)) return qfalse;
        radiusA = R_EPOA_ShadowRadius(a);
        radiusB = R_EPOA_ShadowRadius(b);
        colorA = R_EPOA_ShadowColor(a);
        colorB = R_EPOA_ShadowColor(b);
    }
    else
    {
        if (!R_EPOA_LocalVolEligible(a) || !R_EPOA_LocalVolEligible(b)) return qfalse;
        radiusA = R_EPOA_LocalVolRadius(a);
        radiusB = R_EPOA_LocalVolRadius(b);
        colorA = R_EPOA_LocalVolColor(a);
        colorB = R_EPOA_LocalVolColor(b);
    }

    VectorSubtract(a->origin, b->origin, delta);
    if (DotProduct(delta, delta) > EPOA_CURRENT_MERGE_RADIUS * EPOA_CURRENT_MERGE_RADIUS) return qfalse;
    if (fabs(radiusA - radiusB) > 16.0f) return qfalse;
    VectorSubtract(colorA, colorB, colorDelta);
    if (DotProduct(colorDelta, colorDelta) > 0.01f) return qfalse;
    return qtrue;
}

static void R_EPOA_BuildGroups(eposaGroupKind_t kind, int ids[MAX_DLIGHTS])
{
    int queue[MAX_DLIGHTS];
    int n = MIN(tr.refdef.num_dlights, MAX_DLIGHTS);
    int i, startIndex;

    for (i = 0; i < MAX_DLIGHTS; ++i) ids[i] = -1;

    for (startIndex = 0; startIndex < n; ++startIndex)
    {
        dlight_t *start = &tr.refdef.dlights[startIndex];
        int head = 0, tail = 0, canonical;
        qboolean eligible = (kind == EPOA_GROUP_SHADOW) ? R_EPOA_ShadowEligible(start) : R_EPOA_LocalVolEligible(start);
        if (ids[startIndex] != -1 || !eligible) continue;

        ids[startIndex] = -2;
        queue[tail++] = startIndex;
        canonical = start->staticPromoteFixtureId;

        while (head < tail)
        {
            dlight_t *a = &tr.refdef.dlights[queue[head++]];
            if (a->staticPromoteFixtureId < canonical) canonical = a->staticPromoteFixtureId;

            for (i = 0; i < n; ++i)
            {
                dlight_t *peer = &tr.refdef.dlights[i];
                qboolean peerEligible = (kind == EPOA_GROUP_SHADOW) ? R_EPOA_ShadowEligible(peer) : R_EPOA_LocalVolEligible(peer);
                if (ids[i] != -1 || !peerEligible) continue;
                if (R_EPOA_Equivalent(a, peer, kind))
                {
                    ids[i] = -2;
                    queue[tail++] = i;
                }
            }
        }

        for (i = 0; i < tail; ++i) ids[queue[i]] = canonical;
    }
}

static float R_EPOA_LocalVolWeight(const dlight_t *dl, float activeRadius)
{
    vec3_t delta;
    float dist2;
    if (!dl || activeRadius <= 0.0f) return 0.0f;
    VectorSubtract(dl->origin, tr.refdef.vieworg, delta);
    dist2 = DotProduct(delta, delta);
    return (dist2 < activeRadius * activeRadius) ? 1.0f : 0.0f;
}

static qboolean R_EPOA_GroupContainsFocus(const int ids[MAX_DLIGHTS], int canonical, int focus)
{
    int i;
    if (focus < 0) return qtrue;
    for (i = 0; i < tr.refdef.num_dlights && i < MAX_DLIGHTS; ++i)
        if (ids[i] == canonical && tr.refdef.dlights[i].staticPromoteFixtureId == focus)
            return qtrue;
    return qfalse;
}

static void R_EPOA_PrintRegistry(int mode, int focus)
{
    int i, synthetic = 0;
    if (mode < 3 || !tr.world) return;
    if (s_epoaLastRegistryGeneration == s_staticPromotePersistentBuildGeneration && s_epoaLastRegistryFocus == focus) return;

    s_epoaLastRegistryGeneration = s_staticPromotePersistentBuildGeneration;
    s_epoaLastRegistryFocus = focus;

    for (i = 0; i < s_staticPromotePersistentCount; ++i)
        if (s_staticPromotePersistentLights[i].synthetic) synthetic++;

    ri.Printf(PRINT_ALL, "EPOA_REGISTRY map=%s generation=%d registry=%d synthetic=%d focus=%d readOnly=1\n",
        tr.world->baseName, s_staticPromotePersistentBuildGeneration, s_staticPromotePersistentCount, synthetic, focus);

    for (i = 0; i < s_staticPromotePersistentCount; ++i)
    {
        staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
        int fixture = light->candidate.entityOrdinal;
        if (focus >= 0 && fixture != focus) continue;

        ri.Printf(PRINT_ALL,
            "EPOA_REG map=%s registryIndex=%d fixture=%d synthetic=%d syntheticId=%d origin=%.3f,%.3f,%.3f rawIntensity=%.3f rawColor=%.4f,%.4f,%.4f resident=%d route=%d actualDlight=%d\n",
            tr.world->baseName, i, fixture, light->synthetic ? 1 : 0, light->syntheticId,
            light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2], light->candidate.intensity,
            light->candidate.color[0], light->candidate.color[1], light->candidate.color[2],
            light->unifiedResident ? 1 : 0, light->unifiedRoute, light->unifiedActualDlightIndex);
    }
}

static void R_EPOA_PrintGroup(eposaGroupKind_t kind, const int ids[MAX_DLIGHTS], int canonical, float activeRadius, int focus)
{
    int i, members = 0, synthetic = 0, slot = -1, active = 0;
    vec3_t sum;
    VectorClear(sum);

    if (!R_EPOA_GroupContainsFocus(ids, canonical, focus)) return;

    for (i = 0; i < tr.refdef.num_dlights && i < MAX_DLIGHTS; ++i)
    {
        dlight_t *dl = &tr.refdef.dlights[i];
        if (ids[i] != canonical) continue;
        members++;
        if (R_EPOA_IsSynthetic(dl)) synthetic++;
        VectorAdd(sum, dl->origin, sum);

        if (kind == EPOA_GROUP_SHADOW &&
            (tr.refdef.dlightShadowMask & (1u << i)) &&
            tr.refdef.dlightShadowSlot[i] >= 0 && tr.refdef.dlightShadowSlot[i] < MAX_DLIGHT_SHADOWS)
            slot = tr.refdef.dlightShadowSlot[i];

        if (kind == EPOA_GROUP_LOCALVOL && R_EPOA_LocalVolWeight(dl, activeRadius) > 0.001f)
            active = 1;
    }

    if (members <= 0) return;
    VectorScale(sum, 1.0f / (float)members, sum);

    ri.Printf(PRINT_ALL,
        "EPOA_GROUP kind=%s canonical=%d members=%d synthetic=%d slot=%d active=%d center=%.2f,%.2f,%.2f\n",
        kind == EPOA_GROUP_SHADOW ? "SHADOW" : "LOCALVOL", canonical, members, synthetic, slot, active,
        sum[0], sum[1], sum[2]);
}

static void R_EPOA_PrintMembers(const int shadowIds[MAX_DLIGHTS], const int volIds[MAX_DLIGHTS], int focus)
{
    int i;
    for (i = 0; i < tr.refdef.num_dlights && i < MAX_DLIGHTS; ++i)
    {
        dlight_t *dl = &tr.refdef.dlights[i];
        int slot = -1;
        if (!R_EPOA_IsPromoted(dl)) continue;
        if (focus >= 0 && dl->staticPromoteFixtureId != focus && shadowIds[i] != focus && volIds[i] != focus) continue;

        if ((tr.refdef.dlightShadowMask & (1u << i)) &&
            tr.refdef.dlightShadowSlot[i] >= 0 && tr.refdef.dlightShadowSlot[i] < MAX_DLIGHT_SHADOWS)
            slot = tr.refdef.dlightShadowSlot[i];

        ri.Printf(PRINT_ALL,
            "EPOA_MEMBER dlight=%d fixture=%d synthetic=%d origin=%.2f,%.2f,%.2f directRadius=%.2f directColor=%.4f,%.4f,%.4f shadowGroup=%d localVolGroup=%d shadowSlot=%d localVolMarker=%d iflc=%d\n",
            i, dl->staticPromoteFixtureId, R_EPOA_IsSynthetic(dl) ? 1 : 0,
            dl->origin[0], dl->origin[1], dl->origin[2], dl->radius,
            dl->color[0], dl->color[1], dl->color[2], shadowIds[i], volIds[i], slot,
            dl->localVolumetricLamp ? 1 : 0, dl->iflcActive ? 1 : 0);
    }
}

static int R_EPOA_PrintNearSyntheticPairs(const int shadowIds[MAX_DLIGHTS], const int volIds[MAX_DLIGHTS],
    float nearRadius, int mode, int focus)
{
    int i, j, count = 0;
    float nearSq = nearRadius * nearRadius;

    for (i = 0; i < tr.refdef.num_dlights && i < MAX_DLIGHTS; ++i)
    {
        dlight_t *a = &tr.refdef.dlights[i];
        if (!R_EPOA_IsPromoted(a)) continue;

        for (j = i + 1; j < tr.refdef.num_dlights && j < MAX_DLIGHTS; ++j)
        {
            dlight_t *b = &tr.refdef.dlights[j];
            vec3_t delta, colorDelta;
            float dist2, dist, radiusDelta, colorDeltaSq;

            if (!R_EPOA_IsPromoted(b) || (!R_EPOA_IsSynthetic(a) && !R_EPOA_IsSynthetic(b))) continue;

            VectorSubtract(a->origin, b->origin, delta);
            dist2 = DotProduct(delta, delta);
            if (dist2 > nearSq) continue;

            dist = sqrtf(dist2);
            radiusDelta = fabs(R_EPOA_LocalVolRadius(a) - R_EPOA_LocalVolRadius(b));
            VectorSubtract(R_EPOA_LocalVolColor(a), R_EPOA_LocalVolColor(b), colorDelta);
            colorDeltaSq = DotProduct(colorDelta, colorDelta);
            count++;

            if (mode >= 3 && (focus < 0 || a->staticPromoteFixtureId == focus || b->staticPromoteFixtureId == focus))
                ri.Printf(PRINT_ALL,
                    "EPOA_NEAR fixtureA=%d syntheticA=%d fixtureB=%d syntheticB=%d distance=%.2f radiusDelta=%.2f colorDeltaSq=%.5f currentShadowSame=%d currentLocalVolSame=%d withinCurrentDistance=%d\n",
                    a->staticPromoteFixtureId, R_EPOA_IsSynthetic(a) ? 1 : 0,
                    b->staticPromoteFixtureId, R_EPOA_IsSynthetic(b) ? 1 : 0,
                    dist, radiusDelta, colorDeltaSq,
                    (shadowIds[i] >= 0 && shadowIds[i] == shadowIds[j]) ? 1 : 0,
                    (volIds[i] >= 0 && volIds[i] == volIds[j]) ? 1 : 0,
                    dist <= EPOA_CURRENT_MERGE_RADIUS ? 1 : 0);
        }
    }
    return count;
}

static void R_ElectricPhysicalOwnerAuditFrame(const refdef_t *fd)
{
    int shadowIds[MAX_DLIGHTS], volIds[MAX_DLIGHTS];
    int i, mode, focus, interval, now;
    int promoted = 0, synthetic = 0, shadowGroups = 0, shadowRenderedGroups = 0;
    int localVolGroups = 0, localVolActiveGroups = 0;
    int shadowExtraMembers = 0, localVolExtraMembers = 0, nearSyntheticPairs;
    int seenShadow[MAX_DLIGHTS], seenVol[MAX_DLIGHTS], seenShadowCount = 0, seenVolCount = 0;
    unsigned int slotMask = 0;
    int slotCount = 0;
    float activeRadius, nearRadius;
    qboolean localVolEnabled;

    R_EPOA_EnsureCvars();
    mode = s_epoaMode ? s_epoaMode->integer : 0;
    if (mode <= 0 || !fd || !tr.world || (fd->rdflags & (RDF_NOWORLDMODEL | RDF_SKYBOXPORTAL))) return;

    mode = CLAMP(mode, 1, 3);
    focus = s_epoaFocusFixture ? s_epoaFocusFixture->integer : -1;
    interval = s_epoaIntervalMs ? CLAMP(s_epoaIntervalMs->integer, 250, 10000) : 1000;
    now = ri.Milliseconds();
    if (now - s_epoaLastPrintMs < interval) return;
    s_epoaLastPrintMs = now;

    activeRadius = s_epoaVolumetricActiveRadius ? Com_Clamp(64.0f, 8192.0f, s_epoaVolumetricActiveRadius->value) : 1536.0f;
    nearRadius = s_epoaNearRadius ? Com_Clamp(16.0f, 256.0f, s_epoaNearRadius->value) : EPOA_DEFAULT_NEAR_RADIUS;
    localVolEnabled = (s_epoaVolumetricLocal && s_epoaVolumetricLocal->integer &&
        s_epoaVolumetricLocalMode && s_epoaVolumetricLocalMode->integer == 5) ? qtrue : qfalse;

    R_EPOA_BuildGroups(EPOA_GROUP_SHADOW, shadowIds);
    R_EPOA_BuildGroups(EPOA_GROUP_LOCALVOL, volIds);

    for (i = 0; i < tr.refdef.num_dlights && i < MAX_DLIGHTS; ++i)
    {
        dlight_t *dl = &tr.refdef.dlights[i];
        int k;
        if (!R_EPOA_IsPromoted(dl)) continue;
        promoted++;
        if (R_EPOA_IsSynthetic(dl)) synthetic++;

        if ((tr.refdef.dlightShadowMask & (1u << i)) &&
            tr.refdef.dlightShadowSlot[i] >= 0 && tr.refdef.dlightShadowSlot[i] < MAX_DLIGHT_SHADOWS &&
            tr.refdef.dlightShadowSlot[i] < 32)
            slotMask |= 1u << tr.refdef.dlightShadowSlot[i];

        if (shadowIds[i] >= 0)
        {
            for (k = 0; k < seenShadowCount; ++k) if (seenShadow[k] == shadowIds[i]) break;
            if (k == seenShadowCount && seenShadowCount < MAX_DLIGHTS) seenShadow[seenShadowCount++] = shadowIds[i];
        }

        if (volIds[i] >= 0)
        {
            for (k = 0; k < seenVolCount; ++k) if (seenVol[k] == volIds[i]) break;
            if (k == seenVolCount && seenVolCount < MAX_DLIGHTS) seenVol[seenVolCount++] = volIds[i];
        }
    }

    shadowGroups = seenShadowCount;
    localVolGroups = seenVolCount;

    for (i = 0; i < seenShadowCount; ++i)
    {
        int j, members = 0, rendered = 0;
        for (j = 0; j < tr.refdef.num_dlights && j < MAX_DLIGHTS; ++j)
            if (shadowIds[j] == seenShadow[i])
            {
                members++;
                if ((tr.refdef.dlightShadowMask & (1u << j)) && tr.refdef.dlightShadowSlot[j] >= 0) rendered = 1;
            }
        if (members > 1) shadowExtraMembers += members - 1;
        if (rendered) shadowRenderedGroups++;
    }

    for (i = 0; i < seenVolCount; ++i)
    {
        int j, members = 0, active = 0;
        for (j = 0; j < tr.refdef.num_dlights && j < MAX_DLIGHTS; ++j)
            if (volIds[j] == seenVol[i])
            {
                members++;
                if (R_EPOA_LocalVolWeight(&tr.refdef.dlights[j], activeRadius) > 0.001f) active = 1;
            }
        if (members > 1) localVolExtraMembers += members - 1;
        if (localVolEnabled && active) localVolActiveGroups++;
    }

    nearSyntheticPairs = R_EPOA_PrintNearSyntheticPairs(shadowIds, volIds, nearRadius, mode, focus);
    R_EPOA_PrintRegistry(mode, focus);

    for (i = 0; i < MAX_DLIGHT_SHADOWS && i < 32; ++i)
        if (slotMask & (1u << i)) slotCount++;

    ri.Printf(PRINT_ALL,
        "EPOA_SUMMARY map=%s mode=%d readOnly=1 sceneDlights=%d promotedDirect=%d syntheticDirect=%d shadowGroups=%d shadowRenderedGroups=%d shadowSlotsUsed=%d shadowGroupedExtraDirect=%d localVolGroups=%d localVolActiveGroups=%d localVolGroupedExtraDirect=%d nearSyntheticPairs=%d mergeRadius=%.1f nearRadius=%.1f localVolEnabled=%d localVolMode=%d activeRadius=%.1f\n",
        tr.world->baseName, mode, tr.refdef.num_dlights, promoted, synthetic, shadowGroups, shadowRenderedGroups,
        slotCount, shadowExtraMembers, localVolGroups, localVolActiveGroups, localVolExtraMembers, nearSyntheticPairs,
        EPOA_CURRENT_MERGE_RADIUS, nearRadius, localVolEnabled ? 1 : 0,
        s_epoaVolumetricLocalMode ? s_epoaVolumetricLocalMode->integer : 0, activeRadius);

    if (mode >= 2)
    {
        for (i = 0; i < seenShadowCount; ++i)
            R_EPOA_PrintGroup(EPOA_GROUP_SHADOW, shadowIds, seenShadow[i], activeRadius, focus);
        for (i = 0; i < seenVolCount; ++i)
            R_EPOA_PrintGroup(EPOA_GROUP_LOCALVOL, volIds, seenVol[i], activeRadius, focus);
    }

    if (mode >= 3) R_EPOA_PrintMembers(shadowIds, volIds, focus);
}
