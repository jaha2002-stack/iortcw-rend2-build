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
    p.write_text(s.replace(old, new))

renderer_inc = r'''/* DARKWOLF_DESTRUCTIBLE_LIGHTS_V1
 * Runtime binding of physical StaticPromote fixtures to electrical circuits.
 * Off/dead fixtures are removed after PhysicalElectricOwner assignment and before
 * Direct/shadow/LocalVol consumers. No shadow/DLight budget is increased.
 */
#define DW_DLV1_MAX_BINDINGS 256
#define DW_DLV1_MAX_CIRCUITS 16
#define DW_DLV1_MAX_DEAD 64
#define DW_DLV1_BIND_FILE "darkwolf_light_bindings.txt"

typedef struct dwDlv1Binding_s {
    char mapName[MAX_QPATH];
    int fixtureId;
    int circuit;
    int lampType; /* 1 ceiling, 2 wall, 3 projector */
} dwDlv1Binding_t;

static dwDlv1Binding_t s_dwDlv1Bindings[DW_DLV1_MAX_BINDINGS];
static int s_dwDlv1BindingCount;
static qboolean s_dwDlv1Loaded;
static cvar_t *s_dwDlv1Circuits[DW_DLV1_MAX_CIRCUITS];
static cvar_t *s_dwDlv1DeadCount;
static cvar_t *s_dwDlv1Dead[DW_DLV1_MAX_DEAD];

static void R_DLV1_EnsureCvars(void)
{
    int i;
    char name[64];
    if (!s_dwDlv1Circuits[0]) {
        for (i = 0; i < DW_DLV1_MAX_CIRCUITS; ++i) {
            Com_sprintf(name, sizeof(name), "dw_lightCircuit%02d", i + 1);
            s_dwDlv1Circuits[i] = ri.Cvar_Get(name, "1", 0);
        }
        s_dwDlv1DeadCount = ri.Cvar_Get("dw_dl_deadCount", "0", 0);
        for (i = 0; i < DW_DLV1_MAX_DEAD; ++i) {
            Com_sprintf(name, sizeof(name), "dw_dl_dead%02d", i);
            s_dwDlv1Dead[i] = ri.Cvar_Get(name, "", 0);
        }
        ri.Cvar_Get("dw_dl_lastFixture", "-1", 0);
        ri.Cvar_Get("dw_dl_lastCircuit", "0", 0);
    }
}

static void R_DLV1_LoadBindings(void)
{
    void *buffer = NULL;
    long len;
    char *p;
    if (s_dwDlv1Loaded) return;
    s_dwDlv1Loaded = qtrue;
    s_dwDlv1BindingCount = 0;
    R_DLV1_EnsureCvars();
    len = ri.FS_ReadFile(DW_DLV1_BIND_FILE, &buffer);
    if (len <= 0 || !buffer) return;
    p = (char *)buffer;
    while (*p && s_dwDlv1BindingCount < DW_DLV1_MAX_BINDINGS) {
        char line[256], mapName[MAX_QPATH];
        int n = 0, fixture = -1, circuit = 0, type = 0;
        while (p[n] && p[n] != '\n' && p[n] != '\r' && n < (int)sizeof(line)-1) {
            line[n] = p[n]; n++;
        }
        line[n] = 0;
        while (*p && *p != '\n') p++;
        if (*p == '\n') p++;
        if (line[0] == '#' || !line[0]) continue;
        if (sscanf(line, "%63s %d %d %d", mapName, &fixture, &circuit, &type) == 4 &&
            fixture >= 0 && circuit >= 1 && circuit <= DW_DLV1_MAX_CIRCUITS &&
            type >= 1 && type <= 3) {
            dwDlv1Binding_t *b = &s_dwDlv1Bindings[s_dwDlv1BindingCount++];
            Q_strncpyz(b->mapName, mapName, sizeof(b->mapName));
            b->fixtureId = fixture;
            b->circuit = circuit;
            b->lampType = type;
        }
    }
    ri.FS_FreeFile(buffer);
}

static qboolean R_DLV1_SaveBindings(void)
{
    char out[32768], line[256];
    int i;
    out[0] = 0;
    Q_strcat(out, sizeof(out), "# DarkWolf Destructible Lights V1: map fixtureId circuit lampType\n");
    for (i = 0; i < s_dwDlv1BindingCount; ++i) {
        const dwDlv1Binding_t *b = &s_dwDlv1Bindings[i];
        Com_sprintf(line, sizeof(line), "%s %d %d %d\n",
            b->mapName, b->fixtureId, b->circuit, b->lampType);
        Q_strcat(out, sizeof(out), line);
    }
    ri.FS_WriteFile(DW_DLV1_BIND_FILE, out, (int)strlen(out));
    return qtrue;
}

static int R_DLV1_LampType(const char *s)
{
    if (!s || !*s) return 1;
    if (!Q_stricmp(s, "ceiling") || !Q_stricmp(s, "1")) return 1;
    if (!Q_stricmp(s, "wall") || !Q_stricmp(s, "2")) return 2;
    if (!Q_stricmp(s, "projector") || !Q_stricmp(s, "3")) return 3;
    return 0;
}

static dwDlv1Binding_t *R_DLV1_FindBinding(int fixtureId)
{
    int i;
    const char *map = tr.world ? tr.world->baseName : "";
    R_DLV1_LoadBindings();
    for (i = 0; i < s_dwDlv1BindingCount; ++i) {
        dwDlv1Binding_t *b = &s_dwDlv1Bindings[i];
        if (b->fixtureId == fixtureId && !Q_stricmp(b->mapName, map)) return b;
    }
    return NULL;
}

static staticPromotePersistentLight_t *R_DLV1_FindFixture(int fixtureId)
{
    int i;
    for (i = 0; i < s_staticPromotePersistentCount; ++i)
        if (s_staticPromotePersistentLights[i].candidate.entityOrdinal == fixtureId)
            return &s_staticPromotePersistentLights[i];
    return NULL;
}

static qboolean R_DLV1_OriginDead(const vec3_t origin)
{
    int i, count;
    R_DLV1_EnsureCvars();
    count = s_dwDlv1DeadCount ? s_dwDlv1DeadCount->integer : 0;
    count = CLAMP(count, 0, DW_DLV1_MAX_DEAD);
    for (i = 0; i < count; ++i) {
        float x, y, z;
        vec3_t d;
        if (!s_dwDlv1Dead[i] || sscanf(s_dwDlv1Dead[i]->string, "%f %f %f", &x, &y, &z) != 3)
            continue;
        VectorSet(d, origin[0]-x, origin[1]-y, origin[2]-z);
        if (DotProduct(d,d) <= 80.0f * 80.0f) return qtrue;
    }
    return qfalse;
}

static qboolean R_DLV1_FixtureEnabled(const staticPromotePersistentLight_t *light)
{
    dwDlv1Binding_t *b;
    if (!light) return qtrue;
    if (R_DLV1_OriginDead(light->candidate.origin)) return qfalse;
    b = R_DLV1_FindBinding(light->candidate.entityOrdinal);
    if (!b) return qtrue;
    R_DLV1_EnsureCvars();
    if (b->circuit < 1 || b->circuit > DW_DLV1_MAX_CIRCUITS) return qtrue;
    return s_dwDlv1Circuits[b->circuit - 1]->integer ? qtrue : qfalse;
}

static qboolean R_DLV1_FixtureIdEnabled(int fixtureId)
{
    staticPromotePersistentLight_t *light = R_DLV1_FindFixture(fixtureId);
    return light ? R_DLV1_FixtureEnabled(light) : qtrue;
}

static void R_DLV1_FilterDisabledSceneDlights(int *diagIndex)
{
    int i, out = 0;
    if (!tr.refdef.dlights || tr.refdef.num_dlights <= 0) return;
    for (i = 0; i < tr.refdef.num_dlights; ++i) {
        dlight_t *dl = &tr.refdef.dlights[i];
        int fixtureId = dl->physicalElectricOwnerId > 0 ?
            dl->physicalElectricOwnerId : dl->staticPromoteFixtureId;
        qboolean keep = fixtureId <= 0 || R_DLV1_FixtureIdEnabled(fixtureId);
        if (!keep) {
            if (diagIndex && *diagIndex == i) *diagIndex = -1;
            else if (diagIndex && *diagIndex > i) (*diagIndex)--;
            continue;
        }
        if (out != i) tr.refdef.dlights[out] = tr.refdef.dlights[i];
        out++;
    }
    tr.refdef.num_dlights = out;
}

static staticPromotePersistentLight_t *R_DLV1_PickFixture(void)
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

void R_DLV1_Bind_f(void)
{
    int circuit, type, i;
    staticPromotePersistentLight_t *light;
    dwDlv1Binding_t *b = NULL;
    if (ri.Cmd_Argc() < 3) {
        ri.Printf(PRINT_ALL, "usage: dw_dlr_bind <1..16> <ceiling|wall|projector>\n");
        return;
    }
    circuit = atoi(ri.Cmd_Argv(1));
    type = R_DLV1_LampType(ri.Cmd_Argv(2));
    if (circuit < 1 || circuit > DW_DLV1_MAX_CIRCUITS || !type) {
        ri.Printf(PRINT_WARNING, "DW_DLV1 invalid circuit/type\n");
        return;
    }
    R_DLV1_LoadBindings();
    light = R_DLV1_PickFixture();
    if (!light || !tr.world) {
        ri.Printf(PRINT_WARNING, "DW_DLV1 no StaticPromote fixture under view\n");
        return;
    }
    for (i = 0; i < s_dwDlv1BindingCount; ++i) {
        if (s_dwDlv1Bindings[i].fixtureId == light->candidate.entityOrdinal &&
            !Q_stricmp(s_dwDlv1Bindings[i].mapName, tr.world->baseName)) {
            b = &s_dwDlv1Bindings[i]; break;
        }
    }
    if (!b) {
        if (s_dwDlv1BindingCount >= DW_DLV1_MAX_BINDINGS) {
            ri.Printf(PRINT_WARNING, "DW_DLV1 binding registry full\n"); return;
        }
        b = &s_dwDlv1Bindings[s_dwDlv1BindingCount++];
        memset(b, 0, sizeof(*b));
        Q_strncpyz(b->mapName, tr.world->baseName, sizeof(b->mapName));
        b->fixtureId = light->candidate.entityOrdinal;
    }
    b->circuit = circuit;
    b->lampType = type;
    R_DLV1_SaveBindings();
    ri.Cvar_Set("dw_dl_lastFixture", va("%d", b->fixtureId));
    ri.Cvar_Set("dw_dl_lastCircuit", va("%d", b->circuit));
    ri.Printf(PRINT_ALL,
        "DW_DLV1 BOUND map=%s fixture=%d circuit=%d type=%d origin=(%.1f %.1f %.1f)\n",
        b->mapName, b->fixtureId, b->circuit, b->lampType,
        light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2]);
}

void R_DLV1_Unbind_f(void)
{
    int i, fixture;
    const char *map;
    if (!tr.world) return;
    fixture = ri.Cmd_Argc() > 1 ? atoi(ri.Cmd_Argv(1)) : -1;
    if (fixture < 0) {
        staticPromotePersistentLight_t *light = R_DLV1_PickFixture();
        if (!light) { ri.Printf(PRINT_WARNING, "DW_DLV1 no fixture under view\n"); return; }
        fixture = light->candidate.entityOrdinal;
    }
    map = tr.world->baseName;
    R_DLV1_LoadBindings();
    for (i = 0; i < s_dwDlv1BindingCount; ++i) {
        if (s_dwDlv1Bindings[i].fixtureId == fixture &&
            !Q_stricmp(s_dwDlv1Bindings[i].mapName, map)) {
            if (i + 1 < s_dwDlv1BindingCount)
                memmove(&s_dwDlv1Bindings[i], &s_dwDlv1Bindings[i+1],
                    (s_dwDlv1BindingCount-i-1)*sizeof(s_dwDlv1Bindings[0]));
            s_dwDlv1BindingCount--;
            R_DLV1_SaveBindings();
            ri.Printf(PRINT_ALL, "DW_DLV1 UNBOUND map=%s fixture=%d\n", map, fixture);
            return;
        }
    }
    ri.Printf(PRINT_ALL, "DW_DLV1 fixture=%d not bound\n", fixture);
}

void R_DLV1_List_f(void)
{
    int i;
    const char *map = tr.world ? tr.world->baseName : "";
    R_DLV1_LoadBindings();
    ri.Printf(PRINT_ALL, "DW_DLV1 bindings map=%s\n", map);
    for (i = 0; i < s_dwDlv1BindingCount; ++i) {
        dwDlv1Binding_t *b=&s_dwDlv1Bindings[i];
        if (!Q_stricmp(b->mapName,map))
            ri.Printf(PRINT_ALL, " fixture=%d circuit=%d type=%d enabled=%d\n",
                b->fixtureId,b->circuit,b->lampType,
                R_DLV1_FixtureIdEnabled(b->fixtureId)?1:0);
    }
}
'''

