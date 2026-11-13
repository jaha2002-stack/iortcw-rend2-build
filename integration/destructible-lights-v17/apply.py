#!/usr/bin/env python3
from pathlib import Path
import sys

src=Path(sys.argv[1] if len(sys.argv)>1 else "source")
code=src/"SP"/"code"
rinc=code/"rend2"/"tr_destructible_lights_v1.inc"
ginc=code/"game"/"g_destructible_lights_v1.inc"
cg=code/"cgame"/"cg_ents.c"

for p in (rinc,ginc,cg):
    if not p.exists():
        raise SystemExit(f"missing {p}")

# ---------------------------------------------------------------------------
# RENDERER: publish exact fixture origin; hard-remove OFF/dead DLight entries.
# ---------------------------------------------------------------------------
r=rinc.read_text()

old='''        ri.Cvar_Get("dw_dl_lastFixture", "-1", 0);
        ri.Cvar_Get("dw_dl_lastCircuit", "0", 0);
'''
new='''        ri.Cvar_Get("dw_dl_lastFixture", "-1", 0);
        ri.Cvar_Get("dw_dl_lastCircuit", "0", 0);
        ri.Cvar_Get("dw_dl_lastOrigin", "0 0 0", 0);
'''
if old not in r: raise SystemExit("renderer cvar anchor missing")
r=r.replace(old,new,1)

old='''    ri.Cvar_Set("dw_dl_lastFixture", va("%d", b->fixtureId));
    ri.Cvar_Set("dw_dl_lastCircuit", va("%d", b->circuit));
    ri.Printf(PRINT_ALL,
'''
new='''    ri.Cvar_Set("dw_dl_lastFixture", va("%d", b->fixtureId));
    ri.Cvar_Set("dw_dl_lastCircuit", va("%d", b->circuit));
    ri.Cvar_Set("dw_dl_lastOrigin", va("%.3f %.3f %.3f",
        light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2]));
    ri.Printf(PRINT_ALL,
'''
if old not in r: raise SystemExit("renderer bind cvar anchor missing")
r=r.replace(old,new,1)

old='''static void R_DLV1_FilterDisabledSceneDlights(int *diagIndex)
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
'''
new='''static void R_DLV1_FilterDisabledSceneDlights(int *diagIndex)
{
    int i, out = 0;
    int oldCount;
    if (!tr.refdef.dlights || tr.refdef.num_dlights <= 0) return;

    oldCount = tr.refdef.num_dlights;

    /*
     * V1.7 PHYSICAL OFF CONTRACT:
     * OFF/dead fixtures are removed from the actual refdef DLight array, not
     * dimmed.  This happens after PhysicalElectricOwner assignment and before
     * point-shadow/LocalVol consumers.  Therefore an OFF fixture owns no
     * current-frame DLight and cannot consume a point-shadow selection slot.
     */
    for (i = 0; i < oldCount; ++i) {
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

    /*
     * Clear the removed tail as well.  Normal consumers obey num_dlights, but
     * zeroing stale entries guarantees that no legacy fixed-index shadow/cache
     * path can accidentally retain the disabled light's metadata.
     */
    for (i = out; i < oldCount; ++i)
        memset(&tr.refdef.dlights[i], 0, sizeof(tr.refdef.dlights[i]));

    tr.refdef.num_dlights = out;
}
'''
if old not in r: raise SystemExit("renderer filter anchor missing")
r=r.replace(old,new,1)
rinc.write_text(r)

# ---------------------------------------------------------------------------
# GAME: keep damage proxy where shooting works, but network exact fixture origin
# separately for cgame OFF cover. Destroyed proxy remains as permanent dark state.
# ---------------------------------------------------------------------------
g=ginc.read_text()

old='''    fixtureId=trap_Cvar_VariableIntegerValue("dw_dl_lastFixture");

    e=G_Spawn();
'''
new='''    fixtureId=trap_Cvar_VariableIntegerValue("dw_dl_lastFixture");

    {
        char exactOriginString[128];
        vec3_t exactOrigin;
        trap_Cvar_VariableStringBuffer("dw_dl_lastOrigin",
            exactOriginString,sizeof(exactOriginString));
        if (sscanf(exactOriginString,"%f %f %f",
            &exactOrigin[0],&exactOrigin[1],&exactOrigin[2]) == 3) {
            /*
             * origin2 is networked separately from the collision proxy.
             * The proxy remains at the actually shot surface, while cgame
             * renders the OFF bulb cover at the renderer's exact fixture origin.
             */
            VectorCopy(exactOrigin,e ? e->s.origin2 : exactOrigin);
        }
    }

    e=G_Spawn();
'''
# Can't write to e before spawn. Replace with correct block in one shot.
if old not in g: raise SystemExit("game fixture id anchor missing")
new='''    fixtureId=trap_Cvar_VariableIntegerValue("dw_dl_lastFixture");

    e=G_Spawn();
'''
g=g.replace(old,new,1)

