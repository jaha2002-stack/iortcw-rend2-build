#!/usr/bin/env python3
from pathlib import Path
import sys

src = Path(sys.argv[1] if len(sys.argv) > 1 else "source")
code = src / "SP" / "code"

def edit(rel, old, new, count=1):
    p = code / rel
    s = p.read_text()
    actual = s.count(old)
    if actual != count:
        raise SystemExit(f"anchor mismatch {rel}: expected {count}, got {actual}: {old[:120]!r}")
    p.write_text(s.replace(old, new, count))

renderer_inc = r'''/* DARKWOLF_LAMP_CONTROL_V1
 * Renderer-only individual electric lamp control.
 *
 * Goal:
 *   - pick an existing StaticPromote physical fixture by crosshair
 *   - persist OFF state by map + FixtureId
 *   - OFF fixture is excluded from StaticPromote selection
 *   - its resolved DLight is physically removed from tr.refdef.dlights before
 *     point-shadow / LocalVol consumers, so it cannot consume those resources
 *   - no game entities, switches, damage proxies, cgame visuals or model assets
 *
 * The original BSP lamp artwork is intentionally untouched.
 */
#define DW_LC1_MAX_DISABLED 256
#define DW_LC1_FILE "darkwolf_lamp_control_v1.txt"

typedef struct dwLampControlEntry_s {
    char mapName[MAX_QPATH];
    int fixtureId;
} dwLampControlEntry_t;

static dwLampControlEntry_t s_dwLc1Disabled[DW_LC1_MAX_DISABLED];
static int s_dwLc1DisabledCount;
static qboolean s_dwLc1Loaded;

/* Proven StaticPromote registry and exact crosshair picker already in tr_scene.c. */
static qboolean R_StaticPromoteBuildPersistentRegistry(void);
static int R_StaticPromoteFindCrosshairFixture(float *forwardDistanceOut, float *lateralDistanceOut);

static void R_DWLC1_Load(void)
{
    void *buffer = NULL;
    long len;
    char *p;

    if (s_dwLc1Loaded)
        return;

    s_dwLc1Loaded = qtrue;
    s_dwLc1DisabledCount = 0;

    len = ri.FS_ReadFile(DW_LC1_FILE, &buffer);
    if (len <= 0 || !buffer)
        return;

    p = (char *)buffer;
    while (*p && s_dwLc1DisabledCount < DW_LC1_MAX_DISABLED) {
        char line[256], mapName[MAX_QPATH];
        int n = 0, fixtureId = -1;

        while (p[n] && p[n] != '\n' && p[n] != '\r' && n < (int)sizeof(line) - 1) {
            line[n] = p[n];
            n++;
        }
        line[n] = 0;
        while (*p && *p != '\n') p++;
        if (*p == '\n') p++;

        if (!line[0] || line[0] == '#')
            continue;

        if (sscanf(line, "%63s %d", mapName, &fixtureId) == 2 && fixtureId >= 0) {
            dwLampControlEntry_t *e = &s_dwLc1Disabled[s_dwLc1DisabledCount++];
            Q_strncpyz(e->mapName, mapName, sizeof(e->mapName));
            e->fixtureId = fixtureId;
        }
    }

    ri.FS_FreeFile(buffer);
}

static qboolean R_DWLC1_Save(void)
{
    char out[32768], line[192];
    int i;

    out[0] = 0;
    Q_strcat(out, sizeof(out),
        "# DarkWolf Lamp Control V1\n"
        "# map fixtureId\n");

    for (i = 0; i < s_dwLc1DisabledCount; ++i) {
        const dwLampControlEntry_t *e = &s_dwLc1Disabled[i];
        Com_sprintf(line, sizeof(line), "%s %d\n", e->mapName, e->fixtureId);
        if (strlen(out) + strlen(line) + 1 >= sizeof(out))
            return qfalse;
        Q_strcat(out, sizeof(out), line);
    }

    ri.FS_WriteFile(DW_LC1_FILE, out, (int)strlen(out));
    return qtrue;
}

static int R_DWLC1_FindDisabled(const char *mapName, int fixtureId)
{
    int i;
    R_DWLC1_Load();

    if (!mapName)
        mapName = "";

    for (i = 0; i < s_dwLc1DisabledCount; ++i) {
        const dwLampControlEntry_t *e = &s_dwLc1Disabled[i];
        if (e->fixtureId == fixtureId && !Q_stricmp(e->mapName, mapName))
            return i;
    }
    return -1;
}

static qboolean R_DWLC1_FixtureIdEnabled(int fixtureId)
{
    const char *mapName = tr.world ? tr.world->baseName : "";
    if (fixtureId < 0)
        return qtrue;
    return R_DWLC1_FindDisabled(mapName, fixtureId) < 0 ? qtrue : qfalse;
}

static qboolean R_DWLC1_FixtureEnabled(const staticPromotePersistentLight_t *light)
{
    if (!light)
        return qtrue;
    return R_DWLC1_FixtureIdEnabled(light->candidate.entityOrdinal);
}

static staticPromotePersistentLight_t *R_DWLC1_Pick(float *forwardOut, float *lateralOut)
{
    int fixtureIndex;
    float forwardDistance = 0.0f;
    float lateralDistance = 0.0f;

    if (!tr.world || !R_StaticPromoteBuildPersistentRegistry())
        return NULL;

    /*
     * This picker searches the persistent fixture registry, not the current
     * selected DLight set. Therefore an already-disabled lamp remains pickable
     * and can be enabled again with the same crosshair command.
     */
    fixtureIndex = R_StaticPromoteFindCrosshairFixture(&forwardDistance, &lateralDistance);
    if (fixtureIndex < 0 || fixtureIndex >= s_staticPromotePersistentCount)
        return NULL;

    if (forwardOut) *forwardOut = forwardDistance;
    if (lateralOut) *lateralOut = lateralDistance;
    return &s_staticPromotePersistentLights[fixtureIndex];
}

static qboolean R_DWLC1_SetDisabled(const char *mapName, int fixtureId, qboolean disabled)
{
    int index = R_DWLC1_FindDisabled(mapName, fixtureId);

    if (disabled) {
        dwLampControlEntry_t *e;
        if (index >= 0)
            return qtrue;
        if (s_dwLc1DisabledCount >= DW_LC1_MAX_DISABLED)
            return qfalse;
        e = &s_dwLc1Disabled[s_dwLc1DisabledCount++];
        memset(e, 0, sizeof(*e));
        Q_strncpyz(e->mapName, mapName ? mapName : "", sizeof(e->mapName));
        e->fixtureId = fixtureId;
    } else {
        if (index < 0)
            return qtrue;
        if (index + 1 < s_dwLc1DisabledCount) {
            memmove(&s_dwLc1Disabled[index], &s_dwLc1Disabled[index + 1],
                (s_dwLc1DisabledCount - index - 1) * sizeof(s_dwLc1Disabled[0]));
        }
        s_dwLc1DisabledCount--;
    }

    return R_DWLC1_Save();
}

static void R_DWLC1_SetPickedState(qboolean enable, qboolean toggle)
{
    staticPromotePersistentLight_t *light;
    const char *mapName;
    float forwardDistance = 0.0f, lateralDistance = 0.0f;
    int fixtureId;
    qboolean currentlyEnabled, targetEnabled;

    light = R_DWLC1_Pick(&forwardDistance, &lateralDistance);
    if (!light || !tr.world) {
        ri.Printf(PRINT_WARNING,
            "DW_LAMP_CONTROL: no StaticPromote fixture near crosshair. Aim at the lamp and move closer.\n");
        return;
    }

    mapName = tr.world->baseName;
    fixtureId = light->candidate.entityOrdinal;
    currentlyEnabled = R_DWLC1_FixtureIdEnabled(fixtureId);
    targetEnabled = toggle ? !currentlyEnabled : enable;

    if (!R_DWLC1_SetDisabled(mapName, fixtureId, targetEnabled ? qfalse : qtrue)) {
        ri.Printf(PRINT_WARNING, "DW_LAMP_CONTROL: registry full/write failed\n");
        return;
    }

    ri.Printf(PRINT_ALL,
        "DW_LAMP_CONTROL_V1 map=%s fixture=%d state=%s origin=(%.1f %.1f %.1f) "
        "rayForward=%.1f rayLateral=%.1f direct=%s shadow=%s staticPromote=%s\n",
        mapName, fixtureId, targetEnabled ? "ON" : "OFF",
        light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2],
        forwardDistance, lateralDistance,
        targetEnabled ? "ENABLED" : "REMOVED",
        targetEnabled ? "ELIGIBLE" : "RELEASED",
        targetEnabled ? "ELIGIBLE" : "RELEASED");
}

void R_DWLC1_Toggle_f(void)
{
    R_DWLC1_SetPickedState(qtrue, qtrue);
}

void R_DWLC1_Off_f(void)
{
    R_DWLC1_SetPickedState(qfalse, qfalse);
}

void R_DWLC1_On_f(void)
{
    R_DWLC1_SetPickedState(qtrue, qfalse);
}

void R_DWLC1_List_f(void)
{
    const char *mapName = tr.world ? tr.world->baseName : "";
    int i, shown = 0;

    R_DWLC1_Load();
    ri.Printf(PRINT_ALL, "DW_LAMP_CONTROL_V1 disabled lamps map=%s\n", mapName);

    for (i = 0; i < s_dwLc1DisabledCount; ++i) {
        const dwLampControlEntry_t *e = &s_dwLc1Disabled[i];
        if (Q_stricmp(e->mapName, mapName))
            continue;
        ri.Printf(PRINT_ALL, "  fixture=%d OFF\n", e->fixtureId);
        shown++;
    }

    if (!shown)
        ri.Printf(PRINT_ALL, "  (none)\n");
}

void R_DWLC1_RestoreAll_f(void)
{
    const char *mapName = tr.world ? tr.world->baseName : "";
    int i, out = 0, restored = 0;

    R_DWLC1_Load();

    for (i = 0; i < s_dwLc1DisabledCount; ++i) {
        if (!Q_stricmp(s_dwLc1Disabled[i].mapName, mapName)) {
            restored++;
            continue;
        }
        if (out != i)
            s_dwLc1Disabled[out] = s_dwLc1Disabled[i];
        out++;
    }

    s_dwLc1DisabledCount = out;
    R_DWLC1_Save();
    ri.Printf(PRINT_ALL, "DW_LAMP_CONTROL_V1 restored=%d map=%s\n", restored, mapName);
}

static void R_DWLC1_FilterDisabledSceneDlights(int *diagIndex)
{
    int i, out = 0;
    int oldCount;

    if (!tr.refdef.dlights || tr.refdef.num_dlights <= 0)
        return;

    oldCount = tr.refdef.num_dlights;

    /*
     * HARD OFF: compact the actual refdef DLight array.
     * A disabled fixture is absent from all later consumers, including point
     * shadow selection/capture and LocalVol. This is not intensity=0.
     */
    for (i = 0; i < oldCount; ++i) {
        dlight_t *dl = &tr.refdef.dlights[i];
        int fixtureId = dl->physicalElectricOwnerId >= 0 ?
            dl->physicalElectricOwnerId : dl->staticPromoteFixtureId;
        qboolean keep = fixtureId < 0 || R_DWLC1_FixtureIdEnabled(fixtureId);

        if (!keep) {
            if (diagIndex && *diagIndex == i) *diagIndex = -1;
            else if (diagIndex && *diagIndex > i) (*diagIndex)--;
            continue;
        }

        if (out != i)
            tr.refdef.dlights[out] = tr.refdef.dlights[i];
        out++;
    }

    /* Eliminate stale fixed-index metadata as a cache-safety measure. */
    for (i = out; i < oldCount; ++i)
        memset(&tr.refdef.dlights[i], 0, sizeof(tr.refdef.dlights[i]));

    tr.refdef.num_dlights = out;
}
'''