game_inc = r'''/* DARKWOLF_DESTRUCTIBLE_LIGHTS_V1 game-side switches and damage proxies */
#define DW_DLV1_MAX_CIRCUITS 16
#define DW_DLV1_MAX_DEAD 64

static int DW_Lights_Type(const char *s)
{
    if (!s || !*s) return 1;
    if (!Q_stricmp(s,"ceiling") || !Q_stricmp(s,"1")) return 1;
    if (!Q_stricmp(s,"wall") || !Q_stricmp(s,"2")) return 2;
    if (!Q_stricmp(s,"projector") || !Q_stricmp(s,"3")) return 3;
    return 0;
}

static const char *DW_Lights_SwitchModel(int type)
{
    switch(type) {
    default:
    case 1: return "models/mapobjects/electronics/alarmbox.md3";
    case 2: return "models/mapobjects/electronics/phone.md3";
    case 3: return "models/mapobjects/electronics/loudspeaker2.md3";
    }
}

void DW_Lights_SwitchUse(gentity_t *self, gentity_t *other, gentity_t *activator)
{
    char name[64], value[16];
    int current;
    if (!self) return;
    Com_sprintf(name,sizeof(name),"dw_lightCircuit%02d",CLAMP(self->count,1,DW_DLV1_MAX_CIRCUITS));
    current = trap_Cvar_VariableIntegerValue(name) ? 1 : 0;
    Com_sprintf(value,sizeof(value),"%d",current?0:1);
    trap_Cvar_Set(name,value);
    if (activator && activator->client)
        trap_SendServerCommand(activator-g_entities,
            va("print \"DarkWolf circuit %d: %s\n\"",self->count,current?"OFF":"ON"));
}

void DW_Lights_ProxyDie(gentity_t *self, gentity_t *inflictor, gentity_t *attacker, int damage, int mod)
{
    int slot = trap_Cvar_VariableIntegerValue("dw_dl_deadCount");
    char name[64], value[128];
    if (!self) return;
    slot = CLAMP(slot,0,DW_DLV1_MAX_DEAD);
    if (slot < DW_DLV1_MAX_DEAD) {
        Com_sprintf(name,sizeof(name),"dw_dl_dead%02d",slot);
        Com_sprintf(value,sizeof(value),"%.1f %.1f %.1f",
            self->r.currentOrigin[0],self->r.currentOrigin[1],self->r.currentOrigin[2]);
        trap_Cvar_Set(name,value);
        Com_sprintf(value,sizeof(value),"%d",slot+1);
        trap_Cvar_Set("dw_dl_deadCount",value);
    }
    if (attacker && attacker->client)
        trap_SendServerCommand(attacker-g_entities,
            va("print \"DarkWolf lamp destroyed (circuit %d)\n\"",self->count));
    G_FreeEntity(self);
}

static qboolean DW_Lights_TraceFromPlayer(gentity_t *ent, trace_t *tr, vec3_t forward)
{
    vec3_t start,end;
    if (!ent || !ent->client) return qfalse;
    AngleVectors(ent->client->ps.viewangles,forward,NULL,NULL);
    VectorCopy(ent->client->ps.origin,start);
    start[2] += ent->client->ps.viewheight;
    VectorMA(start,2048.0f,forward,end);
    trap_Trace(tr,start,NULL,NULL,end,ent->s.number,MASK_SHOT);
    return tr->fraction < 1.0f ? qtrue : qfalse;
}

static void DW_Lights_AddProxy(gentity_t *player, int circuit, int type)
{
    trace_t tr;
    vec3_t forward,origin;
    gentity_t *e;
    if (!DW_Lights_TraceFromPlayer(player,&tr,forward)) {
        trap_SendServerCommand(player-g_entities,"print \"DW lamp: aim at the lamp fixture first\n\"");
        return;
    }
    VectorMA(tr.endpos,-8.0f,forward,origin);
    e=G_Spawn();
    e->classname="dw_destructible_lamp";
    e->s.eType=ET_GENERAL;
    e->count=circuit;
    e->count2=type;
    e->health=24;
    e->takedamage=qtrue;
    e->die=DW_Lights_ProxyDie;
    e->r.contents=CONTENTS_SOLID;
    e->clipmask=MASK_SHOT;
    VectorSet(e->r.mins,-13,-13,-10);
    VectorSet(e->r.maxs, 13, 13, 10);
    G_SetOrigin(e,origin);
    trap_LinkEntity(e);
    trap_SendServerCommand(player-g_entities,
        va("print \"DW lamp proxy: circuit=%d type=%d at %.0f %.0f %.0f\n\"",
        circuit,type,origin[0],origin[1],origin[2]));
}

static void DW_Lights_AddSwitch(gentity_t *player, int circuit, int type)
{
    trace_t tr;
    vec3_t forward,origin,angles;
    gentity_t *e;
    const char *model;
    if (!DW_Lights_TraceFromPlayer(player,&tr,forward)) {
        trap_SendServerCommand(player-g_entities,"print \"DW switch: aim at a wall first\n\"");
        return;
    }
    VectorMA(tr.endpos,-5.0f,forward,origin);
    VectorSet(angles,0,player->client->ps.viewangles[YAW]+180.0f,0);
    e=G_Spawn();
    e->classname="dw_light_switch";
    e->s.eType=ET_GENERAL;
    e->count=circuit;
    e->count2=type;
    e->use=DW_Lights_SwitchUse;
    model=DW_Lights_SwitchModel(type);
    e->model=(char *)model;
    e->s.modelindex=G_ModelIndex(model);
    e->r.contents=CONTENTS_SOLID;
    e->clipmask=MASK_SHOT;
    VectorSet(e->r.mins,-9,-7,-12);
    VectorSet(e->r.maxs, 9, 7, 12);
    G_SetOrigin(e,origin);
    VectorCopy(angles,e->s.angles);
    VectorCopy(angles,e->r.currentAngles);
    trap_LinkEntity(e);
    trap_SendServerCommand(player-g_entities,
        va("print \"DW switch installed: circuit=%d type=%d\n\"",circuit,type));
}

static void DW_Lights_CircuitCommand(gentity_t *player)
{
    char a1[32],a2[32],name[64],value[16];
    int circuit,state,current;
    trap_Argv(1,a1,sizeof(a1)); trap_Argv(2,a2,sizeof(a2));
    circuit=atoi(a1);
    if(circuit<1 || circuit>DW_DLV1_MAX_CIRCUITS) return;
    Com_sprintf(name,sizeof(name),"dw_lightCircuit%02d",circuit);
    current=trap_Cvar_VariableIntegerValue(name)?1:0;
    if(!Q_stricmp(a2,"toggle")) state=!current;
    else state=atoi(a2)?1:0;
    Com_sprintf(value,sizeof(value),"%d",state);
    trap_Cvar_Set(name,value);
    trap_SendServerCommand(player-g_entities,
        va("print \"DarkWolf circuit %d: %s\n\"",circuit,state?"ON":"OFF"));
}

void DW_Lights_InitMap(void)
{
    int i;
    char name[64];
    trap_Cvar_Set("dw_dl_deadCount","0");
    for(i=1;i<=DW_DLV1_MAX_CIRCUITS;i++) {
        Com_sprintf(name,sizeof(name),"dw_lightCircuit%02d",i);
        trap_Cvar_Set(name,"1");
    }
}

static qboolean DW_Lights_ClientCommand(gentity_t *ent, const char *cmd)
{
    char a1[32],a2[32];
    int circuit,type;
    if (!Q_stricmp(cmd,"dw_lamp_proxy")) {
        trap_Argv(1,a1,sizeof(a1)); trap_Argv(2,a2,sizeof(a2));
        circuit=atoi(a1); type=DW_Lights_Type(a2);
        if(circuit>=1 && circuit<=DW_DLV1_MAX_CIRCUITS && type) DW_Lights_AddProxy(ent,circuit,type);
        return qtrue;
    }
    if (!Q_stricmp(cmd,"dw_switch_add")) {
        trap_Argv(1,a1,sizeof(a1)); trap_Argv(2,a2,sizeof(a2));
        circuit=atoi(a1); type=atoi(a2);
        if(circuit>=1 && circuit<=DW_DLV1_MAX_CIRCUITS && type>=1 && type<=3) DW_Lights_AddSwitch(ent,circuit,type);
        return qtrue;
    }
    if (!Q_stricmp(cmd,"dw_circuit")) {
        DW_Lights_CircuitCommand(ent); return qtrue;
    }
    return qfalse;
}
'''