old='''    e->s.otherEntityNum2=fixtureId;
    e->s.density=0;
    e->s.effect3Time=DW_DLV14_LAMP_MAGIC;
'''
new='''    e->s.otherEntityNum2=fixtureId;
    {
        char exactOriginString[128];
        vec3_t exactOrigin;
        trap_Cvar_VariableStringBuffer("dw_dl_lastOrigin",
            exactOriginString,sizeof(exactOriginString));
        if (sscanf(exactOriginString,"%f %f %f",
            &exactOrigin[0],&exactOrigin[1],&exactOrigin[2]) == 3)
            VectorCopy(exactOrigin,e->s.origin2);
        else
            VectorCopy(origin,e->s.origin2);
    }
    e->s.density=0;
    e->s.effect3Time=DW_DLV14_LAMP_MAGIC;
'''
if old not in g: raise SystemExit("game lamp network origin anchor missing")
g=g.replace(old,new,1)

old='''        } else if (!Q_stricmp(e->classname, "dw_destructible_lamp")) {
            e->s.density = DW_DLV14_LAMP_MAGIC;
            e->s.effect1Time = e->count2; /* lamp type */
            e->s.effect2Time = DW_Lights_CircuitOn(e->count) ? 1 : 0;
        }
'''
# V1.5 has density reset/effect3Time, so use final form.
if old not in g:
    old='''        } else if (!Q_stricmp(e->classname, "dw_destructible_lamp")) {
            e->s.density=0;
            e->s.effect3Time=DW_DLV14_LAMP_MAGIC;
            e->s.effect1Time = e->count2; /* lamp type */
            e->s.effect2Time = DW_Lights_CircuitOn(e->count) ? 1 : 0;
        }
'''
new='''        } else if (!Q_stricmp(e->classname, "dw_destructible_lamp")) {
            e->s.density=0;
            e->s.effect3Time=DW_DLV14_LAMP_MAGIC;
            e->s.effect1Time = e->count2; /* lamp type */
            e->s.effect2Time =
                (e->health > 0 && DW_Lights_CircuitOn(e->count)) ? 1 : 0;
        }
'''
if old not in g: raise SystemExit("game visual update lamp anchor missing")
g=g.replace(old,new,1)

old='''    if (attacker && attacker->client)
        trap_SendServerCommand(attacker-g_entities,
            va("print \\"DarkWolf lamp destroyed (circuit %d)\\n\\"",self->count));
    G_FreeEntity(self);
}
'''
new='''    if (attacker && attacker->client)
        trap_SendServerCommand(attacker-g_entities,
            va("print \\"DarkWolf lamp destroyed (circuit %d)\\n\\"",self->count));

    /*
     * Do NOT free the entity: it now becomes the permanent dark visual marker
     * for the destroyed fixture.  Collision/damage are removed, while the
     * networked lamp marker remains OFF forever.
     */
    self->classname="dw_destroyed_lamp";
    self->health=0;
    self->takedamage=qfalse;
    self->die=NULL;
    self->r.contents=0;
    self->clipmask=0;
    self->s.effect2Time=0;
    trap_LinkEntity(self);
}
'''
if old not in g: raise SystemExit("game proxy die anchor missing")
g=g.replace(old,new,1)

old='''    VectorSet(e->r.mins,-2,-11,-16);
    VectorSet(e->r.maxs,12,11,16);
'''
new='''    /* V1.7: smaller interaction volume matching the reduced RTCW-scale art. */
    VectorSet(e->r.mins,-2,-7,-10);
    VectorSet(e->r.maxs,8,7,10);
'''
if old not in g: raise SystemExit("switch collision anchor missing")
g=g.replace(old,new,1)
ginc.write_text(g)

# ---------------------------------------------------------------------------
# CGAME: draw OFF bulb cover at exact renderer fixture origin; reduce switch size.
# ---------------------------------------------------------------------------
c=cg.read_text()

old='''            memset(&ent,0,sizeof(ent));
            ent.reType=RT_SPRITE;
            VectorCopy(cent->lerpOrigin,ent.origin);
            ent.radius = (s1->effect1Time == 3) ? 12.0f :
'''
new='''            memset(&ent,0,sizeof(ent));
            ent.reType=RT_SPRITE;
            if (DotProduct(s1->origin2,s1->origin2) > 0.01f)
                VectorCopy(s1->origin2,ent.origin);
            else
                VectorCopy(cent->lerpOrigin,ent.origin);
            ent.radius = (s1->effect1Time == 3) ? 11.0f :
'''
if old not in c: raise SystemExit("cgame lamp exact origin anchor missing")
c=c.replace(old,new,1)

old='''                         (s1->effect1Time == 2) ? 10.0f : 10.0f;
'''
new='''                         (s1->effect1Time == 2) ? 9.0f : 8.5f;
'''
if old not in c: raise SystemExit("cgame lamp radius anchor missing")
c=c.replace(old,new,1)

old='''            visualScale = s_dwDlv16SwitchUsesCustom[ti-1][si] ? 1.15f : 0.34f;
'''
new='''            /* V1.7 art pass: compact wall hardware, closer to RTCW prop scale. */
            visualScale = s_dwDlv16SwitchUsesCustom[ti-1][si] ? 0.64f : 0.24f;
'''
if old not in c: raise SystemExit("cgame switch scale anchor missing")
c=c.replace(old,new,1)

cg.write_text(c)
print("DW_DESTRUCTIBLE_LIGHTS_V17_PHYSICAL_OFF_ART_APPLY_PASS")
