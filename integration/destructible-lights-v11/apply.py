#!/usr/bin/env python3
from pathlib import Path
import sys

src = Path(sys.argv[1] if len(sys.argv) > 1 else "source")
code = src / "SP" / "code"

game = code / "game" / "g_destructible_lights_v1.inc"
cgame = code / "cgame" / "cg_destructible_lights_v1.inc"

if not game.exists() or not cgame.exists():
    raise SystemExit("V1 must be applied before V1.1")

game.write_text(r'''/* DARKWOLF_DESTRUCTIBLE_LIGHTS_V11
 * Persistent runtime switches + surface-normal placement.
 * V1 physical light ownership/filtering remains unchanged.
 */
#define DW_DLV1_MAX_CIRCUITS 16
#define DW_DLV1_MAX_DEAD 64
#define DW_DLV11_MAX_SWITCHES 128
#define DW_DLV11_SWITCH_FILE "darkwolf_switches_v11.txt"

typedef struct dwSwitchPersist_s {
    char mapName[MAX_QPATH];
    int circuit;
    int type; /* 1 toggle, 2 knife, 3 rotary */
    vec3_t origin;
    vec3_t normal;
} dwSwitchPersist_t;

static dwSwitchPersist_t s_dwSwitchPersist[DW_DLV11_MAX_SWITCHES];
static int s_dwSwitchPersistCount;
static qboolean s_dwSwitchPersistLoaded;

static int DW_Lights_Type(const char *s)
{
    if (!s || !*s) return 1;
    if (!Q_stricmp(s,"ceiling") || !Q_stricmp(s,"1")) return 1;
    if (!Q_stricmp(s,"wall") || !Q_stricmp(s,"2")) return 2;
    if (!Q_stricmp(s,"projector") || !Q_stricmp(s,"3")) return 3;
    return 0;
}

static int DW_Lights_SwitchType(const char *s)
{
    if (!s || !*s) return 1;
    if (!Q_stricmp(s,"toggle") || !Q_stricmp(s,"1")) return 1;
    if (!Q_stricmp(s,"knife") || !Q_stricmp(s,"2")) return 2;
    if (!Q_stricmp(s,"rotary") || !Q_stricmp(s,"3")) return 3;
    return 0;
}

static const char *DW_Lights_SwitchTypeName(int type)
{
    switch (type) {
    default:
    case 1: return "toggle";
    case 2: return "knife";
    case 3: return "rotary";
    }
}

static const char *DW_Lights_SwitchModelState(int type, qboolean on)
{
    switch(type) {
    default:
    case 1:
        return on ? "models/darkwolf/switches/toggle_on.md3"
                  : "models/darkwolf/switches/toggle_off.md3";
    case 2:
        return on ? "models/darkwolf/switches/knife_on.md3"
                  : "models/darkwolf/switches/knife_off.md3";
    case 3:
        return on ? "models/darkwolf/switches/rotary_on.md3"
                  : "models/darkwolf/switches/rotary_off.md3";
    }
}

static void DW_Lights_CurrentMap(char *out, int outSize)
{
    trap_Cvar_VariableStringBuffer("mapname", out, outSize);
    if (!out[0]) Q_strncpyz(out, "unknown", outSize);
}

static qboolean DW_Lights_CircuitOn(int circuit)
{
    char name[64];
    if (circuit < 1 || circuit > DW_DLV1_MAX_CIRCUITS) return qtrue;
    Com_sprintf(name,sizeof(name),"dw_lightCircuit%02d",circuit);
    return trap_Cvar_VariableIntegerValue(name) ? qtrue : qfalse;
}

static void DW_Lights_SetSwitchVisual(gentity_t *e)
{
    const char *model;
    if (!e) return;
    model = DW_Lights_SwitchModelState(e->count2, DW_Lights_CircuitOn(e->count));
    e->model = (char *)model;
    e->s.modelindex = G_ModelIndex(model);
}

static void DW_Lights_UpdateSwitchModels(int circuit)
{
    int i;
    for (i = MAX_CLIENTS; i < level.num_entities; ++i) {
        gentity_t *e = &g_entities[i];
        if (!e->inuse || !e->classname) continue;
        if (Q_stricmp(e->classname, "dw_light_switch")) continue;
        if (circuit > 0 && e->count != circuit) continue;
        DW_Lights_SetSwitchVisual(e);
    }
}

static void DW_Lights_LoadSwitchRegistry(void)
{
    fileHandle_t f = 0;
    int len;
    char *buffer, *p;

    if (s_dwSwitchPersistLoaded) return;
    s_dwSwitchPersistLoaded = qtrue;
    s_dwSwitchPersistCount = 0;

    len = trap_FS_FOpenFile(DW_DLV11_SWITCH_FILE, &f, FS_READ);
    if (len <= 0 || !f) {
        if (f) trap_FS_FCloseFile(f);
        return;
    }
    if (len > 65535) {
        trap_FS_FCloseFile(f);
        G_Printf("DW_DLV11: registry too large, ignored\n");
        return;
    }

    buffer = G_Alloc(len + 1);
    trap_FS_Read(buffer, len, f);
    trap_FS_FCloseFile(f);
    buffer[len] = 0;
    p = buffer;

    while (*p && s_dwSwitchPersistCount < DW_DLV11_MAX_SWITCHES) {
        char line[320], mapName[MAX_QPATH];
        int n = 0, circuit = 0, type = 0;
        float ox,oy,oz,nx,ny,nz;
        while (p[n] && p[n] != '\n' && p[n] != '\r' && n < (int)sizeof(line)-1) {
            line[n] = p[n];
            ++n;
        }
        line[n] = 0;
        while (*p && *p != '\n') ++p;
        if (*p == '\n') ++p;
        if (!line[0] || line[0] == '#') continue;

        if (sscanf(line,"%63s %d %d %f %f %f %f %f %f",
                   mapName,&circuit,&type,&ox,&oy,&oz,&nx,&ny,&nz) == 9 &&
            circuit >= 1 && circuit <= DW_DLV1_MAX_CIRCUITS &&
            type >= 1 && type <= 3) {
            dwSwitchPersist_t *r = &s_dwSwitchPersist[s_dwSwitchPersistCount++];
            Q_strncpyz(r->mapName,mapName,sizeof(r->mapName));
            r->circuit = circuit;
            r->type = type;
            VectorSet(r->origin,ox,oy,oz);
            VectorSet(r->normal,nx,ny,nz);
            if (VectorNormalize(r->normal) == 0.0f) VectorSet(r->normal,1,0,0);
        }
    }
}

static qboolean DW_Lights_SaveSwitchRegistry(void)
{
    fileHandle_t f = 0;
    char out[32768], line[320];
    int i, len;
    out[0] = 0;
    Q_strcat(out,sizeof(out),
        "# DarkWolf Destructible Lights V1.1 persistent switches\n"
        "# map circuit type originX originY originZ normalX normalY normalZ\n");
    for (i=0;i<s_dwSwitchPersistCount;i++) {
        const dwSwitchPersist_t *r=&s_dwSwitchPersist[i];
        Com_sprintf(line,sizeof(line),"%s %d %d %.3f %.3f %.3f %.6f %.6f %.6f\n",
            r->mapName,r->circuit,r->type,
            r->origin[0],r->origin[1],r->origin[2],
            r->normal[0],r->normal[1],r->normal[2]);
        if (strlen(out) + strlen(line) + 1 >= sizeof(out)) {
            G_Printf("DW_DLV11: registry buffer full\n");
            return qfalse;
        }
        Q_strcat(out,sizeof(out),line);
    }
    if (trap_FS_FOpenFile(DW_DLV11_SWITCH_FILE,&f,FS_WRITE) < 0 || !f) {
        G_Printf("DW_DLV11: cannot write %s\n",DW_DLV11_SWITCH_FILE);
        return qfalse;
    }
    len=(int)strlen(out);
    if (trap_FS_Write(out,len,f) != len) {
        trap_FS_FCloseFile(f);
        G_Printf("DW_DLV11: short write %s\n",DW_DLV11_SWITCH_FILE);
        return qfalse;
    }
    trap_FS_FCloseFile(f);
    return qtrue;
}

void DW_Lights_SwitchUse(gentity_t *self, gentity_t *other, gentity_t *activator);

static void DW_Lights_SpawnSwitchRecord(const dwSwitchPersist_t *r)
{
    gentity_t *e;
    vec3_t angles;
    if (!r) return;

    e=G_Spawn();
    e->classname="dw_light_switch";
    e->s.eType=ET_GENERAL;
    e->count=r->circuit;
    e->count2=r->type;
    e->use=DW_Lights_SwitchUse;
    e->r.contents=CONTENTS_SOLID;
    e->clipmask=MASK_SHOT;

    /* Custom models are authored with +X pointing out from the wall. */
    vectoangles(r->normal,angles);
    G_SetOrigin(e,r->origin);
    VectorCopy(angles,e->s.angles);
    VectorCopy(angles,e->r.currentAngles);

    VectorSet(e->r.mins,-2,-11,-16);
    VectorSet(e->r.maxs,12,11,16);
    DW_Lights_SetSwitchVisual(e);
    trap_LinkEntity(e);
}

void DW_Lights_SwitchUse(gentity_t *self, gentity_t *other, gentity_t *activator)
{
    char name[64], value[16];
    int current, circuit;
    if (!self) return;
    circuit=self->count;
    if (circuit < 1) circuit=1;
    if (circuit > DW_DLV1_MAX_CIRCUITS) circuit=DW_DLV1_MAX_CIRCUITS;

    Com_sprintf(name,sizeof(name),"dw_lightCircuit%02d",circuit);
    current=trap_Cvar_VariableIntegerValue(name) ? 1 : 0;
    Com_sprintf(value,sizeof(value),"%d",current?0:1);
    trap_Cvar_Set(name,value);
    DW_Lights_UpdateSwitchModels(circuit);

    if (activator && activator->client)
        trap_SendServerCommand(activator-g_entities,
            va("print \"DarkWolf circuit %d: %s\n\"",circuit,current?"OFF":"ON"));
}

void DW_Lights_ProxyDie(gentity_t *self, gentity_t *inflictor, gentity_t *attacker, int damage, int mod)
{
    int slot=trap_Cvar_VariableIntegerValue("dw_dl_deadCount");
    char name[64], value[128];
    if (!self) return;
    if (slot < 0) slot=0;
    if (slot > DW_DLV1_MAX_DEAD) slot=DW_DLV1_MAX_DEAD;
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
    start[2]+=ent->client->ps.viewheight;
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
    VectorSet(e->r.maxs,13,13,10);
    G_SetOrigin(e,origin);
    trap_LinkEntity(e);
    trap_SendServerCommand(player-g_entities,
        va("print \"DW lamp proxy: circuit=%d type=%d at %.0f %.0f %.0f\n\"",
        circuit,type,origin[0],origin[1],origin[2]));
}

static qboolean DW_Lights_SwitchDuplicate(const char *mapName, const vec3_t origin)
{
    int i;
    DW_Lights_LoadSwitchRegistry();
    for (i=0;i<s_dwSwitchPersistCount;i++) {
        vec3_t d;
        if (Q_stricmp(s_dwSwitchPersist[i].mapName,mapName)) continue;
        VectorSubtract(s_dwSwitchPersist[i].origin,origin,d);
        if (DotProduct(d,d) < 64.0f) return qtrue;
    }
    return qfalse;
}

static void DW_Lights_AddSwitch(gentity_t *player, int circuit, int type)
{
    trace_t tr;
    vec3_t forward,normal,origin;
    char mapName[MAX_QPATH];
    dwSwitchPersist_t *r;

    if (!DW_Lights_TraceFromPlayer(player,&tr,forward)) {
        trap_SendServerCommand(player-g_entities,"print \"DW switch: aim at a wall first\n\"");
        return;
    }
    VectorCopy(tr.plane.normal,normal);
    if (VectorNormalize(normal) == 0.0f) {
        trap_SendServerCommand(player-g_entities,"print \"DW switch: invalid surface normal\n\"");
        return;
    }

    /* Keep the back plate just outside the traced wall. */
    VectorMA(tr.endpos,0.75f,normal,origin);
    DW_Lights_CurrentMap(mapName,sizeof(mapName));
    if (DW_Lights_SwitchDuplicate(mapName,origin)) {
        trap_SendServerCommand(player-g_entities,"print \"DW switch: a persistent switch already exists here\n\"");
        return;
    }

    if (s_dwSwitchPersistCount >= DW_DLV11_MAX_SWITCHES) {
        trap_SendServerCommand(player-g_entities,"print \"DW switch registry is full\n\"");
        return;
    }
    r=&s_dwSwitchPersist[s_dwSwitchPersistCount++];
    memset(r,0,sizeof(*r));
    Q_strncpyz(r->mapName,mapName,sizeof(r->mapName));
    r->circuit=circuit;
    r->type=type;
    VectorCopy(origin,r->origin);
    VectorCopy(normal,r->normal);

    if (!DW_Lights_SaveSwitchRegistry()) {
        --s_dwSwitchPersistCount;
        trap_SendServerCommand(player-g_entities,"print \"DW switch: persistence write failed\n\"");
        return;
    }

    DW_Lights_SpawnSwitchRecord(r);
    trap_SendServerCommand(player-g_entities,
        va("print \"DW persistent switch installed: circuit=%d type=%s normal=(%.2f %.2f %.2f)\n\"",
        circuit,DW_Lights_SwitchTypeName(type),normal[0],normal[1],normal[2]));
}

static void DW_Lights_RemoveSwitch(gentity_t *player)
{
    trace_t tr;
    vec3_t forward;
    gentity_t *e;
    char mapName[MAX_QPATH];
    int i;

    if (!DW_Lights_TraceFromPlayer(player,&tr,forward) || tr.entityNum < 0 || tr.entityNum >= level.num_entities) {
        trap_SendServerCommand(player-g_entities,"print \"DW switch remove: aim directly at a switch\n\"");
        return;
    }
    e=&g_entities[tr.entityNum];
    if (!e->inuse || !e->classname || Q_stricmp(e->classname,"dw_light_switch")) {
        trap_SendServerCommand(player-g_entities,"print \"DW switch remove: aimed entity is not a DarkWolf switch\n\"");
        return;
    }

    DW_Lights_CurrentMap(mapName,sizeof(mapName));
    DW_Lights_LoadSwitchRegistry();
    for (i=0;i<s_dwSwitchPersistCount;i++) {
        vec3_t d;
        if (Q_stricmp(s_dwSwitchPersist[i].mapName,mapName)) continue;
        VectorSubtract(s_dwSwitchPersist[i].origin,e->r.currentOrigin,d);
        if (DotProduct(d,d) <= 16.0f) {
            if (i+1 < s_dwSwitchPersistCount)
                memmove(&s_dwSwitchPersist[i],&s_dwSwitchPersist[i+1],
                    (s_dwSwitchPersistCount-i-1)*sizeof(s_dwSwitchPersist[0]));
            --s_dwSwitchPersistCount;
            DW_Lights_SaveSwitchRegistry();
            G_FreeEntity(e);
            trap_SendServerCommand(player-g_entities,"print \"DW persistent switch removed\n\"");
            return;
        }
    }
    trap_SendServerCommand(player-g_entities,"print \"DW switch remove: registry entry not found\n\"");
}

static void DW_Lights_ListSwitches(gentity_t *player)
{
    char mapName[MAX_QPATH];
    int i, shown=0;
    DW_Lights_CurrentMap(mapName,sizeof(mapName));
    DW_Lights_LoadSwitchRegistry();
    trap_SendServerCommand(player-g_entities,
        va("print \"DW persistent switches map=%s\n\"",mapName));
    for (i=0;i<s_dwSwitchPersistCount;i++) {
        const dwSwitchPersist_t *r=&s_dwSwitchPersist[i];
        if (Q_stricmp(r->mapName,mapName)) continue;
        trap_SendServerCommand(player-g_entities,
            va("print \" #%d circuit=%d type=%s origin=(%.0f %.0f %.0f) normal=(%.2f %.2f %.2f)\n\"",
               shown+1,r->circuit,DW_Lights_SwitchTypeName(r->type),
               r->origin[0],r->origin[1],r->origin[2],
               r->normal[0],r->normal[1],r->normal[2]));
        ++shown;
    }
    if (!shown) trap_SendServerCommand(player-g_entities,"print \" (none)\n\"");
}

static void DW_Lights_CircuitCommand(gentity_t *player)
{
    char a1[32],a2[32],name[64],value[16];
    int circuit,state,current;
    trap_Argv(1,a1,sizeof(a1));
    trap_Argv(2,a2,sizeof(a2));
    circuit=atoi(a1);
    if(circuit<1 || circuit>DW_DLV1_MAX_CIRCUITS) return;
    Com_sprintf(name,sizeof(name),"dw_lightCircuit%02d",circuit);
    current=trap_Cvar_VariableIntegerValue(name)?1:0;
    if(!Q_stricmp(a2,"toggle")) state=!current;
    else state=atoi(a2)?1:0;
    Com_sprintf(value,sizeof(value),"%d",state);
    trap_Cvar_Set(name,value);
    DW_Lights_UpdateSwitchModels(circuit);
    trap_SendServerCommand(player-g_entities,
        va("print \"DarkWolf circuit %d: %s\n\"",circuit,state?"ON":"OFF"));
}

void DW_Lights_InitMap(void)
{
    int i;
    char name[64], mapName[MAX_QPATH];

    trap_Cvar_Set("dw_dl_deadCount","0");
    for(i=1;i<=DW_DLV1_MAX_CIRCUITS;i++) {
        Com_sprintf(name,sizeof(name),"dw_lightCircuit%02d",i);
        trap_Cvar_Set(name,"1");
    }

    /* Game DLL can survive map transitions, so force registry refresh each map. */
    s_dwSwitchPersistLoaded=qfalse;
    s_dwSwitchPersistCount=0;
    DW_Lights_LoadSwitchRegistry();

    /*
     * During a savegame restore the save system will restore entities itself.
     * Skip registry spawning in that one path to avoid duplicates.
     */
    if (trap_Cvar_VariableIntegerValue("savegame_loading")) return;

    DW_Lights_CurrentMap(mapName,sizeof(mapName));
    for(i=0;i<s_dwSwitchPersistCount;i++) {
        if (!Q_stricmp(s_dwSwitchPersist[i].mapName,mapName))
            DW_Lights_SpawnSwitchRecord(&s_dwSwitchPersist[i]);
    }
    G_Printf("DW_DLV11: restored persistent switches for %s\n",mapName);
}

static qboolean DW_Lights_ClientCommand(gentity_t *ent, const char *cmd)
{
    char a1[32],a2[32];
    int circuit,type;

    if (!Q_stricmp(cmd,"dw_lamp_proxy")) {
        trap_Argv(1,a1,sizeof(a1));
        trap_Argv(2,a2,sizeof(a2));
        circuit=atoi(a1);
        type=DW_Lights_Type(a2);
        if(circuit>=1 && circuit<=DW_DLV1_MAX_CIRCUITS && type)
            DW_Lights_AddProxy(ent,circuit,type);
        return qtrue;
    }
    if (!Q_stricmp(cmd,"dw_switch_add")) {
        trap_Argv(1,a1,sizeof(a1));
        trap_Argv(2,a2,sizeof(a2));
        circuit=atoi(a1);
        type=DW_Lights_SwitchType(a2);
        if(circuit>=1 && circuit<=DW_DLV1_MAX_CIRCUITS && type)
            DW_Lights_AddSwitch(ent,circuit,type);
        else
            trap_SendServerCommand(ent-g_entities,
                "print \"usage: dw_switch_add <1..16> <toggle|knife|rotary|1|2|3>\n\"");
        return qtrue;
    }
    if (!Q_stricmp(cmd,"dw_switch_remove")) {
        DW_Lights_RemoveSwitch(ent);
        return qtrue;
    }
    if (!Q_stricmp(cmd,"dw_switch_list")) {
        DW_Lights_ListSwitches(ent);
        return qtrue;
    }
    if (!Q_stricmp(cmd,"dw_circuit")) {
        DW_Lights_CircuitCommand(ent);
        return qtrue;
    }
    return qfalse;
}
''')

