#!/usr/bin/env python3
from pathlib import Path
import sys

src=Path(sys.argv[1] if len(sys.argv)>1 else "source")
code=src/"SP"/"code"
ginc=code/"game"/"g_destructible_lights_v1.inc"
rinc=code/"rend2"/"tr_destructible_lights_v1.inc"
cgents=code/"cgame"/"cg_ents.c"

for p in (ginc,rinc,cgents):
    if not p.exists():
        raise SystemExit(f"missing {p}")

# ---------------------------------------------------------------------------
# GAME: send explicit visual markers/state to cgame, exact fixture destruction.
# ---------------------------------------------------------------------------
g=ginc.read_text()

anchor="#define DW_DLV11_SWITCH_FILE \"darkwolf_switches_v11.txt\"\n"
insert=anchor+"""#define DW_DLV14_SWITCH_MAGIC 0x44575331 /* DWS1 */
#define DW_DLV14_LAMP_MAGIC   0x44574C31 /* DWL1 */
"""
if anchor not in g: raise SystemExit("game define anchor missing")
g=g.replace(anchor,insert,1)

old=r'''static void DW_Lights_SetSwitchVisual(gentity_t *e)
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
'''
new=r'''static void DW_Lights_SetSwitchVisual(gentity_t *e)
{
    const char *model;
    qboolean on;
    if (!e) return;
    on = DW_Lights_CircuitOn(e->count);
    model = DW_Lights_SwitchModelState(e->count2, on);
    e->model = (char *)model;

    /*
     * Keep the legacy modelindex path as a compatibility fallback, but V1.4
     * no longer depends on it for visibility.  The cgame recognizes this
     * network marker and registers/renders the model directly.
     */
    e->s.modelindex = G_ModelIndex(model);
    e->s.density = DW_DLV14_SWITCH_MAGIC;
    e->s.effect1Time = e->count2;       /* switch type */
    e->s.effect2Time = on ? 1 : 0;      /* circuit visual state */
}

static void DW_Lights_UpdateVisualStates(int circuit)
{
    int i;
    for (i = MAX_CLIENTS; i < level.num_entities; ++i) {
        gentity_t *e = &g_entities[i];
        if (!e->inuse || !e->classname) continue;
        if (circuit > 0 && e->count != circuit) continue;

        if (!Q_stricmp(e->classname, "dw_light_switch")) {
            DW_Lights_SetSwitchVisual(e);
        } else if (!Q_stricmp(e->classname, "dw_destructible_lamp")) {
            e->s.density = DW_DLV14_LAMP_MAGIC;
            e->s.effect1Time = e->count2; /* lamp type */
            e->s.effect2Time = DW_Lights_CircuitOn(e->count) ? 1 : 0;
        }
    }
}
'''
if old not in g: raise SystemExit("switch visual block missing")
g=g.replace(old,new,1)
g=g.replace("DW_Lights_UpdateSwitchModels(circuit);","DW_Lights_UpdateVisualStates(circuit);")

old=r'''static void DW_Lights_AddProxy(gentity_t *player, int circuit, int type)
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
'''
new=r'''static void DW_Lights_AddProxy(gentity_t *player, int circuit, int type)
{
    trace_t tr;
    vec3_t forward,normal,origin,angles;
    gentity_t *e;
    int fixtureId;
    if (!DW_Lights_TraceFromPlayer(player,&tr,forward)) {
        trap_SendServerCommand(player-g_entities,"print \"DW lamp: aim at the lamp fixture first\n\"");
        return;
    }

    VectorCopy(tr.plane.normal,normal);
    if (VectorNormalize(normal) == 0.0f)
        VectorScale(forward,-1.0f,normal);

    /*
     * Place the visual/damage proxy just outside the actually aimed lamp
     * surface.  This is much more stable than the old camera-forward offset.
     */
    VectorMA(tr.endpos,2.0f,normal,origin);
    vectoangles(normal,angles);

    fixtureId=trap_Cvar_VariableIntegerValue("dw_dl_lastFixture");

    e=G_Spawn();
    e->classname="dw_destructible_lamp";
    e->s.eType=ET_GENERAL;
    e->count=circuit;
    e->count2=type;
    e->s.otherEntityNum2=fixtureId;
    e->s.density=DW_DLV14_LAMP_MAGIC;
    e->s.effect1Time=type;
    e->s.effect2Time=DW_Lights_CircuitOn(circuit) ? 1 : 0;
    e->health=24;
    e->takedamage=qtrue;
    e->die=DW_Lights_ProxyDie;
    e->r.contents=CONTENTS_SOLID;
    e->clipmask=MASK_SHOT;
    VectorSet(e->r.mins,-10,-10,-10);
    VectorSet(e->r.maxs, 10, 10, 10);
    G_SetOrigin(e,origin);
    G_SetAngle(e,angles);
    trap_LinkEntity(e);
    trap_SendServerCommand(player-g_entities,
        va("print \"DW V1.4 lamp proxy: circuit=%d type=%d fixture=%d at %.1f %.1f %.1f\n\"",
        circuit,type,fixtureId,origin[0],origin[1],origin[2]));
}
'''
if old not in g: raise SystemExit("lamp proxy block missing")
g=g.replace(old,new,1)

