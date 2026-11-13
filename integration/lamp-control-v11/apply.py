#!/usr/bin/env python3
from pathlib import Path
import sys

src=Path(sys.argv[1] if len(sys.argv)>1 else "source")
p=src/"SP"/"code"/"rend2"/"tr_lamp_control_v1.inc"
if not p.exists():
    raise SystemExit("Lamp Control V1 must be applied before V1.1")
s=p.read_text()

anchor='''static void R_DWLC1_FilterDisabledSceneDlights(int *diagIndex)
{
'''
helper='''static qboolean R_DWLC11_DisabledNativeRouteAtIndex(int dlightIndex, int *fixtureIdOut)
{
    int i;

    /*
     * StaticPromote already resolved the exact native route for each persistent
     * physical fixture earlier in this frame.  Native DLight entries themselves
     * intentionally have staticPromoteFixtureId=-1 and therefore cannot be
     * recognized by the V1 metadata-only filter.  Reuse the exact route mapping
     * instead of proximity/colour heuristics.
     */
    for (i = 0; i < s_staticPromotePersistentCount; ++i) {
        const staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
        int fixtureId;

        if (!light->unifiedNativeRuntimePresent)
            continue;
        if (light->unifiedNativeSceneIndex != dlightIndex)
            continue;

        fixtureId = light->candidate.entityOrdinal;
        if (R_DWLC1_FixtureIdEnabled(fixtureId))
            continue;

        if (fixtureIdOut)
            *fixtureIdOut = fixtureId;
        return qtrue;
    }

    return qfalse;
}

static void R_DWLC1_FilterDisabledSceneDlights(int *diagIndex)
{
'''
if anchor not in s:
    raise SystemExit("filter anchor missing")
s=s.replace(anchor,helper,1)

old='''    for (i = 0; i < oldCount; ++i) {
        dlight_t *dl = &tr.refdef.dlights[i];
        int fixtureId = dl->physicalElectricOwnerId >= 0 ?
            dl->physicalElectricOwnerId : dl->staticPromoteFixtureId;
        qboolean keep = fixtureId < 0 || R_DWLC1_FixtureIdEnabled(fixtureId);

        if (!keep) {
'''
new='''    for (i = 0; i < oldCount; ++i) {
        dlight_t *dl = &tr.refdef.dlights[i];
        int nativeFixtureId = -1;
        qboolean keep = qtrue;

        /*
         * Route-independent ownership:
         *   1) real promoted light -> exact staticPromoteFixtureId
         *   2) synthetic child     -> physicalElectricOwnerId inherited from real owner
         *   3) authored/native     -> exact unifiedNativeSceneIndex mapping
         *
         * Do not choose one id with a ternary.  A light may carry more than one
         * useful identity, and every identity that resolves to an OFF fixture must
         * veto delivery.
         */
        if (dl->staticPromoteFixtureId >= 0 &&
            !R_DWLC1_FixtureIdEnabled(dl->staticPromoteFixtureId))
            keep = qfalse;

        if (keep && dl->physicalElectricOwnerId > 0 &&
            !R_DWLC1_FixtureIdEnabled(dl->physicalElectricOwnerId))
            keep = qfalse;

        if (keep && R_DWLC11_DisabledNativeRouteAtIndex(i, &nativeFixtureId))
            keep = qfalse;

        if (!keep) {
'''
if old not in s:
    raise SystemExit("V1 filter body anchor missing")
s=s.replace(old,new,1)

old='''        "rayForward=%.1f rayLateral=%.1f direct=%s shadow=%s staticPromote=%s\n",
        mapName, fixtureId, targetEnabled ? "ON" : "OFF",
        light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2],
        forwardDistance, lateralDistance,
        targetEnabled ? "ENABLED" : "REMOVED",
        targetEnabled ? "ELIGIBLE" : "RELEASED",
        targetEnabled ? "ELIGIBLE" : "RELEASED");
'''
new='''        "rayForward=%.1f rayLateral=%.1f route=%s nativeIndex=%d "
        "direct=%s shadow=%s staticPromote=%s\n",
        mapName, fixtureId, targetEnabled ? "ON" : "OFF",
        light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2],
        forwardDistance, lateralDistance,
        light->unifiedNativeRuntimePresent ? "NATIVE" : "PROMOTED",
        light->unifiedNativeRuntimePresent ? light->unifiedNativeSceneIndex : -1,
        targetEnabled ? "ENABLED" : "REMOVED",
        targetEnabled ? "ELIGIBLE" : "RELEASED",
        targetEnabled ? "ELIGIBLE" : "RELEASED");
'''
if old not in s:
    raise SystemExit("toggle diagnostic anchor missing")
s=s.replace(old,new,1)

p.write_text(s)
print("DW_LAMP_CONTROL_V11_ROUTE_INDEPENDENT_APPLY_PASS")
