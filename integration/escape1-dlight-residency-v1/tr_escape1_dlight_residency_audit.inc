// DARKWOLF_ESCAPE1_DLIGHT_RESIDENCY_AUDIT_V1
// Read-only telemetry for the MAX_DLIGHTS/USLRD ownership boundary.
// It never changes selection, Direct energy, shadow, LocalVol, IFLC, ELSS or StaticPromote profiles.

static cvar_t *s_edraEnable;
static cvar_t *s_edraIntervalMs;
static int s_edraLastPrintMs = -1000000;
static int s_edraLastNativeCount = -1;
static int s_edraLastHeadroom = -1;
static int s_edraLastBudget = -1;
static int s_edraLastEvictions = -1;
static int s_edraGuardLastResident[5] = { -1, -1, -1, -1, -1 };
static int s_edraGuardIds[5] = { 740, 741, 742, 743, 744 };

static void R_EDRA_EnsureCvars(void)
{
    if (s_edraEnable) return;
    s_edraEnable = ri.Cvar_Get("r_dwEscape1DlightResidencyAudit", "0", CVAR_ARCHIVE);
    s_edraIntervalMs = ri.Cvar_Get("r_dwEscape1DlightResidencyAuditIntervalMs", "250", CVAR_ARCHIVE);
}

static int R_EDRA_FindFixtureIndex(int entityOrdinal)
{
    int i;
    for (i = 0; i < s_staticPromotePersistentCount; ++i)
        if (s_staticPromotePersistentLights[i].candidate.entityOrdinal == entityOrdinal)
            return i;
    return -1;
}

static void R_EDRA_PrintNativeDlights(void)
{
    int j;
    int end = MIN(r_firstSceneDlight + s_uslrdSceneNativeCount, r_numdlights);
    for (j = r_firstSceneDlight; j < end && j < MAX_DLIGHTS; ++j)
    {
        dlight_t *dl = &backEndData->dlights[j];
        ri.Printf(PRINT_ALL,
            "EDRA_NATIVE sceneIndex=%d globalIndex=%d origin=%.2f,%.2f,%.2f radius=%.2f color=%.4f,%.4f,%.4f nativeAuthored=%d fixture=%d forced=%d noShadow=%d localVol=%d iflc=%d\n",
            j - r_firstSceneDlight, j, dl->origin[0], dl->origin[1], dl->origin[2],
            dl->radius, dl->color[0], dl->color[1], dl->color[2],
            dl->nativeAuthoredDlight ? 1 : 0, dl->staticPromoteFixtureId,
            dl->forceDlight ? 1 : 0, dl->noDlightShadow ? 1 : 0,
            dl->localVolumetricLamp ? 1 : 0, dl->iflcActive ? 1 : 0);
    }
}

static void R_EDRA_PrintFixture(const staticPromotePersistentLight_t *light, const char *tag)
{
    if (!light) return;
    ri.Printf(PRINT_ALL,
        "EDRA_%s fixture=%d priority=%d synthetic=%d rawMembers=%d classAccepted=%d tier=%s wasResident=%d resident=%d route=%s selectedSlot=%d dlightIndex=%d budgetEvicted=%d nativeRuntime=%d surface=%d spherePvs=%d physicalFallback=%d held=%d origin=%.2f,%.2f,%.2f intensity=%.2f\n",
        tag, light->candidate.entityOrdinal, R_StaticPromoteUSLRDPriority(light),
        light->synthetic ? 1 : 0, light->rawMembers, light->unifiedClassAccepted ? 1 : 0,
        R_StaticPromoteUSLRDTierName(light->unifiedVisibilityTier),
        light->unifiedWasResident ? 1 : 0, light->unifiedResident ? 1 : 0,
        R_StaticPromoteUSLRDRouteName(light->unifiedRoute),
        light->unifiedSelectedSlot, light->unifiedActualDlightIndex,
        light->unifiedBudgetEvicted ? 1 : 0, light->unifiedNativeRuntimePresent ? 1 : 0,
        light->unifiedSurfaceSignal ? 1 : 0, light->unifiedSpherePvsConnected ? 1 : 0,
        light->unifiedPhysicalFallback ? 1 : 0, light->unifiedHeld ? 1 : 0,
        light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2],
        light->candidate.intensity);
}

