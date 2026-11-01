/* DARKWOLF_PCPS_RUNTIME_V1 -- opt-in, map-local, reversible controls.
 * A light's shadow cubemap slot is released by filtering pendingLightsMask
 * BEFORE the production source selector (not by hiding the shadow afterward).
 * World caster omissions affect ordinary point shadow depth views ONLY.
 * No global material blacklists or per-frame heap allocations.
 */
#define DWPS_MAX_RULES 24
#define DWPS_MAX_CASTERS 32
typedef struct {
    int id;
    surfaceType_t *surface;
    char material[MAX_QPATH];
    vec3_t bounds[2];
} dwpsCaster_t;
typedef struct {
    vec3_t origin;
    float radius;
    int sourceClass;
    int fixtureId;
    qboolean shadowOff;
    int numCasters;
    dwpsCaster_t casters[DWPS_MAX_CASTERS];
} dwpsRule_t;
static dwpsRule_t dwpsRules[DWPS_MAX_RULES];
static int dwpsNumRules=0,dwpsSelected=-1,dwpsLastSurface=-1;
static const world_t *dwpsWorld=NULL;
static const msurface_t *dwpsWorldSurfaces=NULL;
static char dwpsMap[MAX_QPATH]="";

static void DWPS_CheckWorld(void)
{
    if (!tr.world || !tr.world->surfaces) {
        dwpsWorld=NULL;
        dwpsWorldSurfaces=NULL;
        dwpsMap[0]=0;
        dwpsNumRules=0;
        dwpsSelected=-1;
        dwpsLastSurface=-1;
        return;
    }
    if (dwpsWorld==tr.world && dwpsWorldSurfaces==tr.world->surfaces &&
        !Q_stricmp(dwpsMap,tr.world->name)) return;
    dwpsWorld=tr.world;
    dwpsWorldSurfaces=tr.world->surfaces;
    Q_strncpyz(dwpsMap,tr.world->name,sizeof(dwpsMap));
    dwpsNumRules=0;
    dwpsSelected=-1;
    dwpsLastSurface=-1;
}
static qboolean DWPS_SameSource(const dwpsRule_t *r,const dlight_t *l)
{
    vec3_t delta;
    VectorSubtract(r->origin,l->origin,delta);
    if (DotProduct(delta,delta)>2.25f) return qfalse;
    if (r->sourceClass!=l->shadowSourceClass) return qfalse;
    if(r->fixtureId>=0 && l->staticPromoteFixtureId>=0)
        return (r->fixtureId==l->staticPromoteFixtureId) ? qtrue : qfalse;
    if (fabsf(r->radius-l->radius)>32.0f) return qfalse;
    return qtrue;
}
static int DWPS_FindRuleForLight(const dlight_t *light)
{
    int i;
    for(i=0;i<dwpsNumRules;i++)
        if(DWPS_SameSource(&dwpsRules[i],light))return i;
    return -1;
}
static int DWPS_SelectLightIndex(int index)
{
    int r;
    dlight_t *l;
    DWPS_CheckWorld();
    if(!tr.world || index<0 || index>=tr.refdef.num_dlights) {
        ri.Printf(PRINT_ALL,"PCPS: no valid current light %d\n",index);
        return -1;
    }
    l=&tr.refdef.dlights[index];
    r=DWPS_FindRuleForLight(l);
    if(r<0) {
        if(dwpsNumRules>=DWPS_MAX_RULES) {
            ri.Printf(PRINT_ALL,"PCPS: rule limit reached (%d)\n",DWPS_MAX_RULES);
            return -1;
        }
        r=dwpsNumRules++;
        Com_Memset(&dwpsRules[r],0,sizeof(dwpsRules[r]));
        VectorCopy(l->origin,dwpsRules[r].origin);
        dwpsRules[r].radius=l->radius;
        dwpsRules[r].sourceClass=l->shadowSourceClass;
        dwpsRules[r].fixtureId=l->staticPromoteFixtureId;
    }
    dwpsSelected=r;
    dwpsLastSurface=-1;
    ri.Printf(PRINT_ALL,"PCPS: selected light %d, map %s, origin %.2f %.2f %.2f, radius %.1f\n",
       index,dwpsMap,l->origin[0],l->origin[1],l->origin[2],l->radius);
    return r;
}
static void DWPS_Help_f(void)
{
    ri.Printf(PRINT_ALL,
      "DarkWolf PCPS V1 (session-only; all defaults unchanged)\n"
      "dw_ps_lights       list available dynamic lights\n"
      "dw_ps_picklight    select light nearest crosshair\n"
      "dw_ps_select N     select light index from list\n"
      "dw_ps_light_off    disable selected light's point shadow AND free its slot\n"
      "dw_ps_light_on     restore selected light's point shadow\n"
      "dw_ps_pickcaster  select BSP triangle under crosshair\n"
      "dw_ps_caster_off  exclude selected BSP triangle surface from selected light\n"
      "dw_ps_caster_on   restore selected BSP surface\n"
      "dw_ps_info        show selected light/caster state\n"
      "dw_ps_reset       clear ALL PCPS rules for current map\n"
      "Light itself and other lighting systems remain enabled.\n"
      "A saved index is not portable to another BSP.\n");
}
static void DWPS_Lights_f(void)
{
    int i;
    DWPS_CheckWorld();
    if(!tr.world) {ri.Printf(PRINT_ALL,"PCPS: load a map first\n");return;}
    ri.Printf(PRINT_ALL,"PCPS: %d lights; dlight indices are temporary\n",tr.refdef.num_dlights);
    for(i=0;i<tr.refdef.num_dlights;i++) {
        const dlight_t *l=&tr.refdef.dlights[i];
        int rule=DWPS_FindRuleForLight(l);
        ri.Printf(PRINT_ALL,
            " %2d: (%.1f %.1f %.1f) radius %.1f class %d selectedSlot %d%s\n",
            i,l->origin[0],l->origin[1],l->origin[2],l->radius,
            l->shadowSourceClass,tr.refdef.dlightShadowSlot[i],
            rule>=0&&dwpsRules[rule].shadowOff?" [PCPS SHADOW OFF]":"");
    }
}
static void DWPS_Select_f(void)
{
    int n;
    if(ri.Cmd_Argc()!=2) {ri.Printf(PRINT_ALL,"Usage: dw_ps_select INDEX\n");return;}
    n=atoi(ri.Cmd_Argv(1));
    DWPS_SelectLightIndex(n);
}
static void DWPS_PickLight_f(void)
{
    int i,best=-1;
    float bestScore=-1.0f;
    DWPS_CheckWorld();
    if(!tr.world) {ri.Printf(PRINT_ALL,"PCPS: load a map first\n");return;}
    for(i=0;i<tr.refdef.num_dlights;i++) {
        vec3_t d;
        float along,distSq,score;
        const dlight_t *l=&tr.refdef.dlights[i];
        VectorSubtract(l->origin,tr.refdef.vieworg,d);
        along=DotProduct(d,tr.refdef.viewaxis[0]);
        distSq=DotProduct(d,d);
        if(along<=0.0f || distSq<0.001f)continue;
        score=along*along/distSq; /* square of cos(angle) */
        if(score<0.94f)continue;
        score-=distSq*0.00000001f; /* tie: nearer */
        if(score>bestScore){bestScore=score;best=i;}
    }
    if(best<0) {
        ri.Printf(PRINT_ALL,"PCPS: no light near crosshair; try dw_ps_lights\n");
        return;
    }
    DWPS_SelectLightIndex(best);
}
static qboolean DWPS_RayTriangle(const vec3_t orig,const vec3_t dir,
   const vec3_t v0,const vec3_t v1,const vec3_t v2,float *t)
{
    vec3_t edge1,edge2,p,s,q;
    float det,inv,u,v,dist;
    VectorSubtract(v1,v0,edge1);
    VectorSubtract(v2,v0,edge2);
    CrossProduct(dir,edge2,p);
    det=DotProduct(edge1,p);
    if(fabsf(det)<1.0e-6f)return qfalse;
    inv=1.0f/det;
    VectorSubtract(orig,v0,s);
    u=inv*DotProduct(s,p);
    if(u<0.0f || u>1.0f)return qfalse;
    CrossProduct(s,edge1,q);
    v=inv*DotProduct(dir,q);
    if(v<0.0f || u+v>1.0f)return qfalse;
    dist=inv*DotProduct(edge2,q);
    if(dist<0.01f || dist>8192.0f)return qfalse;
    *t=dist;
    return qtrue;
}
static void DWPS_PickCaster_f(void)
{
    int i,j,best=-1;
    float nearest=8192.0f;
    DWPS_CheckWorld();
    if(dwpsSelected<0) {
        ri.Printf(PRINT_ALL,"PCPS: select a light first\n");
        return;
    }
    for(i=0;i<tr.world->numWorldSurfaces;i++) {
        const msurface_t *ms=&tr.world->surfaces[i];
        const srfBspSurface_t *s;
        if(!ms->data || !ms->shader)continue;
        if(*ms->data!=SF_FACE && *ms->data!=SF_GRID &&
           *ms->data!=SF_TRIANGLES)continue;
        s=(const srfBspSurface_t*)ms->data;
        if(!s->verts || !s->indexes || s->numIndexes<3 ||
           s->numIndexes>1000000 || s->numVerts<3 || s->numVerts>1000000)
            continue;
        for(j=0;j+2<s->numIndexes;j+=3) {
            int a=(int)s->indexes[j],b=(int)s->indexes[j+1],c=(int)s->indexes[j+2];
            float t;
            if(a<0 || b<0 || c<0 || a>=s->numVerts || b>=s->numVerts || c>=s->numVerts)
                continue;
            if(DWPS_RayTriangle(tr.refdef.vieworg,tr.refdef.viewaxis[0],
               s->verts[a].xyz,s->verts[b].xyz,s->verts[c].xyz,&t) && t<nearest)
            {
                nearest=t;
                best=i;
            }
        }
    }
    if(best<0) {
        ri.Printf(PRINT_ALL,"PCPS: no world BSP triangle under crosshair\n");
        return;
    }
    dwpsLastSurface=best;
    ri.Printf(PRINT_ALL,"PCPS: BSP surface %d, material %s, ray distance %.2f\n",
        best,tr.world->surfaces[best].shader->name,nearest);
}
static void DWPS_LightOff_f(void)
{
    DWPS_CheckWorld();
    if(dwpsSelected<0){ri.Printf(PRINT_ALL,"PCPS: select a light first\n");return;}
    dwpsRules[dwpsSelected].shadowOff=qtrue;
    ri.Printf(PRINT_ALL,"PCPS: source shadow OFF; removed from shadow-slot candidates (light preserved)\n");
}
static void DWPS_LightOn_f(void)
{
    DWPS_CheckWorld();
    if(dwpsSelected<0){ri.Printf(PRINT_ALL,"PCPS: select a light first\n");return;}
    dwpsRules[dwpsSelected].shadowOff=qfalse;
    ri.Printf(PRINT_ALL,"PCPS: source shadow ON; eligible for existing shadow slots\n");
}
static qboolean DWPS_CasterValid(const dwpsCaster_t *c)
{
    const msurface_t *m;
    int k,j;
    if(!tr.world || c->id<0 || c->id>=tr.world->numWorldSurfaces)return qfalse;
    m=&tr.world->surfaces[c->id];
    if(!m->data || m->data!=c->surface || !m->shader ||
       Q_stricmp(c->material,m->shader->name))return qfalse;
    if(!(m->cullinfo.type & CULLINFO_BOX))return qfalse;
    for(k=0;k<2;k++)for(j=0;j<3;j++)
       if(fabsf(c->bounds[k][j]-m->cullinfo.bounds[k][j])>0.25f)
           return qfalse;
    return qtrue;
}
static void DWPS_CasterOff_f(void)
{
    dwpsRule_t *r;
    dwpsCaster_t *c;
    const msurface_t *m;
    int i;
    DWPS_CheckWorld();
    if(dwpsSelected<0 || dwpsLastSurface<0) {
        ri.Printf(PRINT_ALL,"PCPS: select light then dw_ps_pickcaster first\n");return;
    }
    r=&dwpsRules[dwpsSelected];
    for(i=0;i<r->numCasters;i++)if(r->casters[i].id==dwpsLastSurface) {
        ri.Printf(PRINT_ALL,"PCPS: caster already excluded\n");return;
    }
    if(r->numCasters>=DWPS_MAX_CASTERS){ri.Printf(PRINT_ALL,"PCPS: caster limit reached\n");return;}
    m=&tr.world->surfaces[dwpsLastSurface];
    if(!m->shader || !m->data || !(m->cullinfo.type&CULLINFO_BOX)) {
        ri.Printf(PRINT_ALL,"PCPS: BSP surface has no safe geometry fingerprint\n");return;
    }
    c=&r->casters[r->numCasters];
    Com_Memset(c,0,sizeof(*c));
    c->id=dwpsLastSurface;
    c->surface=m->data;
    Q_strncpyz(c->material,m->shader->name,sizeof(c->material));
    VectorCopy(m->cullinfo.bounds[0],c->bounds[0]);
    VectorCopy(m->cullinfo.bounds[1],c->bounds[1]);
    if(!DWPS_CasterValid(c)){ri.Printf(PRINT_ALL,"PCPS: fingerprint validation failed\n");return;}
    r->numCasters++;
    ri.Printf(PRINT_ALL,"PCPS: excluded BSP surface %d for SELECTED light only\n",c->id);
}
static void DWPS_CasterOn_f(void)
{
    int i;
    dwpsRule_t *r;
    DWPS_CheckWorld();
    if(dwpsSelected<0 || dwpsLastSurface<0)return;
    r=&dwpsRules[dwpsSelected];
    for(i=0;i<r->numCasters;i++)if(r->casters[i].id==dwpsLastSurface) {
        int restored=r->casters[i].id;
        r->casters[i]=r->casters[r->numCasters-1];
        r->numCasters--;
        ri.Printf(PRINT_ALL,"PCPS: restored BSP caster %d\n",restored);
        return;
    }
    ri.Printf(PRINT_ALL,"PCPS: selected caster already enabled\n");
}
static void DWPS_Info_f(void)
{
    const dwpsRule_t *r;
    int i;
    DWPS_CheckWorld();
    if(dwpsSelected<0){ri.Printf(PRINT_ALL,"PCPS: no selected source\n");return;}
    r=&dwpsRules[dwpsSelected];
    ri.Printf(PRINT_ALL,"PCPS: %s source (%.2f %.2f %.2f), shadow %s, casters removed %d\n",
        dwpsMap,r->origin[0],r->origin[1],r->origin[2],
        r->shadowOff?"OFF / NOT ELIGIBLE FOR SLOT":"ON",r->numCasters);
    for(i=0;i<r->numCasters;i++)
        ri.Printf(PRINT_ALL,"  BSP %d: %s\n",r->casters[i].id,r->casters[i].material);
}
static void DWPS_Reset_f(void)
{
    DWPS_CheckWorld();
    dwpsSelected=-1;
    dwpsLastSurface=-1;
    dwpsNumRules=0;
    Com_Memset(dwpsRules,0,sizeof(dwpsRules));
    ri.Printf(PRINT_ALL,"PCPS: ALL overrides cleared; original point shadows restored\n");
}
void DWPS_Register(void)
{
    ri.Cmd_AddCommand("dw_ps_help",DWPS_Help_f);
    ri.Cmd_AddCommand("dw_ps_lights",DWPS_Lights_f);
    ri.Cmd_AddCommand("dw_ps_picklight",DWPS_PickLight_f);
    ri.Cmd_AddCommand("dw_ps_select",DWPS_Select_f);
    ri.Cmd_AddCommand("dw_ps_pickcaster",DWPS_PickCaster_f);
    ri.Cmd_AddCommand("dw_ps_light_off",DWPS_LightOff_f);
    ri.Cmd_AddCommand("dw_ps_light_on",DWPS_LightOn_f);
    ri.Cmd_AddCommand("dw_ps_caster_off",DWPS_CasterOff_f);
    ri.Cmd_AddCommand("dw_ps_caster_on",DWPS_CasterOn_f);
    ri.Cmd_AddCommand("dw_ps_info",DWPS_Info_f);
    ri.Cmd_AddCommand("dw_ps_reset",DWPS_Reset_f);
}
void DWPS_Unregister(void)
{
    ri.Cmd_RemoveCommand("dw_ps_help");
    ri.Cmd_RemoveCommand("dw_ps_lights");
    ri.Cmd_RemoveCommand("dw_ps_picklight");
    ri.Cmd_RemoveCommand("dw_ps_select");
    ri.Cmd_RemoveCommand("dw_ps_pickcaster");
    ri.Cmd_RemoveCommand("dw_ps_light_off");
    ri.Cmd_RemoveCommand("dw_ps_light_on");
    ri.Cmd_RemoveCommand("dw_ps_caster_off");
    ri.Cmd_RemoveCommand("dw_ps_caster_on");
    ri.Cmd_RemoveCommand("dw_ps_info");
    ri.Cmd_RemoveCommand("dw_ps_reset");
    DWPS_Reset_f();
}
unsigned int DWPS_ApplyPendingMask(unsigned int mask)
{
    int i,j,k;
    DWPS_CheckWorld();
    if(!tr.world || !dwpsNumRules)return mask;
    for(j=0;j<dwpsNumRules;j++) {
        const dwpsRule_t *r=&dwpsRules[j];
        int matches=0;
        if(!r->shadowOff)continue;
        for(i=0;i<tr.refdef.num_dlights && i<32;i++) {
            if(DWPS_SameSource(r,&tr.refdef.dlights[i]))matches++;
        }
        /* A named StaticPromote fixture can own several dlights. Explicitly
         * release the entire fixture's shadow residency; keep direct light.
         * For non-fixture sources, refuse ambiguous geometric matches. */
        if(matches==0 || (r->fixtureId<0 && matches!=1))continue;
        for(k=0;k<tr.refdef.num_dlights && k<32;k++) {
            const dlight_t *l=&tr.refdef.dlights[k];
            if((r->fixtureId>=0 && l->staticPromoteFixtureId==r->fixtureId &&
                l->shadowSourceClass==r->sourceClass)
               ||(r->fixtureId<0 && DWPS_SameSource(r,l)))
                mask&=~(1u<<k);
        }
    }
    return mask;
}
qboolean DWPS_ShouldSkipCaster(const drawSurf_t *ds)
{
    int i,j,entityNum;
    if(dwpsWorld!=tr.world || !tr.world || dwpsWorldSurfaces!=tr.world->surfaces ||
       !dwpsNumRules || !ds || !ds->surface)return qfalse;
    if((backEnd.viewParms.flags & (VPF_SHADOWMAP|VPF_DEPTHSHADOW)) !=
       (VPF_SHADOWMAP|VPF_DEPTHSHADOW))return qfalse;
    if(backEnd.viewParms.flags &
       (VPF_DLIGHT_WORLD_OCCLUSION|VPF_FIREVOL_SYNTHETIC_SHADOW))return qfalse;
    entityNum=(ds->sort>>QSORT_REFENTITYNUM_SHIFT)&REFENTITYNUM_MASK;
    if(entityNum!=REFENTITYNUM_WORLD)return qfalse;
    for(i=0;i<dwpsNumRules;i++) {
        vec3_t d;
        const dwpsRule_t *r=&dwpsRules[i];
        VectorSubtract(r->origin,backEnd.viewParms.or.origin,d);
        int currentMatches=0,k;
        if(DotProduct(d,d)>2.25f || r->shadowOff)continue;
        for(k=0;k<tr.refdef.num_dlights;k++)
            if(DWPS_SameSource(r,&tr.refdef.dlights[k]))currentMatches++;
        if(r->fixtureId<0 && currentMatches!=1)continue;
        if(r->fixtureId>=0 && currentMatches<1)continue;
        for(j=0;j<r->numCasters;j++) {
            const dwpsCaster_t *c=&r->casters[j];
            if(c->surface==ds->surface && DWPS_CasterValid(c))return qtrue;
        }
    }
    return qfalse;
}
