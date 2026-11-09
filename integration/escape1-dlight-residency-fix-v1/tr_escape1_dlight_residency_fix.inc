// DARKWOLF_ESCAPE1_DLIGHT_RESIDENCY_FIX_V1_1
// Escape1-only stable ownership for the hard 32-DLight boundary.
// Proven native occupancy on Escape1 oscillates 6..9. Reserve 9 native slots,
// then choose a deterministic promoted set. This stops 23<->24 residency churn.
// Direct radius/color/intensity are never modified.

#define EDRF_ESCAPE1_DEFAULT_NATIVE_RESERVE 9
#define EDRF_COHERENCE_RADIUS 260.0f

static cvar_t *s_edrfEnable;
static cvar_t *s_edrfDiag;
static cvar_t *s_edrfNativeReserve;
static int s_edrfLastDiagMs = -1000000;

static void R_EDRF_EnsureCvars(void)
{
    if (s_edrfEnable) return;
    s_edrfEnable = ri.Cvar_Get("r_dwEscape1StableDlightResidency", "1", CVAR_ARCHIVE);
    s_edrfDiag = ri.Cvar_Get("r_dwEscape1StableDlightResidencyDiag", "0", CVAR_ARCHIVE);
    s_edrfNativeReserve = ri.Cvar_Get("r_dwEscape1DlightNativeReserve", "9", CVAR_ARCHIVE);
}

static qboolean R_DarkWolfEscape1StableResidencyEnabled(void)
{
    R_EDRF_EnsureCvars();
    if (!tr.world || Q_stricmp(tr.world->baseName, "escape1") != 0)
        return qfalse;
    return (s_edrfEnable && s_edrfEnable->integer) ? qtrue : qfalse;
}

static int R_DarkWolfEscape1StableStaticBudget(int eligiblePromoted, int actualStaticBudget)
{
    int reserve, stableBudget;
    if (!R_DarkWolfEscape1StableResidencyEnabled())
        return actualStaticBudget;
    reserve = s_edrfNativeReserve ? CLAMP(s_edrfNativeReserve->integer, 0, MAX_DLIGHTS - 1)
                                 : EDRF_ESCAPE1_DEFAULT_NATIVE_RESERVE;
    stableBudget = MAX(0, MAX_DLIGHTS - reserve);
    // If everything already fits inside the reserved budget, preserve the old path exactly.
    if (eligiblePromoted <= stableBudget)
        return actualStaticBudget;
    return MIN(actualStaticBudget, stableBudget);
}

static qboolean R_DarkWolfEscape1StableSelectionActive(int eligiblePromoted, int actualStaticBudget)
{
    int effective = R_DarkWolfEscape1StableStaticBudget(eligiblePromoted, actualStaticBudget);
    return (R_DarkWolfEscape1StableResidencyEnabled() &&
            eligiblePromoted > effective) ? qtrue : qfalse;
}

static int R_DarkWolfEscape1FixtureCoherenceScore(const staticPromotePersistentLight_t *light)
{
    int i, score = 0;
    const float radiusSq = EDRF_COHERENCE_RADIUS * EDRF_COHERENCE_RADIUS;
    if (!light || !R_DarkWolfEscape1StableResidencyEnabled())
        return 0;
    for (i = 0; i < s_staticPromotePersistentCount; ++i)
    {
        const staticPromotePersistentLight_t *peer = &s_staticPromotePersistentLights[i];
        vec3_t delta;
        if (peer == light || !peer->unifiedClassAccepted || peer->unifiedNativeRuntimePresent)
            continue;
        // Coherence is a stable map-space tie-break only. No camera distance participates.
        if (R_StaticPromoteUSLRDPriority(peer) != R_StaticPromoteUSLRDPriority(light))
            continue;
        VectorSubtract(light->candidate.origin, peer->candidate.origin, delta);
        if (DotProduct(delta, delta) <= radiusSq)
            score++;
    }
    return CLAMP(score, 0, 31);
}

static void R_DarkWolfEscape1ResidencyFixDiag(int eligiblePromoted, int actualStaticBudget,
    int effectiveStaticBudget, int selectedCount, qboolean stableActive)
{
    int now;
    R_EDRF_EnsureCvars();
    if (!s_edrfDiag || !s_edrfDiag->integer || !tr.world ||
        Q_stricmp(tr.world->baseName, "escape1") != 0)
        return;
    now = ri.Milliseconds();
    if (now - s_edrfLastDiagMs < 250)
        return;
    s_edrfLastDiagMs = now;
    ri.Printf(PRINT_ALL,
        "EDRF_SUMMARY map=escape1 enabled=%d stableActive=%d eligiblePromoted=%d actualBudget=%d effectiveBudget=%d selected=%d sceneNative=%d headroom=%d nativeReserve=%d budgetEvictions=%d directEnergyMutated=0 cameraDistanceUsed=0\n",
        s_edrfEnable && s_edrfEnable->integer ? 1 : 0,
        stableActive ? 1 : 0, eligiblePromoted, actualStaticBudget,
        effectiveStaticBudget, selectedCount, s_uslrdSceneNativeCount,
        s_uslrdHeadroom,
        s_edrfNativeReserve ? s_edrfNativeReserve->integer : EDRF_ESCAPE1_DEFAULT_NATIVE_RESERVE,
        s_uslrdBudgetEvictions);
}
