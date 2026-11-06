// DARKWOLF_ELECTRIC_PHYSICAL_OWNER_V1
// Explicit map-local owner identity for expensive electric-lamp consumers.
// Scope is intentionally narrow: metadata only. Direct DLight origin/radius/color,
// StaticPromote residency, IFLC and ELSS profiles are never modified here.

#define DW_EPO_V1_SYNTHETIC_BASE 1000000
#define DW_EPO_V1_INHERIT_MAX_DIST 48.0f
#define DW_EPO_V1_AMBIGUITY_MARGIN 16.0f
#define DW_EPO_V1_RADIUS_DELTA 16.0f
#define DW_EPO_V1_COLOR_DELTA_SQ 0.01f

static cvar_t *s_rDwElectricPhysicalOwner;
static cvar_t *s_rDwElectricPhysicalOwnerDiag;
static int s_dwElectricPhysicalOwnerLastDiagMs = -1000000;

static void R_DarkWolfElectricPhysicalOwnerEnsureCvars(void)
{
    if (s_rDwElectricPhysicalOwner) return;
    s_rDwElectricPhysicalOwner = ri.Cvar_Get("r_dwElectricPhysicalOwner", "1", CVAR_ARCHIVE);
    s_rDwElectricPhysicalOwnerDiag = ri.Cvar_Get("r_dwElectricPhysicalOwnerDiag", "0", CVAR_ARCHIVE);
}

static float R_DarkWolfElectricOwnerBaseRadius(const dlight_t *dl)
{
    return (dl && dl->iflcActive) ? dl->iflcBaseRadius : (dl ? dl->radius : 0.0f);
}

static const float *R_DarkWolfElectricOwnerBaseColor(const dlight_t *dl)
{
    static const vec3_t zero = { 0.0f, 0.0f, 0.0f };
    return (dl && dl->iflcActive) ? dl->iflcBaseColor : (dl ? dl->color : zero);
}

static qboolean R_DarkWolfElectricOwnerIsPromoted(const dlight_t *dl)
{
    return (dl && dl->staticPromoteFixtureId >= 0) ? qtrue : qfalse;
}

static qboolean R_DarkWolfElectricOwnerIsSynthetic(const dlight_t *dl)
{
    return (R_DarkWolfElectricOwnerIsPromoted(dl) &&
        dl->staticPromoteFixtureId >= DW_EPO_V1_SYNTHETIC_BASE) ? qtrue : qfalse;
}

static qboolean R_DarkWolfElectricOwnerCompatible(const dlight_t *a, const dlight_t *b)
{
    vec3_t colorDelta;
    float radiusDelta;
    if (!a || !b) return qfalse;
    radiusDelta = fabs(R_DarkWolfElectricOwnerBaseRadius(a) - R_DarkWolfElectricOwnerBaseRadius(b));
    if (radiusDelta > DW_EPO_V1_RADIUS_DELTA) return qfalse;
    VectorSubtract(R_DarkWolfElectricOwnerBaseColor(a), R_DarkWolfElectricOwnerBaseColor(b), colorDelta);
    return DotProduct(colorDelta, colorDelta) <= DW_EPO_V1_COLOR_DELTA_SQ ? qtrue : qfalse;
}