cgame_inc = r'''/* DARKWOLF_DESTRUCTIBLE_LIGHTS_V1 local authoring wrappers */
static void CG_DWLampBind_f(void)
{
    char circuit[16], type[32], cmd[128];
    Q_strncpyz(circuit,CG_Argv(1),sizeof(circuit));
    Q_strncpyz(type,CG_Argv(2),sizeof(type));
    if(!circuit[0] || !type[0]) {
        CG_Printf("usage: dw_lamp_bind <1..16> <ceiling|wall|projector>\n"); return;
    }
    Com_sprintf(cmd,sizeof(cmd),"dw_dlr_bind %s %s\n",circuit,type);
    trap_SendConsoleCommand(cmd);
    trap_SendClientCommand(va("dw_lamp_proxy %s %s",circuit,type));
}
static void CG_DWSwitchAdd_f(void)
{
    char circuit[16], type[16];
    Q_strncpyz(circuit,CG_Argv(1),sizeof(circuit));
    Q_strncpyz(type,CG_Argv(2),sizeof(type));
    if(!circuit[0] || !type[0]) {
        CG_Printf("usage: dw_switch_add <1..16> <1|2|3>\n"); return;
    }
    trap_SendClientCommand(va("dw_switch_add %s %s",circuit,type));
}
static void CG_DWCircuit_f(void)
{
    char circuit[16], state[16];
    Q_strncpyz(circuit,CG_Argv(1),sizeof(circuit));
    Q_strncpyz(state,CG_Argv(2),sizeof(state));
    if(!circuit[0] || !state[0]) {
        CG_Printf("usage: dw_circuit <1..16> <0|1|toggle>\n"); return;
    }
    trap_SendClientCommand(va("dw_circuit %s %s",circuit,state));
}
'''

