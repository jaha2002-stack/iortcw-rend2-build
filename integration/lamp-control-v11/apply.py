#!/usr/bin/env python3
from pathlib import Path
import sys

src=Path(sys.argv[1] if len(sys.argv)>1 else "source")
root=src/"SP"/"code"/"rend2"
inc=root/"tr_lamp_control_v1.inc"
scene=root/"tr_scene.c"
if not inc.exists() or not scene.exists():
    raise SystemExit("Lamp Control V1 must be applied before V1.1")

s=inc.read_text()

# Forward declaration of the production exact native resolver already in tr_scene.c.
anchor="""static int R_StaticPromoteFindCrosshairFixture(float *forwardDistanceOut, float *lateralDistanceOut);
"""
repl=anchor+"""static int R_StaticPromoteUSLRDFindNativeRuntimeDlight(const staticPromotePersistentLight_t *light);
"""
if anchor not in s:
    raise SystemExit("forward declaration anchor missing")
s=s.replace(anchor,repl,1)

# Add route-independent native resolver before the hard post-BeginScene filter.
anchor="""static void R_DWLC1_FilterDisabledSceneDlights(int *diagIndex)
{
"""
helper=r'''static int R_DWLC11_FindBlockedNativeRuntimeDlight(const staticPromotePersistentLight_t *light)
{
    int exactIndex;
    int pass, j;
    int bestIndex = -1, secondIndex = -1;
    float best2 = 1.0e30f, second2 = 1.0e30f;
    const float maxDist = 96.0f;
    const float ambiguityMargin = 18.0f;

    if (!light)
        return -1;

    /*
     * Preferred path: the production PLR marker/ordinal association.
     * This is the exact same resolver used by normal NATIVE routing.
     */
    exactIndex = R_StaticPromoteUSLRDFindNativeRuntimeDlight(light);
    if (exactIndex >= 0)
        return exactIndex;

    /*
     * Fallback for old/unclassified electric fixtures that lack a PLR native
     * ordinal but still have a real runtime DLight.  Search native scene lights
     * only, prefer authored DLight entries, require proximity to the persistent
     * physical fixture, and reject ambiguous nearest-neighbour matches.
     *
     * This is intentionally bounded and is used only for an explicit user-OFF
     * fixture, never for automatic promotion/classification.
     */
    for (pass = 0; pass < 2; ++pass) {
        bestIndex = -1;
        secondIndex = -1;
        best2 = second2 = 1.0e30f;

        for (j = r_firstSceneDlight; j < r_numdlights && j < MAX_DLIGHTS; ++j) {
            dlight_t *dl = &backEndData->dlights[j];
            vec3_t delta;
            float dist2;

            if (dl->staticPromoteFixtureId >= 0)
                continue;
            if (pass == 0 && !dl->nativeAuthoredDlight)
                continue;
            if (pass == 1 && dl->nativeAuthoredDlight)
                continue;

            VectorSubtract(dl->origin, light->candidate.origin, delta);
            dist2 = DotProduct(delta, delta);
            if (dist2 > maxDist * maxDist)
                continue;

            if (dist2 < best2) {
                second2 = best2;
                secondIndex = bestIndex;
                best2 = dist2;
                bestIndex = j - r_firstSceneDlight;
            } else if (dist2 < second2) {
                second2 = dist2;
                secondIndex = j - r_firstSceneDlight;
            }
        }

        if (bestIndex >= 0) {
            if (secondIndex >= 0) {
                float bestDist = sqrtf(best2);
                float secondDist = sqrtf(second2);
                if (secondDist < bestDist + ambiguityMargin)
                    return -1;
            }
            return bestIndex;
        }
    }

    return -1;
}

static void R_DWLC1_FilterDisabledSceneDlights(int *diagIndex)
{
'''
if anchor not in s:
    raise SystemExit("filter anchor missing")
s=s.replace(anchor,helper,1)