old=r'''        Com_sprintf(name,sizeof(name),"dw_dl_dead%02d",slot);
        Com_sprintf(value,sizeof(value),"%.1f %.1f %.1f",
            self->r.currentOrigin[0],self->r.currentOrigin[1],self->r.currentOrigin[2]);
        trap_Cvar_Set(name,value);
'''
new=r'''        Com_sprintf(name,sizeof(name),"dw_dl_dead%02d",slot);
        if (self->s.otherEntityNum2 > 0)
            Com_sprintf(value,sizeof(value),"id:%d",self->s.otherEntityNum2);
        else
            Com_sprintf(value,sizeof(value),"%.1f %.1f %.1f",
                self->r.currentOrigin[0],self->r.currentOrigin[1],self->r.currentOrigin[2]);
        trap_Cvar_Set(name,value);
'''
if old not in g: raise SystemExit("proxy death record block missing")
g=g.replace(old,new,1)

ginc.write_text(g)

# ---------------------------------------------------------------------------
# RENDERER: exact fixture-id dead records, preserving legacy xyz compatibility.
# ---------------------------------------------------------------------------
r=rinc.read_text()
old=r'''static qboolean R_DLV1_OriginDead(const vec3_t origin)
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
'''
new=r'''static qboolean R_DLV1_FixtureDead(const staticPromotePersistentLight_t *light)
{
    int i, count;
    if (!light) return qfalse;
    R_DLV1_EnsureCvars();
    count = s_dwDlv1DeadCount ? s_dwDlv1DeadCount->integer : 0;
    count = CLAMP(count, 0, DW_DLV1_MAX_DEAD);
    for (i = 0; i < count; ++i) {
        const char *s;
        float x, y, z;
        vec3_t d;
        if (!s_dwDlv1Dead[i]) continue;
        s = s_dwDlv1Dead[i]->string;
        if (!Q_stricmpn(s,"id:",3)) {
            if (atoi(s+3) == light->candidate.entityOrdinal)
                return qtrue;
            continue;
        }
        if (sscanf(s, "%f %f %f", &x, &y, &z) != 3)
            continue;
        VectorSet(d, light->candidate.origin[0]-x,
                     light->candidate.origin[1]-y,
                     light->candidate.origin[2]-z);
        if (DotProduct(d,d) <= 80.0f * 80.0f) return qtrue;
    }
    return qfalse;
}
'''
if old not in r: raise SystemExit("renderer dead function missing")
r=r.replace(old,new,1)
r=r.replace("if (R_DLV1_OriginDead(light->candidate.origin)) return qfalse;",
            "if (R_DLV1_FixtureDead(light)) return qfalse;")
rinc.write_text(r)

