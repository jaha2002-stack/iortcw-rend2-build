// DARKWOLF_ESCAPE1_PHYSICAL_DLIGHT_OWNER_RESIDENCY_V12
// Escape1-only owner-first residency for the hard MAX_DLIGHTS boundary.
//
// Core invariant:
//   external native DLight + selected physical electric owners <= MAX_DLIGHTS
//
// An accepted StaticPromote fixture is counted once as a PHYSICAL OWNER regardless
// of whether the current frame delivers that owner through an already-authored
// native DLight or through a promoted DLight.  Route changes therefore do not
// create/free an owner slot and cannot make a neighbouring lamp blink.
//
// Direct light radius/color/intensity are not modified here.

#define EDR12_DEFAULT_EXTERNAL_NATIVE_RESERVE 9

static cvar_t *s_edr12Enable;
static cvar_t *s_edr12Diag;
static cvar_t *s_edr12ExternalNativeReserve;
static int s_edr12LastDiagMs = -1000000;

static void R_EDR12_EnsureCvars(void)
{
    if (s_edr12Enable)
        return;

    s_edr12Enable = ri.Cvar_Get("r_dwEscape1PhysicalDlightOwnerResidency", "1", CVAR_ARCHIVE);
    s_edr12Diag = ri.Cvar_Get("r_dwEscape1PhysicalDlightOwnerDiag", "0", CVAR_ARCHIVE);
    s_edr12ExternalNativeReserve = ri.Cvar_Get(
        "r_dwEscape1ExternalNativeReserve", "9", CVAR_ARCHIVE);
}

static qboolean R_EDR12_Enabled(void)
{
    R_EDR12_EnsureCvars();

    if (!tr.world || Q_stricmp(tr.world->baseName, "escape1") != 0)
        return qfalse;

    return (s_edr12Enable && s_edr12Enable->integer) ? qtrue : qfalse;
}

static qboolean R_EDR12_NativeCapableOwner(const staticPromotePersistentLight_t *light)
{
    if (!light)
        return qfalse;

    return (light->physicalNativeDlightOrdinal >= 0 || light->nativeDuplicateSuppressed)
        ? qtrue : qfalse;
}

static int R_EDR12_ExternalNativeCount(int sceneNativeCount, int acceptedNativeRoutes)
{
    return MAX(0, sceneNativeCount - acceptedNativeRoutes);
}

static int R_EDR12_PhysicalOwnerBudget(int requestedMaxLights,
    int externalNativeCount)
{
    int configuredReserve;
    int hardReserve;
    int hardOwnerCapacity;

    R_EDR12_EnsureCvars();

    if (!R_EDR12_Enabled())
        return requestedMaxLights;

    configuredReserve = s_edr12ExternalNativeReserve
        ? CLAMP(s_edr12ExternalNativeReserve->integer, 0, MAX_DLIGHTS - 1)
        : EDR12_DEFAULT_EXTERNAL_NATIVE_RESERVE;

    // The configured reserve stabilizes ordinary Escape1 native occupancy.
    // If a truly larger external-native high-water is observed, hard safety wins.
    hardReserve = MAX(configuredReserve, externalNativeCount);
    hardOwnerCapacity = MAX(0, MAX_DLIGHTS - hardReserve);

    return MIN(requestedMaxLights, hardOwnerCapacity);
}

static int R_EDR12_PromotedBudget(int physicalOwnerBudget,
    int acceptedNativeRoutes, int actualPromotedHeadroom)
{
    int budget = MAX(0, physicalOwnerBudget - acceptedNativeRoutes);
    return MIN(budget, actualPromotedHeadroom);
}

static void R_EDR12_Diag(int classifierAccepted, int acceptedNativeRoutes,
    int eligiblePromoted, int externalNativeCount, int physicalOwnerBudget,
    int promotedBudget, int selectedPromoted, int budgetEvictions)
{
    int now;

    R_EDR12_EnsureCvars();

    if (!s_edr12Diag || !s_edr12Diag->integer || !tr.world ||
        Q_stricmp(tr.world->baseName, "escape1") != 0)
        return;

    now = ri.Milliseconds();
    if (now - s_edr12LastDiagMs < 150)
        return;
    s_edr12LastDiagMs = now;

    ri.Printf(PRINT_ALL,
        "EDR12_SUMMARY map=escape1 enabled=%d sceneNative=%d acceptedNativeRoutes=%d "
        "externalNative=%d configuredExternalReserve=%d classifierAccepted=%d "
        "eligiblePromoted=%d physicalOwnerBudget=%d promotedBudget=%d "
        "selectedPromoted=%d physicalResidentTarget=%d budgetEvictions=%d "
        "directEnergyMutated=0 maxDlights=%d ownerFirst=1 routeIndependent=1\n",
        s_edr12Enable && s_edr12Enable->integer ? 1 : 0,
        s_uslrdSceneNativeCount, acceptedNativeRoutes, externalNativeCount,
        s_edr12ExternalNativeReserve ? s_edr12ExternalNativeReserve->integer
                                     : EDR12_DEFAULT_EXTERNAL_NATIVE_RESERVE,
        classifierAccepted, eligiblePromoted, physicalOwnerBudget,
        promotedBudget, selectedPromoted,
        MIN(classifierAccepted, physicalOwnerBudget), budgetEvictions,
        MAX_DLIGHTS);
}