(code/"rend2"/"tr_destructible_lights_v1.inc").write_text(renderer_inc)
(code/"game"/"g_destructible_lights_v1.inc").write_text(game_inc)
(code/"cgame"/"cg_destructible_lights_v1.inc").write_text(cgame_inc)

# Renderer: include after StaticPromote registries, gate unified selection, filter after owner assignment.
edit("rend2/tr_scene.c",
'''static char s_staticPromoteWideMapName[MAX_QPATH] = "";

''',
'''static char s_staticPromoteWideMapName[MAX_QPATH] = "";

#include "tr_destructible_lights_v1.inc"

''')
edit("rend2/tr_scene.c",
'''\t\tallowed = R_StaticPromoteUSLRDAllowed(light, autoMapLights, &classReason);
\t\tif (!allowed)
''',
'''\t\tallowed = R_StaticPromoteUSLRDAllowed(light, autoMapLights, &classReason);
\t\tif (allowed && !R_DLV1_FixtureEnabled(light)) {
\t\t\tallowed = qfalse;
\t\t\tclassReason = STATIC_PROMOTE_CLASS_USER_BLOCKED;
\t\t}
\t\tif (!allowed)
''')
edit("rend2/tr_scene.c",
'''\tR_DarkWolfAssignPhysicalElectricOwnerIds(); // metadata only; Direct DLight is unchanged
''',
'''\tR_DarkWolfAssignPhysicalElectricOwnerIds(); // metadata only; Direct DLight is unchanged
\tR_DLV1_FilterDisabledSceneDlights(&dlightDiagInjectedIndex); // DARKWOLF_DESTRUCTIBLE_LIGHTS_V1
''')