# ---------------------------------------------------------------------------
# CGAME: direct switch model render + OFF bulb mask, before modelindex early-out.
# ---------------------------------------------------------------------------
c=cgents.read_text()
anchor="static void CG_General( centity_t *cent ) {\n"
helper=r'''#define DW_DLV14_SWITCH_MAGIC 0x44575331
#define DW_DLV14_LAMP_MAGIC   0x44574C31

static qhandle_t s_dwDlv14SwitchModel[3][2];
static qboolean s_dwDlv14SwitchModelTried[3][2];
static qhandle_t s_dwDlv14LampOffShader;
static qboolean s_dwDlv14LampOffShaderTried;

static const char *CG_DLV14_SwitchModelPath(int type, int on)
{
    switch (type) {
    default:
    case 1: return on ? "models/darkwolf/switches/toggle_on.md3"
                      : "models/darkwolf/switches/toggle_off.md3";
    case 2: return on ? "models/darkwolf/switches/knife_on.md3"
                      : "models/darkwolf/switches/knife_off.md3";
    case 3: return on ? "models/darkwolf/switches/rotary_on.md3"
                      : "models/darkwolf/switches/rotary_off.md3";
    }
}

static qhandle_t CG_DLV14_GetSwitchModel(int type, int on)
{
    int ti, si;
    const char *path;
    if (type < 1 || type > 3) type = 1;
    ti = type - 1;
    si = on ? 1 : 0;
    if (!s_dwDlv14SwitchModelTried[ti][si]) {
        s_dwDlv14SwitchModelTried[ti][si] = qtrue;
        path = CG_DLV14_SwitchModelPath(type,on);
        s_dwDlv14SwitchModel[ti][si] = trap_R_RegisterModel(path);
        CG_Printf("DW_DLV14 SWITCH_MODEL path=%s handle=%d\n",
            path,(int)s_dwDlv14SwitchModel[ti][si]);
    }
    return s_dwDlv14SwitchModel[ti][si];
}

static qhandle_t CG_DLV14_GetLampOffShader(void)
{
    if (!s_dwDlv14LampOffShaderTried) {
        s_dwDlv14LampOffShaderTried = qtrue;
        s_dwDlv14LampOffShader = trap_R_RegisterShader("darkwolf/dlv14_lamp_off");
        CG_Printf("DW_DLV14 LAMP_OFF_SHADER handle=%d\n",(int)s_dwDlv14LampOffShader);
    }
    return s_dwDlv14LampOffShader;
}

static qboolean CG_DLV14_CustomGeneral(centity_t *cent)
{
    const entityState_t *s1;
    refEntity_t ent;
    if (!cent) return qfalse;
    s1=&cent->currentState;

    if (s1->density == DW_DLV14_SWITCH_MAGIC) {
        qhandle_t h = CG_DLV14_GetSwitchModel(s1->effect1Time, s1->effect2Time ? 1 : 0);
        memset(&ent,0,sizeof(ent));
        VectorCopy(cent->lerpOrigin,ent.origin);
        VectorCopy(cent->lerpOrigin,ent.oldorigin);

        if (h) {
            ent.reType=RT_MODEL;
            ent.hModel=h;
            AnglesToAxis(cent->lerpAngles,ent.axis);
            /* Slight readability scale; no change to server collision. */
            VectorScale(ent.axis[0],1.15f,ent.axis[0]);
            VectorScale(ent.axis[1],1.15f,ent.axis[1]);
            VectorScale(ent.axis[2],1.15f,ent.axis[2]);
            ent.nonNormalizedAxes=qtrue;
            trap_R_AddRefEntityToScene(&ent);
        } else {
            /* Guaranteed visible fallback if a custom MD3 ever fails to load. */
            ent.reType=RT_SPRITE;
            ent.radius=9.0f;
            ent.customShader=cgs.media.whiteShader;
            ent.shaderRGBA[0]=86;
            ent.shaderRGBA[1]=78;
            ent.shaderRGBA[2]=61;
            ent.shaderRGBA[3]=255;
            trap_R_AddRefEntityToScene(&ent);
        }
        return qtrue;
    }

    if (s1->density == DW_DLV14_LAMP_MAGIC) {
        /*
         * The proxy itself stays visually absent while ON.  When OFF, draw a
         * small dark circular cover over the actually aimed bulb/fixture point.
         * This is local per-lamp and never remaps a shared BSP shader.
         */
        if (!s1->effect2Time) {
            qhandle_t sh = CG_DLV14_GetLampOffShader();
            memset(&ent,0,sizeof(ent));
            ent.reType=RT_SPRITE;
            VectorCopy(cent->lerpOrigin,ent.origin);
            ent.radius = (s1->effect1Time == 3) ? 9.0f :
                         (s1->effect1Time == 2) ? 8.0f : 7.0f;
            ent.customShader = sh ? sh : cgs.media.smokePuffShader;
            ent.shaderRGBA[0]=255;
            ent.shaderRGBA[1]=255;
            ent.shaderRGBA[2]=255;
            ent.shaderRGBA[3]=255;
            trap_R_AddRefEntityToScene(&ent);
        }
        return qtrue;
    }

    return qfalse;
}

'''
if anchor not in c: raise SystemExit("CG_General anchor missing")
c=c.replace(anchor,helper+anchor,1)
needle="\ts1 = &cent->currentState;\n\n\t// if set to invisible, skip\n"
replacement="\ts1 = &cent->currentState;\n\n\tif (CG_DLV14_CustomGeneral(cent)) {\n\t\treturn;\n\t}\n\n\t// if set to invisible, skip\n"
if needle not in c: raise SystemExit("CG_General currentState anchor missing")
c=c.replace(needle,replacement,1)
cgents.write_text(c)

print("DW_DESTRUCTIBLE_LIGHTS_V14_VISUAL_STATE_APPLY_PASS")
