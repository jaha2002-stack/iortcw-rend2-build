#!/usr/bin/env python3
from pathlib import Path
import sys

src=Path(sys.argv[1] if len(sys.argv)>1 else "source")
root=src/"SP"/"code"/"rend2"
lc=root/"tr_lamp_control_v1.inc"
scene=root/"tr_scene.c"
if not lc.exists() or not scene.exists():
    raise SystemExit("Lamp Control V1/V1.1 must be applied before V1.2")

s=lc.read_text()

# Old V1/V1.1 selections are not trustworthy because the old picker searched all
# 509 StaticPromote fixtures through a 4096-unit wide cone.  Do not import stale ids.
old='#define DW_LC1_FILE "darkwolf_lamp_control_v1.txt"'
new='#define DW_LC1_FILE "darkwolf_lamp_control_v12.txt"'
if s.count(old)!=1:
    raise SystemExit("registry file anchor missing")
s=s.replace(old,new,1)

anchor='static int R_StaticPromoteUSLRDFindNativeRuntimeDlight(const staticPromotePersistentLight_t *light);\n'
if s.count(anchor)!=1:
    raise SystemExit("V1.1 forward anchor missing")
s=s.replace(anchor,anchor+'static staticPromotePersistentLight_t *R_DWLC12_PickExact(float *forwardOut, float *lateralOut);\n',1)

start=s.index('static staticPromotePersistentLight_t *R_DWLC1_Pick(float *forwardOut, float *lateralOut)\n{')
end=s.index('\nstatic qboolean R_DWLC1_SetDisabled',start)
replacement=r'''static staticPromotePersistentLight_t *R_DWLC1_Pick(float *forwardOut, float *lateralOut)
{
    /*
     * V1/V1.1 used R_StaticPromoteFindCrosshairFixture(), which is a diagnostic
     * cone picker over every BSP light fixture.  It has no surface hit, no
     * visibility test and no proof that the fixture owns a runtime DLight.
     *
     * V1.2 deliberately delegates to the exact-visible picker defined after
     * IFLC/ELSS, where the proven surface ray and visibility helpers exist.
     */
    return R_DWLC12_PickExact(forwardOut, lateralOut);
}
'''
s=s[:start]+replacement+s[end:]

s=s.replace(
    '"DW_LAMP_CONTROL: no StaticPromote fixture near crosshair. Aim at the lamp and move closer.\\n"',
    '"DW_LAMP_CONTROL_V12: no unique visible electric DLight owner under crosshair. Aim at the lamp housing/light and move closer.\\n"'
)
s=s.replace('"DW_LAMP_CONTROL_V1 map=%s fixture=%d state=%s origin=(%.1f %.1f %.1f) "',
            '"DW_LAMP_CONTROL_V12 map=%s fixture=%d state=%s origin=(%.1f %.1f %.1f) "')
s=s.replace('# DarkWolf Lamp Control V1\\n', '# DarkWolf Lamp Control V1.2 exact-visible picker\\n')
lc.write_text(s)