static void R_DarkWolfEscape1DlightResidencyAuditFrame(const refdef_t *fd)
{
    int i, now, interval;
    int accepted = 0, resident = 0, promoted = 0, nativeRoute = 0, evicted = 0;
    int gained = 0, lost = 0, latentAccepted = 0;
    qboolean summaryChanged;

    R_EDRA_EnsureCvars();
    if (!s_edraEnable || !s_edraEnable->integer || !fd || !tr.world)
        return;
    if (Q_stricmp(tr.world->baseName, "escape1") != 0)
        return;
    if (fd->rdflags & (RDF_NOWORLDMODEL | RDF_SKYBOXPORTAL))
        return;

    now = ri.Milliseconds();
    interval = s_edraIntervalMs ? CLAMP(s_edraIntervalMs->integer, 50, 2000) : 250;

    for (i = 0; i < s_staticPromotePersistentCount; ++i)
    {
        staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
        if (!light->unifiedClassAccepted) continue;
        accepted++;
        if (light->unifiedVisibilityTier == DWSP_TIER_LATENT) latentAccepted++;
        if (light->unifiedResident) resident++;
        if (light->unifiedRoute == USLRD_ROUTE_PROMOTED) promoted++;
        if (light->unifiedRoute == USLRD_ROUTE_NATIVE) nativeRoute++;
        if (light->unifiedBudgetEvicted) evicted++;
        if (!light->unifiedWasResident && light->unifiedResident) gained++;
        if (light->unifiedWasResident && !light->unifiedResident) lost++;
    }

    summaryChanged =
        s_edraLastNativeCount != s_uslrdSceneNativeCount ||
        s_edraLastHeadroom != s_uslrdHeadroom ||
        s_edraLastBudget != s_uslrdStaticBudget ||
        s_edraLastEvictions != s_uslrdBudgetEvictions;

    if (summaryChanged || now - s_edraLastPrintMs >= interval)
    {
        ri.Printf(PRINT_ALL,
            "EDRA_SUMMARY ms=%d map=escape1 maxDlights=%d firstScene=%d rNumDlights=%d sceneNative=%d globalUsedBeforePromote=%d headroom=%d staticBudget=%d submittedPromoted=%d accepted=%d resident=%d promotedRoutes=%d nativeRoutes=%d latentAccepted=%d budgetEvictions=%d gained=%d lost=%d readOnly=1\n",
            now, MAX_DLIGHTS, r_firstSceneDlight, r_numdlights, s_uslrdSceneNativeCount,
            s_uslrdGlobalDlightsUsed, s_uslrdHeadroom, s_uslrdStaticBudget,
            s_uslrdSubmittedPromoted, accepted, resident, promoted, nativeRoute,
            latentAccepted, evicted, gained, lost);
        s_edraLastPrintMs = now;
    }

    if (s_edraLastNativeCount != s_uslrdSceneNativeCount)
    {
        ri.Printf(PRINT_ALL,
            "EDRA_NATIVE_CHANGE ms=%d old=%d new=%d headroom=%d staticBudget=%d\n",
            now, s_edraLastNativeCount, s_uslrdSceneNativeCount, s_uslrdHeadroom, s_uslrdStaticBudget);
        R_EDRA_PrintNativeDlights();
        s_edraLastNativeCount = s_uslrdSceneNativeCount;
    }

    if (s_edraLastHeadroom != s_uslrdHeadroom || s_edraLastBudget != s_uslrdStaticBudget ||
        s_edraLastEvictions != s_uslrdBudgetEvictions)
    {
        for (i = 0; i < s_staticPromotePersistentCount; ++i)
        {
            staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
            if (!light->unifiedClassAccepted) continue;
            if (light->unifiedBudgetEvicted || light->unifiedWasResident != light->unifiedResident)
                R_EDRA_PrintFixture(light, light->unifiedBudgetEvicted ? "EVICT" : "TRANSITION");
        }
        s_edraLastHeadroom = s_uslrdHeadroom;
        s_edraLastBudget = s_uslrdStaticBudget;
        s_edraLastEvictions = s_uslrdBudgetEvictions;
    }

    for (i = 0; i < 5; ++i)
    {
        int fi = R_EDRA_FindFixtureIndex(s_edraGuardIds[i]);
        if (fi >= 0)
        {
            staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[fi];
            int state = light->unifiedResident ? 1 : 0;
            if (s_edraGuardLastResident[i] != state || summaryChanged || now - s_edraLastPrintMs < 2)
                R_EDRA_PrintFixture(light, "GUARD");
            s_edraGuardLastResident[i] = state;
        }
    }
}