static void R_DarkWolfAssignPhysicalElectricOwnerIds(void)
{
    int i, j, physicalResolved = 0, syntheticLinked = 0, syntheticUnresolved = 0, ambiguous = 0;
    int uniqueOwners[MAX_DLIGHTS], uniqueOwnerCount = 0;
    int n = MIN(tr.refdef.num_dlights, MAX_DLIGHTS);
    int now;

    R_DarkWolfElectricPhysicalOwnerEnsureCvars();

    for (i = 0; i < n; ++i)
        tr.refdef.dlights[i].physicalElectricOwnerId = -1;

    if (!s_rDwElectricPhysicalOwner || !s_rDwElectricPhysicalOwner->integer)
        return;

    // Pass 1: every delivered REAL StaticPromote light is already a stable physical
    // identity. Reuse that persistent fixture id as PhysicalElectricOwnerId.
    // Crucially, this never merges two real promoted lights; only synthetic children
    // may inherit a real owner's id in pass 2.
    for (i = 0; i < n; ++i)
    {
        dlight_t *dl = &tr.refdef.dlights[i];
        if (!R_DarkWolfElectricOwnerIsPromoted(dl) || R_DarkWolfElectricOwnerIsSynthetic(dl))
            continue;
        dl->physicalElectricOwnerId = dl->staticPromoteFixtureId;
        physicalResolved++;
    }

    // Pass 2: a synthetic may inherit ONLY from a delivered real promoted light.
    // The inheritance path is bounded, radius/color compatible, and rejected when
    // a competing real owner is too close. Existing Electric Fixture geometry is
    // supplementary evidence: if BOTH sides resolve and disagree, the candidate
    // is rejected; an unresolved geometry id never blocks a stable StaticPromote owner.
    for (i = 0; i < n; ++i)
    {
        dlight_t *syn = &tr.refdef.dlights[i];
        int selfFixture, bestOwner = -1, secondOwner = -1;
        float best2 = 1.0e30f, second2 = 1.0e30f;
        if (!R_DarkWolfElectricOwnerIsSynthetic(syn))
            continue;

        selfFixture = R_ElectricFixtureForLight(syn);
        for (j = 0; j < n; ++j)
        {
            dlight_t *real = &tr.refdef.dlights[j];
            vec3_t delta;
            float dist2;
            int owner, realFixture;
            if (i == j || !R_DarkWolfElectricOwnerIsPromoted(real) ||
                R_DarkWolfElectricOwnerIsSynthetic(real))
                continue;
            owner = real->physicalElectricOwnerId;
            if (owner <= 0)
                continue;
            realFixture = R_ElectricFixtureForLight(real);
            if (selfFixture > 0 && realFixture > 0 && selfFixture != realFixture)
                continue;
            if (!R_DarkWolfElectricOwnerCompatible(syn, real))
                continue;
            VectorSubtract(syn->origin, real->origin, delta);
            dist2 = DotProduct(delta, delta);
            if (dist2 > DW_EPO_V1_INHERIT_MAX_DIST * DW_EPO_V1_INHERIT_MAX_DIST)
                continue;

            if (owner == bestOwner)
            {
                if (dist2 < best2) best2 = dist2;
                continue;
            }
            if (dist2 < best2)
            {
                second2 = best2;
                secondOwner = bestOwner;
                best2 = dist2;
                bestOwner = owner;
            }
            else if (owner != bestOwner && dist2 < second2)
            {
                second2 = dist2;
                secondOwner = owner;
            }
        }

        if (bestOwner > 0)
        {
            qboolean accept = qtrue;
            if (secondOwner > 0)
            {
                float bestDist = sqrtf(best2);
                float secondDist = sqrtf(second2);
                if (secondDist < bestDist + DW_EPO_V1_AMBIGUITY_MARGIN)
                    accept = qfalse;
            }
            if (accept)
            {
                syn->physicalElectricOwnerId = bestOwner;
                syntheticLinked++;
            }
            else
            {
                ambiguous++;
                syntheticUnresolved++;
            }
        }
        else
        {
            syntheticUnresolved++;
        }
    }

    for (i = 0; i < n; ++i)
    {
        int owner = tr.refdef.dlights[i].physicalElectricOwnerId;
        if (owner <= 0) continue;
        for (j = 0; j < uniqueOwnerCount; ++j)
            if (uniqueOwners[j] == owner) break;
        if (j == uniqueOwnerCount && uniqueOwnerCount < MAX_DLIGHTS)
            uniqueOwners[uniqueOwnerCount++] = owner;
    }

    if (!s_rDwElectricPhysicalOwnerDiag || !s_rDwElectricPhysicalOwnerDiag->integer)
        return;
    now = ri.Milliseconds();
    if (now - s_dwElectricPhysicalOwnerLastDiagMs < 750)
        return;
    s_dwElectricPhysicalOwnerLastDiagMs = now;

    ri.Printf(PRINT_ALL,
        "EPO_V1_SUMMARY map=%s enabled=1 sceneDlights=%d physicalResolved=%d syntheticLinked=%d syntheticUnresolved=%d ambiguous=%d owners=%d directMutated=0\n",
        tr.world ? tr.world->baseName : "", n, physicalResolved, syntheticLinked,
        syntheticUnresolved, ambiguous, uniqueOwnerCount);

    if (s_rDwElectricPhysicalOwnerDiag->integer >= 2)
    {
        for (i = 0; i < n; ++i)
        {
            dlight_t *dl = &tr.refdef.dlights[i];
            if (!R_DarkWolfElectricOwnerIsPromoted(dl))
                continue;
            ri.Printf(PRINT_ALL,
                "EPO_V1_MEMBER dlight=%d fixture=%d synthetic=%d owner=%d electricFixture=%d origin=%.2f,%.2f,%.2f radius=%.2f color=%.4f,%.4f,%.4f iflc=%d localVol=%d\n",
                i, dl->staticPromoteFixtureId, R_DarkWolfElectricOwnerIsSynthetic(dl) ? 1 : 0,
                dl->physicalElectricOwnerId, R_ElectricFixtureForLight(dl),
                dl->origin[0], dl->origin[1], dl->origin[2],
                dl->radius, dl->color[0], dl->color[1], dl->color[2],
                dl->iflcActive ? 1 : 0, dl->localVolumetricLamp ? 1 : 0);
        }
    }
}