# Replace the V1 ternary filter with independent identities. Native route gets
# tagged before RE_BeginScene, so staticPromoteFixtureId handles it here too.
old='''    for (i = 0; i < oldCount; ++i) {
        dlight_t *dl = &tr.refdef.dlights[i];
        int fixtureId = dl->physicalElectricOwnerId >= 0 ?
            dl->physicalElectricOwnerId : dl->staticPromoteFixtureId;
        qboolean keep = fixtureId < 0 || R_DWLC1_FixtureIdEnabled(fixtureId);

        if (!keep) {
'''
new='''    for (i = 0; i < oldCount; ++i) {
        dlight_t *dl = &tr.refdef.dlights[i];
        qboolean keep = qtrue;

        if (dl->staticPromoteFixtureId >= 0 &&
            !R_DWLC1_FixtureIdEnabled(dl->staticPromoteFixtureId))
            keep = qfalse;

        if (keep && dl->physicalElectricOwnerId > 0 &&
            !R_DWLC1_FixtureIdEnabled(dl->physicalElectricOwnerId))
            keep = qfalse;

        if (!keep) {
'''
if old not in s:
    raise SystemExit("V1 hard filter body missing")
s=s.replace(old,new,1)

# Diagnostics: report stable physical native ordinal. Runtime route is frame-local
# and OFF fixtures intentionally do not enter normal route classification.
old='''        "rayForward=%.1f rayLateral=%.1f direct=%s shadow=%s staticPromote=%s\n",
        mapName, fixtureId, targetEnabled ? "ON" : "OFF",
        light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2],
        forwardDistance, lateralDistance,
        targetEnabled ? "ENABLED" : "REMOVED",
        targetEnabled ? "ELIGIBLE" : "RELEASED",
        targetEnabled ? "ELIGIBLE" : "RELEASED");
'''
new='''        "rayForward=%.1f rayLateral=%.1f nativeOrdinal=%d "
        "direct=%s shadow=%s staticPromote=%s\n",
        mapName, fixtureId, targetEnabled ? "ON" : "OFF",
        light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2],
        forwardDistance, lateralDistance,
        light->physicalNativeDlightOrdinal,
        targetEnabled ? "ENABLED" : "REMOVED",
        targetEnabled ? "ELIGIBLE" : "RELEASED",
        targetEnabled ? "ELIGIBLE" : "RELEASED");
'''
if old not in s:
    raise SystemExit("V1 toggle diag anchor missing")
s=s.replace(old,new,1)
inc.write_text(s)

t=scene.read_text()

old=r'''			if (classReason == STATIC_PROMOTE_CLASS_USER_BLOCKED &&
				(light->physicalNativeDlightOrdinal >= 0 || light->nativeDuplicateSuppressed))
			{
				int blockedNative = R_StaticPromoteUSLRDFindNativeRuntimeDlight(light);
				if (blockedNative >= 0)
				{
					dlight_t *blocked = &backEndData->dlights[r_firstSceneDlight + blockedNative];
					blocked->radius = 0.0f;
					VectorClear(blocked->color);
					blocked->noDlightShadow = qtrue;
					blocked->localVolumetricLamp = qfalse;
					blocked->staticPromoteFixtureId = -1;
				}
			}
'''
new=r'''			if (classReason == STATIC_PROMOTE_CLASS_USER_BLOCKED)
			{
				int blockedNative = R_DWLC11_FindBlockedNativeRuntimeDlight(light);
				if (blockedNative >= 0)
				{
					dlight_t *blocked = &backEndData->dlights[r_firstSceneDlight + blockedNative];
					/*
					 * Tag the native representation with the SAME physical FixtureId.
					 * Do not merely zero intensity here.  After RE_BeginScene the
					 * renderer hard-filter physically removes this DLight from
					 * tr.refdef.dlights, before point-shadow / LocalVol consumers.
					 */
					blocked->staticPromoteFixtureId = light->candidate.entityOrdinal;
				}
			}
'''
if old not in t:
    raise SystemExit("native user-block block missing in reconstructed production source")
t=t.replace(old,new,1)
scene.write_text(t)

print("DW_LAMP_CONTROL_V11_ROUTE_INDEPENDENT_APPLY_PASS")