(code / "rend2" / "tr_lamp_control_v1.inc").write_text(renderer_inc)

# Include near StaticPromote registry state so the helper can use persistent fixtures.
edit("rend2/tr_scene.c",
'''static char s_staticPromoteWideMapName[MAX_QPATH] = "";

''',
'''static char s_staticPromoteWideMapName[MAX_QPATH] = "";

#include "tr_lamp_control_v1.inc"

''')

# Disabled fixtures never enter the promoted selection. This directly releases
# their StaticPromote candidate/budget slot and allows another eligible fixture.
edit("rend2/tr_scene.c",
'''		allowed = R_StaticPromoteUSLRDAllowed(light, autoMapLights, &classReason);
		if (!allowed)
''',
'''		allowed = R_StaticPromoteUSLRDAllowed(light, autoMapLights, &classReason);
		if (allowed && !R_DWLC1_FixtureEnabled(light)) {
			allowed = qfalse;
			classReason = STATIC_PROMOTE_CLASS_USER_BLOCKED;
		}
		if (!allowed)
''')

# Physical owner metadata resolves native/promoted/synthetic aliases to one fixture.
# Remove OFF fixtures immediately afterwards, before shadow/LocalVol consumers.
edit("rend2/tr_scene.c",
'''	R_DarkWolfAssignPhysicalElectricOwnerIds(); // metadata only; Direct DLight is unchanged
''',
'''	R_DarkWolfAssignPhysicalElectricOwnerIds(); // metadata only; Direct DLight is unchanged
	R_DWLC1_FilterDisabledSceneDlights(&dlightDiagInjectedIndex); // DARKWOLF_LAMP_CONTROL_V1 hard OFF
''')

