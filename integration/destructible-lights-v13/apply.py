#!/usr/bin/env python3
from pathlib import Path
import sys

src=Path(sys.argv[1] if len(sys.argv)>1 else "source")
code=src/"SP"/"code"
rinc=code/"rend2"/"tr_destructible_lights_v1.inc"
ginc=code/"game"/"g_destructible_lights_v1.inc"

if not rinc.exists() or not ginc.exists():
    raise SystemExit("V1/V1.1 must be applied before V1.3")

r=rinc.read_text()

anchor="#define DW_DLV1_BIND_FILE \"darkwolf_light_bindings.txt\"\n"
insert=anchor+"""
/* V1.3 uses the exact proven StaticPromote registry/picker from tr_scene.c. */
static qboolean R_StaticPromoteBuildPersistentRegistry(void);
static int R_StaticPromoteFindCrosshairFixture(float *forwardDistanceOut, float *lateralDistanceOut);
"""
if anchor not in r:
    raise SystemExit("renderer declaration anchor missing")
r=r.replace(anchor,insert,1)

old="""static staticPromotePersistentLight_t *R_DLV1_PickFixture(void)
{
    int i;
    float best = 1e30f;
    staticPromotePersistentLight_t *picked = NULL;
    if (!s_staticPromoteLastViewValid) return NULL;
    for (i = 0; i < s_staticPromotePersistentCount; ++i) {
        staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
        vec3_t d, side;
        float along, perp2, cone, score;
        VectorSubtract(light->candidate.origin, s_staticPromoteLastViewOrg, d);
        along = DotProduct(d, s_staticPromoteLastViewForward);
        if (along <= 8.0f || along > 2048.0f) continue;
        VectorMA(d, -along, s_staticPromoteLastViewForward, side);
        perp2 = DotProduct(side, side);
        cone = MAX(30.0f, along * 0.12f);
        if (perp2 > cone * cone) continue;
        score = perp2 + along * 0.04f;
        if (score < best) { best = score; picked = light; }
    }
    return picked;
}
"""
new="""static staticPromotePersistentLight_t *R_DLV1_PickFixture(float *forwardOut, float *lateralOut)
{
    int fixtureIndex;
    float forwardDistance = 0.0f;
    float lateralDistance = 0.0f;

    if (!tr.world || !R_StaticPromoteBuildPersistentRegistry())
        return NULL;

    fixtureIndex = R_StaticPromoteFindCrosshairFixture(&forwardDistance, &lateralDistance);
    if (fixtureIndex < 0 || fixtureIndex >= s_staticPromotePersistentCount)
        return NULL;

    if (forwardOut) *forwardOut = forwardDistance;
    if (lateralOut) *lateralOut = lateralDistance;
    return &s_staticPromotePersistentLights[fixtureIndex];
}
"""
if old not in r:
    raise SystemExit("old custom picker not found")
r=r.replace(old,new,1)

old="""    int circuit, type, i;
    staticPromotePersistentLight_t *light;
    dwDlv1Binding_t *b = NULL;
"""
new="""    int circuit, type, i;
    float forwardDistance = 0.0f, lateralDistance = 0.0f;
    staticPromotePersistentLight_t *light;
    dwDlv1Binding_t *b = NULL;
"""
if old not in r: raise SystemExit("bind vars anchor missing")
r=r.replace(old,new,1)

old="""    light = R_DLV1_PickFixture();
    if (!light || !tr.world) {
        ri.Printf(PRINT_WARNING, "DW_DLV1 no StaticPromote fixture under view\\n");
        return;
    }
"""
new="""    light = R_DLV1_PickFixture(&forwardDistance, &lateralDistance);
    if (!light || !tr.world) {
        ri.Printf(PRINT_WARNING,
            "DW_DLV13 BIND FAILED: no StaticPromote fixture near crosshair. Aim at the bulb/fixture and move closer.\\n");
        return;
    }
"""
if old not in r: raise SystemExit("bind picker call missing")
r=r.replace(old,new,1)