cgame.write_text(r'''/* DARKWOLF_DESTRUCTIBLE_LIGHTS_V11 local authoring wrappers */
static void CG_DWLampBind_f(void)
{
    char circuit[16], type[32], cmd[128];
    Q_strncpyz(circuit,CG_Argv(1),sizeof(circuit));
    Q_strncpyz(type,CG_Argv(2),sizeof(type));
    if(!circuit[0] || !type[0]) {
        CG_Printf("usage: dw_lamp_bind <1..16> <ceiling|wall|projector>\n");
        return;
    }
    Com_sprintf(cmd,sizeof(cmd),"dw_dlr_bind %s %s\n",circuit,type);
    trap_SendConsoleCommand(cmd);
    trap_SendClientCommand(va("dw_lamp_proxy %s %s",circuit,type));
}
static void CG_DWSwitchAdd_f(void)
{
    char circuit[16], type[32];
    Q_strncpyz(circuit,CG_Argv(1),sizeof(circuit));
    Q_strncpyz(type,CG_Argv(2),sizeof(type));
    if(!circuit[0] || !type[0]) {
        CG_Printf("usage: dw_switch_add <1..16> <toggle|knife|rotary|1|2|3>\n");
        return;
    }
    trap_SendClientCommand(va("dw_switch_add %s %s",circuit,type));
}
static void CG_DWSwitchRemove_f(void)
{
    trap_SendClientCommand("dw_switch_remove");
}
static void CG_DWSwitchList_f(void)
{
    trap_SendClientCommand("dw_switch_list");
}
static void CG_DWCircuit_f(void)
{
    char circuit[16], state[16];
    Q_strncpyz(circuit,CG_Argv(1),sizeof(circuit));
    Q_strncpyz(state,CG_Argv(2),sizeof(state));
    if(!circuit[0] || !state[0]) {
        CG_Printf("usage: dw_circuit <1..16> <0|1|toggle>\n");
        return;
    }
    trap_SendClientCommand(va("dw_circuit %s %s",circuit,state));
}
''')

# Add V1.1 local commands to the existing command table created by V1.
p=code/"cgame"/"cg_consolecmds.c"
s=p.read_text()
anchor='''\t{ "dw_switch_add", CG_DWSwitchAdd_f },
\t{ "dw_circuit", CG_DWCircuit_f },
'''
replacement='''\t{ "dw_switch_add", CG_DWSwitchAdd_f },
\t{ "dw_switch_remove", CG_DWSwitchRemove_f },
\t{ "dw_switch_list", CG_DWSwitchList_f },
\t{ "dw_circuit", CG_DWCircuit_f },
'''
if s.count(anchor)!=1:
    raise SystemExit("V1.1 cgame command anchor mismatch")
p.write_text(s.replace(anchor,replacement))

print("DW_DESTRUCTIBLE_LIGHTS_V11_APPLY_PASS")