# Renderer console commands only. No cgame/game dependency.
edit("rend2/tr_init.c",
'''	ri.Cmd_AddCommand( "imagelist", R_ImageList_f );
''',
'''	ri.Cmd_AddCommand( "imagelist", R_ImageList_f );
	ri.Cmd_AddCommand( "dw_lamp_toggle", R_DWLC1_Toggle_f );
	ri.Cmd_AddCommand( "dw_lamp_off", R_DWLC1_Off_f );
	ri.Cmd_AddCommand( "dw_lamp_on", R_DWLC1_On_f );
	ri.Cmd_AddCommand( "dw_lamp_list", R_DWLC1_List_f );
	ri.Cmd_AddCommand( "dw_lamp_restore_all", R_DWLC1_RestoreAll_f );
''')

edit("rend2/tr_local.h",
'''void R_ELSS_List_f(void);
''',
'''void R_ELSS_List_f(void);
void R_DWLC1_Toggle_f(void);
void R_DWLC1_Off_f(void);
void R_DWLC1_On_f(void);
void R_DWLC1_List_f(void);
void R_DWLC1_RestoreAll_f(void);
''')

edit("rend2/tr_init.c",
'''	ri.Cmd_RemoveCommand( "imagelist" );
''',
'''	ri.Cmd_RemoveCommand( "imagelist" );
	ri.Cmd_RemoveCommand( "dw_lamp_toggle" );
	ri.Cmd_RemoveCommand( "dw_lamp_off" );
	ri.Cmd_RemoveCommand( "dw_lamp_on" );
	ri.Cmd_RemoveCommand( "dw_lamp_list" );
	ri.Cmd_RemoveCommand( "dw_lamp_restore_all" );
''')

print("DW_LAMP_CONTROL_V1_APPLY_PASS")