old="""    ri.Printf(PRINT_ALL,
        "DW_DLV1 BOUND map=%s fixture=%d circuit=%d type=%d origin=(%.1f %.1f %.1f)\\n",
        b->mapName, b->fixtureId, b->circuit, b->lampType,
        light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2]);
"""
new="""    ri.Printf(PRINT_ALL,
        "DW_DLV13 BOUND EXACT map=%s fixture=%d circuit=%d type=%d physical=%d nativeOrdinal=%d "
        "origin=(%.1f %.1f %.1f) rayForward=%.1f rayLateral=%.1f enabled=%d\\n",
        b->mapName, b->fixtureId, b->circuit, b->lampType,
        light->physicalRecognitionAccepted ? 1 : 0, light->physicalNativeDlightOrdinal,
        light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2],
        forwardDistance, lateralDistance, R_DLV1_FixtureEnabled(light) ? 1 : 0);
"""
if old not in r: raise SystemExit("bind print anchor missing")
r=r.replace(old,new,1)

r=r.replace("staticPromotePersistentLight_t *light = R_DLV1_PickFixture();",
            "staticPromotePersistentLight_t *light = R_DLV1_PickFixture(NULL, NULL);")

# Make binding registry reload cleanly after map changes.
old="""static qboolean s_dwDlv1Loaded;
static cvar_t *s_dwDlv1Circuits[DW_DLV1_MAX_CIRCUITS];
"""
new="""static qboolean s_dwDlv1Loaded;
static char s_dwDlv1LoadedMap[MAX_QPATH];
static cvar_t *s_dwDlv1Circuits[DW_DLV1_MAX_CIRCUITS];
"""
if old not in r: raise SystemExit("loaded map anchor missing")
r=r.replace(old,new,1)

old="""    if (s_dwDlv1Loaded) return;
    s_dwDlv1Loaded = qtrue;
    s_dwDlv1BindingCount = 0;
"""
new="""    {
        const char *currentMap = tr.world ? tr.world->baseName : "";
        if (s_dwDlv1Loaded && !Q_stricmp(s_dwDlv1LoadedMap, currentMap))
            return;
        s_dwDlv1Loaded = qtrue;
        Q_strncpyz(s_dwDlv1LoadedMap, currentMap, sizeof(s_dwDlv1LoadedMap));
    }
    s_dwDlv1BindingCount = 0;
"""
if old not in r: raise SystemExit("load once anchor missing")
r=r.replace(old,new,1)

rinc.write_text(r)

g=ginc.read_text()
old="""    G_SetOrigin(e,r->origin);
    VectorCopy(angles,e->s.angles);
    VectorCopy(angles,e->r.currentAngles);

    VectorSet(e->r.mins,-2,-11,-16);
"""
new="""    G_SetOrigin(e,r->origin);
    /* V1.3 correctness: CG lerpAngles is evaluated from s.apos, not s.angles. */
    G_SetAngle(e,angles);
    e->s.eFlags &= ~EF_NODRAW;
    e->r.svFlags &= ~SVF_NOCLIENT;

    VectorSet(e->r.mins,-2,-11,-16);
"""
if old not in g: raise SystemExit("switch angle anchor missing")
g=g.replace(old,new,1)

# Push the back plate a touch farther outside the traced plane.
g=g.replace("VectorMA(tr.endpos,0.75f,normal,origin);",
            "VectorMA(tr.endpos,1.50f,normal,origin);",1)

# Add modelindex sanity output on freshly installed switch.
old="""    DW_Lights_SpawnSwitchRecord(r);
    trap_SendServerCommand(player-g_entities,
        va("print \"DW persistent switch installed: circuit=%d type=%s normal=(%.2f %.2f %.2f)\\n\"",
        circuit,DW_Lights_SwitchTypeName(type),normal[0],normal[1],normal[2]));
"""
new="""    DW_Lights_SpawnSwitchRecord(r);
    trap_SendServerCommand(player-g_entities,
        va("print \"DW V1.3 switch installed: circuit=%d type=%s origin=(%.1f %.1f %.1f) normal=(%.2f %.2f %.2f)\\n\"",
        circuit,DW_Lights_SwitchTypeName(type),origin[0],origin[1],origin[2],
        normal[0],normal[1],normal[2]));
"""
if old not in g: raise SystemExit("switch install print anchor missing")
g=g.replace(old,new,1)

ginc.write_text(g)
print("DW_DESTRUCTIBLE_LIGHTS_V13_CORRECTNESS_APPLY_PASS")