# Renderer commands
edit("rend2/tr_init.c",
'''\tri.Cmd_AddCommand( "imagelist", R_ImageList_f );
''',
'''\tri.Cmd_AddCommand( "imagelist", R_ImageList_f );
\tri.Cmd_AddCommand( "dw_dlr_bind", R_DLV1_Bind_f );
\tri.Cmd_AddCommand( "dw_dlr_unbind", R_DLV1_Unbind_f );
\tri.Cmd_AddCommand( "dw_dlr_list", R_DLV1_List_f );
''')
edit("rend2/tr_init.c",
'''\tri.Cmd_RemoveCommand( "imagelist" );
''',
'''\tri.Cmd_RemoveCommand( "imagelist" );
\tri.Cmd_RemoveCommand( "dw_dlr_bind" );
\tri.Cmd_RemoveCommand( "dw_dlr_unbind" );
\tri.Cmd_RemoveCommand( "dw_dlr_list" );
''')

# Game include and command hook.
edit("game/g_cmds.c",
'''#include "g_local.h"
''',
'''#include "g_local.h"
#include "g_destructible_lights_v1.inc"
''')
edit("game/g_cmds.c",
'''\ttrap_Argv( 0, cmd, sizeof( cmd ) );

''',
'''\ttrap_Argv( 0, cmd, sizeof( cmd ) );

\tif (DW_Lights_ClientCommand(ent, cmd)) {
\t\treturn;
\t}

''')

