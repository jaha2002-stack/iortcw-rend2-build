// DARKWOLF_ESCAPE1_DLIGHT_RESIDENCY_FIX_V1
// Escape1-only overflow policy. It changes only WHICH accepted promoted fixture owns
// a scarce Direct DLight slot when accepted promoted lights exceed actual MAX_DLIGHTS
// headroom. Direct radius/color/intensity and all source/profile data remain untouched.

static cvar_t *s_edrfEnable;
static cvar_t *s_edrfDiag;
static int s_edrfLastDiagMs = -1000000;

static void R_EDRF_EnsureCvars(void)
{
    if (s_edrfEnable) return;
    s_edrfEnable = ri.Cvar_Get("r_dwEscape1StableDlightResidency", "1", CVAR_ARCHIVE);
    s_edrfDiag = ri.Cvar_Get("r_dwEscape1StableDlightResidencyDiag", "0", CVAR_ARCHIVE);
}

static qboolean R_DarkWolfEscape1OverflowRelevantSelection(int eligiblePromoted, int staticBudget)
{
    R_EDRF_EnsureCvars();
    if (!tr.world || Q_stricmp(tr.world->baseName, "escape1") != 0)
        return qfalse;
    if (!s_edrfEnable || !s_edrfEnable->integer)
        return qfalse;
    return (eligiblePromoted > staticBudget) ? qtrue : qfalse;
}

static void R_DarkWolfEscape1ResidencyFixDiag(int eligiblePromoted, int staticBudget,
    int selectedCount, qboolean overflowRelevant)
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
        "EDRF_SUMMARY map=escape1 enabled=%d overflowRelevant=%d eligiblePromoted=%d staticBudget=%d selected=%d sceneNative=%d headroom=%d budgetEvictions=%d directEnergyMutated=0\n",
        s_edrfEnable && s_edrfEnable->integer ? 1 : 0,
        overflowRelevant ? 1 : 0, eligiblePromoted, staticBudget, selectedCount,
        s_uslrdSceneNativeCount, s_uslrdHeadroom, s_uslrdBudgetEvictions);
}