helper=r'''/* DARKWOLF_LAMP_CONTROL_V12_EXACT_VISIBLE_PICKER
 *
 * Selection contract:
 *   - only a fixture that owns a REAL runtime DLight may be newly selected;
 *   - an already-disabled fixture remains selectable for re-enable;
 *   - use the proven IFLC/ELSS primary-view surface hit and occlusion helpers;
 *   - maximum working distance is 512 units, matching ELSS;
 *   - distinct qualifying fixtures are treated as ambiguous: do nothing.
 *
 * This intentionally rejects uncertain input instead of changing the wrong lamp.
 */
#define DW_LC12_MAX_PICKS 16

typedef struct dwLc12Pick_s {
    int fixtureIndex;
    float score;
    float forward;
    float lateral;
} dwLc12Pick_t;

static int R_DWLC12_FindFixtureIndexById(int fixtureId)
{
    int i;
    for (i = 0; i < s_staticPromotePersistentCount; ++i)
        if (s_staticPromotePersistentLights[i].candidate.entityOrdinal == fixtureId)
            return i;
    return -1;
}

static qboolean R_DWLC12_RuntimeLampDlight(const dlight_t *dl, int *fixtureIdOut)
{
    int fixtureId = -1;

    if (!dl)
        return qfalse;

    /* Fire and transient effects are not electric lamp-control targets. */
    if (dl->iflcOptIn || dl->fireVolumetricSource || dl->transientBlast)
        return qfalse;

    if (dl->staticPromoteFixtureId >= 0)
        fixtureId = dl->staticPromoteFixtureId;
    else if (dl->physicalElectricOwnerId > 0)
        fixtureId = dl->physicalElectricOwnerId;

    if (fixtureId < 0)
        return qfalse;

    if (fixtureIdOut)
        *fixtureIdOut = fixtureId;
    return qtrue;
}

static void R_DWLC12_InsertPick(dwLc12Pick_t *picks, int *count,
    int fixtureIndex, float score, float forward, float lateral)
{
    int i, pos;

    if (!picks || !count || fixtureIndex < 0)
        return;

    /* One physical FixtureId may have Direct/Shadow/LocalVol aliases. */
    for (i = 0; i < *count; ++i) {
        if (picks[i].fixtureIndex == fixtureIndex) {
            if (score < picks[i].score) {
                picks[i].score = score;
                picks[i].forward = forward;
                picks[i].lateral = lateral;
            }
            return;
        }
    }

    if (*count >= DW_LC12_MAX_PICKS)
        return;

    pos = *count;
    while (pos > 0 && score < picks[pos - 1].score) {
        picks[pos] = picks[pos - 1];
        --pos;
    }
    picks[pos].fixtureIndex = fixtureIndex;
    picks[pos].score = score;
    picks[pos].forward = forward;
    picks[pos].lateral = lateral;
    (*count)++;
}

static qboolean R_DWLC12_ConsiderFixture(int fixtureIndex, float radius,
    qboolean haveHit, const vec3_t hitPoint,
    float *scoreOut, float *forwardOut, float *lateralOut)
{
    staticPromotePersistentLight_t *light;
    vec3_t delta;
    float forward, total2, lateral2, lateral;
    float hit2 = 1.0e30f;
    float hitRadius, strictRadius, score;

    if (fixtureIndex < 0 || fixtureIndex >= s_staticPromotePersistentCount)
        return qfalse;

    light = &s_staticPromotePersistentLights[fixtureIndex];
    VectorSubtract(light->candidate.origin, s_iflcViewOrigin, delta);
    forward = DotProduct(delta, s_iflcViewForward);
    if (forward < 1.0f || forward > 512.0f)
        return qfalse;

    total2 = DotProduct(delta, delta);
    lateral2 = MAX(0.0f, total2 - forward * forward);
    lateral = sqrtf(lateral2);

    hitRadius = MIN(128.0f, MAX(56.0f, radius * 0.45f + 16.0f));
    if (haveHit)
        hit2 = R_IFLC_DistanceSquared(light->candidate.origin, hitPoint);

    if (hit2 <= hitRadius * hitRadius) {
        /* Same rule that makes ELSS robust on lamp housing / nearby mount. */
        score = sqrtf(hit2) * 0.001f + forward * 0.00001f;
    } else {
        /* No housing-proximity proof: require a very tight visible crosshair ray. */
        strictRadius = 10.0f + forward * 0.035f;
        if (lateral2 > strictRadius * strictRadius)
            return qfalse;
        if (!R_IFLC_LineVisible(s_iflcViewOrigin, light->candidate.origin))
            return qfalse;
        score = 1.0f + lateral / MAX(forward, 1.0f);
    }

    if (scoreOut) *scoreOut = score;
    if (forwardOut) *forwardOut = forward;
    if (lateralOut) *lateralOut = lateral;
    return qtrue;
}

static staticPromotePersistentLight_t *R_DWLC12_PickExact(float *forwardOut, float *lateralOut)
{
    qboolean active[STATIC_PROMOTE_PERSISTENT_MAX_FIXTURES];
    float activeRadius[STATIC_PROMOTE_PERSISTENT_MAX_FIXTURES];
    dwLc12Pick_t picks[DW_LC12_MAX_PICKS];
    int pickCount = 0;
    int i;
    vec3_t hitPoint;
    int hitSurface = -1;
    float hitDistance = 0.0f;
    qboolean haveHit = qfalse;

    if (forwardOut) *forwardOut = 0.0f;
    if (lateralOut) *lateralOut = 0.0f;

    R_IssuePendingRenderCommands();

    if (!tr.world || !s_iflcViewValid || !R_StaticPromoteBuildPersistentRegistry())
        return NULL;

    Com_Memset(active, 0, sizeof(active));
    Com_Memset(activeRadius, 0, sizeof(activeRadius));
    Com_Memset(picks, 0, sizeof(picks));

    /*
     * A fixture is a new OFF target only if it owns a real DLight in the last
     * rendered scene.  This is the key difference from the old 509-fixture cone.
     */
    if (tr.refdef.dlights && tr.refdef.num_dlights > 0) {
        for (i = 0; i < tr.refdef.num_dlights; ++i) {
            const dlight_t *dl = &tr.refdef.dlights[i];
            int fixtureId, fixtureIndex;
            if (!R_DWLC12_RuntimeLampDlight(dl, &fixtureId))
                continue;
            fixtureIndex = R_DWLC12_FindFixtureIndexById(fixtureId);
            if (fixtureIndex < 0)
                continue;
            active[fixtureIndex] = qtrue;
            if (dl->radius > activeRadius[fixtureIndex])
                activeRadius[fixtureIndex] = dl->radius;
        }
    }

    haveHit = R_ELSS_FirstHit(hitPoint, &hitSurface, &hitDistance);

    for (i = 0; i < s_staticPromotePersistentCount; ++i) {
        staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
        int fixtureId = light->candidate.entityOrdinal;
        qboolean disabled = !R_DWLC1_FixtureIdEnabled(fixtureId);
        float radius, score, forward, lateral;

        /*
         * Active real DLight OR our own disabled fixture.  Class-rejected BSP
         * lights and unrelated registry entries can no longer be selected.
         */
        if (!active[i] && !disabled)
            continue;

        radius = activeRadius[i];
        if (radius <= 1.0f)
            radius = light->unifiedRuntimeRadius;
        if (radius <= 1.0f)
            radius = 96.0f;

        if (!R_DWLC12_ConsiderFixture(i, radius, haveHit, hitPoint,
                &score, &forward, &lateral))
            continue;

        R_DWLC12_InsertPick(picks, &pickCount, i, score, forward, lateral);
    }

    if (pickCount <= 0)
        return NULL;

    if (pickCount > 1) {
        ri.Printf(PRINT_WARNING,
            "DW_LAMP_CONTROL_V12: ambiguous crosshair (%d distinct electric fixtures); no change. "
            "Move closer and aim directly at one lamp.\n", pickCount);
        for (i = 0; i < pickCount && i < 6; ++i) {
            staticPromotePersistentLight_t *light =
                &s_staticPromotePersistentLights[picks[i].fixtureIndex];
            ri.Printf(PRINT_ALL,
                "  candidate=%d fixture=%d score=%.4f forward=%.1f lateral=%.1f state=%s\n",
                i + 1, light->candidate.entityOrdinal, picks[i].score,
                picks[i].forward, picks[i].lateral,
                R_DWLC1_FixtureIdEnabled(light->candidate.entityOrdinal) ? "ON" : "OFF");
        }
        return NULL;
    }

    if (forwardOut) *forwardOut = picks[0].forward;
    if (lateralOut) *lateralOut = picks[0].lateral;
    return &s_staticPromotePersistentLights[picks[0].fixtureIndex];
}
'''

(root/"tr_lamp_control_v12.inc").write_text(helper)

t=scene.read_text()
anchor='#include "tr_iflc.inc"\n#include "tr_elss.inc"'
if t.count(anchor)!=1:
    raise SystemExit("IFLC/ELSS include anchor missing")
t=t.replace(anchor,anchor+'\n#include "tr_lamp_control_v12.inc"',1)
scene.write_text(t)

print("DW_LAMP_CONTROL_V12_EXACT_VISIBLE_APPLY_PASS")