# Activation path: custom switch use before stock special cases.
edit("game/g_cmds.c",
'''\ttraceEnt = &g_entities[trace.entityNum];

''',
'''\ttraceEnt = &g_entities[trace.entityNum];

\tif (traceEnt->classname && !Q_stricmp(traceEnt->classname, "dw_light_switch") && traceEnt->use) {
\t\ttraceEnt->use(traceEnt, ent, ent);
\t\treturn;
\t}

''')

# Reset runtime dead list and circuit states on map initialization.
edit("game/g_main.c",
'''\tG_SpawnEntitiesFromString();

''',
'''\tG_SpawnEntitiesFromString();
\tDW_Lights_InitMap();

''')
# expose declaration because function lives in g_cmds.c but called by g_main.c
edit("game/g_local.h",
'''void G_ProcessTagConnect( gentity_t *ent, qboolean clearAngles );
''',
'''void G_ProcessTagConnect( gentity_t *ent, qboolean clearAngles );
void DW_Lights_InitMap(void);
''')

# savegame function registry for runtime entities.
edit("game/g_func_decs.h",
'''extern void Cmd_Activate_f ( gentity_t * ent ) ;
''',
'''extern void Cmd_Activate_f ( gentity_t * ent ) ;
extern void DW_Lights_SwitchUse ( gentity_t * self , gentity_t * other , gentity_t * activator ) ;
extern void DW_Lights_ProxyDie ( gentity_t * self , gentity_t * inflictor , gentity_t * attacker , int damage , int mod ) ;
''')
edit("game/g_funcs.h",
'''{"Cmd_Activate_f", (byte *)Cmd_Activate_f},
''',
'''{"Cmd_Activate_f", (byte *)Cmd_Activate_f},
{"DW_Lights_SwitchUse", (byte *)DW_Lights_SwitchUse},
{"DW_Lights_ProxyDie", (byte *)DW_Lights_ProxyDie},
''')

# Cgame wrappers and command table.
edit("cgame/cg_consolecmds.c",
'''typedef struct {
\tchar    *cmd;
''',
'''#include "cg_destructible_lights_v1.inc"

typedef struct {
\tchar    *cmd;
''')
edit("cgame/cg_consolecmds.c",
'''static consoleCommand_t commands[] = {
''',
'''static consoleCommand_t commands[] = {
\t{ "dw_lamp_bind", CG_DWLampBind_f },
\t{ "dw_switch_add", CG_DWSwitchAdd_f },
\t{ "dw_circuit", CG_DWCircuit_f },
''')

print("DW_DESTRUCTIBLE_LIGHTS_V1_APPLY_PASS")
