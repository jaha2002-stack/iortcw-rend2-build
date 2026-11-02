/* DARKWOLF_PCPS_V3_PICK_VISUAL_20261102
 * Opt-in selection overlay and a guarded source-picker.
 * - The ray is tested against world BSP triangles to identify the visible
 *   object under crosshair. Light-origin angular proximity is *also* ranked.
 * - A visual PREVIEW is never interpreted as final source identity: explicit
 *   dw_ps_confirm is required before any saved shadow editing is possible.
 * - Source identity is rechecked against the CURRENT dlight table at confirm.
 * - HUD is composited after existing postprocess; no FBO, GLSL, slot changes.
 */
#define DWPS3_CANDIDATES 5
#define DWPS3_PI 3.14159265358979323846f
typedef struct {
    int index,slot,sourceClass,fixtureId;
    float radius,angle,rayDistance,hitDistance,score;
    vec3_t origin;
} dwps3Candidate_t;
static dwps3Candidate_t dwps3Candidates[DWPS3_CANDIDATES];
static int dwps3Count=0,dwps3Preview=-1,dwps3Overlay=0;
static int dwps3SelectedId=-1,dwps3SurfaceId=-1;
static qhandle_t dwps3WhiteShader=0,dwps3FontShader=0;

static void DWPS3_OnWorldChanged(void)
{
    dwps3Count=0;
    dwps3Preview=-1;
    dwps3SelectedId=-1;
    dwps3SurfaceId=-1;
    dwps3Overlay=0; /* never persist debug overlays */
}
static void DWPS3_ConfirmedIndex(int index)
{
    dwps3Preview=-1;
    dwps3SelectedId=index;
    dwps3SurfaceId=-1;
}
static void DWPS3_OnCasterPicked(void)
{
    dwps3SurfaceId=dwpsLastSurface;
    dwps3Overlay=1;
}
/* Query BSP hit ONLY when the user asks to pick: never scan BSP per frame. */
static qboolean DWPS3_RaycastBSP(vec3_t hit,int *surfId,float *rayT)
{
    int i,j,found=-1;
    float best=8192.0f;
    if(!tr.world || !tr.world->surfaces)return qfalse;
    for(i=0;i<tr.world->numWorldSurfaces;i++)
    {
        const msurface_t *ms=&tr.world->surfaces[i];
        const srfBspSurface_t *s;
        if(!ms->data || !ms->shader ||
           (*ms->data!=SF_FACE && *ms->data!=SF_GRID &&
            *ms->data!=SF_TRIANGLES))
            continue;
        s=(const srfBspSurface_t*)ms->data;
        if(!s->verts || !s->indexes || s->numIndexes<3 ||
           s->numIndexes>1000000 || s->numVerts<3 || s->numVerts>1000000)
            continue;
        for(j=0;j+2<s->numIndexes;j+=3)
        {
            int a=(int)s->indexes[j],b=(int)s->indexes[j+1],
                c=(int)s->indexes[j+2];
            float t;
            if(a<0 || b<0 || c<0 ||
               a>=s->numVerts || b>=s->numVerts || c>=s->numVerts)continue;
            if(DWPS_RayTriangle(tr.refdef.vieworg,tr.refdef.viewaxis[0],
                s->verts[a].xyz,s->verts[b].xyz,s->verts[c].xyz,&t)
               && t<best){best=t;found=i;}
        }
    }
    if(found<0)return qfalse;
    if(hit)VectorMA(tr.refdef.vieworg,best,tr.refdef.viewaxis[0],hit);
    if(surfId)*surfId=found;
    if(rayT)*rayT=best;
    return qtrue;
}
static void DWPS3_SortCandidates(void)
{
    int i,j;
    for(i=0;i<dwps3Count;i++)
        for(j=i+1;j<dwps3Count;j++)
            if(dwps3Candidates[j].score<dwps3Candidates[i].score)
            {
                dwps3Candidate_t tmp=dwps3Candidates[i];
                dwps3Candidates[i]=dwps3Candidates[j];
                dwps3Candidates[j]=tmp;
            }
}
static int DWPS3_LiveIndex(const dwps3Candidate_t *c)
{
    int i,count=0,result=-1;
    for(i=0;i<tr.refdef.num_dlights;i++)
    {
        const dlight_t *l=&tr.refdef.dlights[i];
        vec3_t d;
        if(l->shadowSourceClass!=c->sourceClass)continue;
        if(c->fixtureId>=0 && l->staticPromoteFixtureId!=c->fixtureId)
            continue;
        VectorSubtract(l->origin,c->origin,d);
        if(DotProduct(d,d)>2.25f)continue;
        if(fabsf(l->radius-c->radius)>32.0f)continue;
        count++;result=i;
    }
    return count==1?result:-1; /* fail closed on a moved/ambiguous source */
}
static void DWPS3_Candidates_f(void)
{
    int i,raySurface=-1;
    float rayT=0.0f;
    vec3_t hit;
    qboolean hasHit;
    DWPS_CheckWorld();
    dwps3Count=0;
    dwps3Preview=-1;
    dwps3SurfaceId=-1;
    dwpsSelected=-1; /* no editing without explicit confirmation */
    dwpsLastSurface=-1;
    if(!tr.world) {ri.Printf(PRINT_ALL,"PCPS V3: load a map first\n");return;}
    hasHit=DWPS3_RaycastBSP(hit,&raySurface,&rayT);
    if(hasHit)
        ri.Printf(PRINT_ALL,
           "PCPS V3: crosshair BSP %d shader %s ray %.1f units\n",
           raySurface,tr.world->surfaces[raySurface].shader->name,rayT);
    else
        ri.Printf(PRINT_ALL,
           "PCPS V3: no world BSP hit under crosshair; ranking source angles only\n");
    for(i=0;i<tr.refdef.num_dlights;i++)
    {
        const dlight_t *l=&tr.refdef.dlights[i];
        dwps3Candidate_t c;
        vec3_t dir;
        float along,perpSq,len2,angle,hitDist=999999.0f,score,limit;
        int j,pos;
        VectorSubtract(l->origin,tr.refdef.vieworg,dir);
        len2=DotProduct(dir,dir);
        along=DotProduct(dir,tr.refdef.viewaxis[0]);
        if(along<=0.01f || len2<0.01f)continue;
        perpSq=len2-along*along;
        if(perpSq<0)perpSq=0;
        angle=atan2f(sqrtf(perpSq),along)*(180.0f/DWPS3_PI);
        if(hasHit)
        {
            vec3_t d;
            VectorSubtract(l->origin,hit,d);
            hitDist=sqrtf(DotProduct(d,d));
        }
        /* Strong preference for the actual BSP surface under the crosshair,
           but only if a source is physically close enough to be plausible.
           A 100+ degree hidden source is never selected automatically. */
        if(angle>58.0f && (!hasHit || hitDist>128.0f))continue;
        limit=hasHit?(hitDist<360.0f?hitDist:360.0f):360.0f;
        score=angle*0.76f+limit*0.115f;
        if(hasHit && hitDist<144.0f)
            score-=10.0f*(1.0f-hitDist/144.0f);
        if(hasHit && along>rayT+192.0f)
            score+=20.0f; /* beyond a world wall, prefer nearer visible */
        Com_Memset(&c,0,sizeof(c));
        c.index=i;c.slot=tr.refdef.dlightShadowSlot[i];
        c.sourceClass=l->shadowSourceClass;
        c.fixtureId=l->staticPromoteFixtureId;
        c.radius=l->radius;
        c.angle=angle;
        c.rayDistance=sqrtf(perpSq);
        c.hitDistance=hitDist;
        c.score=score;
        VectorCopy(l->origin,c.origin);
        pos=dwps3Count;
        if(pos<DWPS3_CANDIDATES)dwps3Count++;
        else
        {
            if(score>=dwps3Candidates[dwps3Count-1].score)continue;
            pos=dwps3Count-1;
        }
        dwps3Candidates[pos]=c;
        DWPS3_SortCandidates();
        /* Keep only top 5 in a bounded array; no dynamic allocation. */
        for(j=1;j<dwps3Count;j++)
            if(dwps3Candidates[j].score<dwps3Candidates[j-1].score)
                ri.Printf(PRINT_WARNING,"PCPS V3: internal ranking order issue\n");
    }
    if(!dwps3Count)
    {
        dwps3Overlay=0;
        ri.Printf(PRINT_ALL,"PCPS V3: no visible candidates. Face the lamp or use dw_ps_lights / dw_ps_select N\n");
        return;
    }
    dwps3Preview=0;
    dwps3Overlay=1;
    ri.Printf(PRINT_ALL,
       "PCPS V3: %d ranked candidates (BSP proximity + ray angle). PREVIEW ONLY; no light disabled.\n",
       dwps3Count);
    for(i=0;i<dwps3Count;i++)
    {
        const dwps3Candidate_t *c=&dwps3Candidates[i];
        ri.Printf(PRINT_ALL,
           " %d) light %d  (%.1f %.1f %.1f)  angle %.1f  hitDist %s  slot %d  score %.2f\n",
           i+1,c->index,c->origin[0],c->origin[1],c->origin[2],
           c->angle,hasHit?"see numeric in next line":"n/a",c->slot,c->score);
        if(hasHit)ri.Printf(PRINT_ALL,"    BSP-hit to source distance %.1f units\n",c->hitDistance);
    }
    if(dwps3Count>1 &&
       dwps3Candidates[1].score-dwps3Candidates[0].score<7.5f)
        ri.Printf(PRINT_WARNING,
          "PCPS V3: AMBIGUOUS light: compare on-screen labels; use dw_ps_next / dw_ps_confirm.\n");
    ri.Printf(PRINT_ALL,
      "PCPS V3: selected PREVIEW light %d; /dw_ps_confirm [rank 1..%d] before light_off/caster_off\n",
      dwps3Candidates[0].index,dwps3Count);
}
static void DWPS3_PickLight_f(void)
{
    DWPS3_Candidates_f();
}
static void DWPS3_Next_f(void)
{
    if(dwps3Count<=0){ri.Printf(PRINT_ALL,"PCPS V3: aim and run dw_ps_picklight first\n");return;}
    dwps3Preview=(dwps3Preview+1)%dwps3Count;
    dwps3Overlay=1;
    ri.Printf(PRINT_ALL,"PCPS V3: preview rank %d = light %d (NOT YET CONFIRMED)\n",
       dwps3Preview+1,dwps3Candidates[dwps3Preview].index);
}
static void DWPS3_Prev_f(void)
{
    if(dwps3Count<=0){ri.Printf(PRINT_ALL,"PCPS V3: aim and run dw_ps_picklight first\n");return;}
    dwps3Preview=(dwps3Preview+dwps3Count-1)%dwps3Count;
    dwps3Overlay=1;
    ri.Printf(PRINT_ALL,"PCPS V3: preview rank %d = light %d (NOT YET CONFIRMED)\n",
       dwps3Preview+1,dwps3Candidates[dwps3Preview].index);
}
static void DWPS3_Confirm_f(void)
{
    int rank,index;
    if(dwps3Count<=0 || dwps3Preview<0)
    {
        ri.Printf(PRINT_ALL,"PCPS V3: no preview. Use dw_ps_picklight, then dw_ps_confirm\n");
        return;
    }
    rank=dwps3Preview;
    if(ri.Cmd_Argc()==2)
    {
        int n=atoi(ri.Cmd_Argv(1));
        if(n<1 || n>dwps3Count)
        {
            ri.Printf(PRINT_ALL,"PCPS V3: valid rank 1..%d\n",dwps3Count);
            return;
        }
        rank=n-1;
    }
    index=DWPS3_LiveIndex(&dwps3Candidates[rank]);
    if(index<0)
    {
        ri.Printf(PRINT_WARNING,
          "PCPS V3: source moved or ambiguous; NOT selected. Re-aim and pick again.\n");
        dwpsSelected=-1;
        return;
    }
    if(DWPS_SelectLightIndex(index)<0)return;
    dwps3Overlay=1;
    ri.Printf(PRINT_ALL,
      "PCPS V3: CONFIRMED light %d at (%.1f %.1f %.1f), slot %d. Shadow edits now enabled.\n",
      index,tr.refdef.dlights[index].origin[0],
      tr.refdef.dlights[index].origin[1],
      tr.refdef.dlights[index].origin[2],
      tr.refdef.dlightShadowSlot[index]);
}
static void DWPS3_Overlay_f(void)
{
    if(ri.Cmd_Argc()==2)
    {
        int n=atoi(ri.Cmd_Argv(1));
        if(n!=0 && n!=1)
        {
            ri.Printf(PRINT_ALL,"Usage: dw_ps_overlay 0|1\n");return;
        }
        dwps3Overlay=n;
    }
    else dwps3Overlay=!dwps3Overlay;
    ri.Printf(PRINT_ALL,"PCPS V3: visual overlay %s (session-only)\n",
       dwps3Overlay?"ON":"OFF");
}
/* Screen overlay uses only existing UI stretchpic commands, queued after
 * postprocessing. No GL state, shadow mask, FBO or shader source edits.
 */
static qboolean DWPS3_Project(const refdef_t *fd,const vec3_t xyz,float *x,float *y)
{
    vec3_t d;
    float z,viewRight,viewUp,tanX,tanY;
    VectorSubtract(xyz,fd->vieworg,d);
    z=DotProduct(d,fd->viewaxis[0]);
    if(z<1.0f)return qfalse;
    viewRight=DotProduct(d,fd->viewaxis[1]);
    viewUp=DotProduct(d,fd->viewaxis[2]);
    tanX=tanf(fd->fov_x*DWPS3_PI/360.0f);
    tanY=tanf(fd->fov_y*DWPS3_PI/360.0f);
    if(tanX<=0.001f || tanY<=0.001f)return qfalse;
    *x=fd->x+fd->width*0.5f -
       (viewRight/z)*(fd->width*0.5f/tanX);
    *y=fd->y+fd->height*0.5f -
       (viewUp/z)*(fd->height*0.5f/tanY);
    return (*x>=fd->x-20 && *x<=fd->x+fd->width+20 &&
            *y>=fd->y-20 && *y<=fd->y+fd->height+20)?qtrue:qfalse;
}
static void DWPS3_Rect(float x,float y,float w,float h,const float *color)
{
    if(!dwps3WhiteShader)return;
    RE_SetColor(color);
    RE_StretchPic(x,y,w,h,0,0,1,1,dwps3WhiteShader);
}
static void DWPS3_Text(float x,float y,const char *value,const float *color)
{
    int n=0;
    if(!dwps3FontShader)return;
    RE_SetColor(color);
    for(;*value && n<62;value++,n++)
    {
        unsigned char c=(unsigned char)*value;
        float s,t;
        if(c==' ')continue;
        if(c<32 || c>126)c='?';
        s=(float)(c&15)/16.0f;
        t=(float)(c>>4)/16.0f;
        RE_StretchPic(x+n*9.0f,y,9.0f,12.0f,
           s,t,s+1.0f/16.0f,t+1.0f/16.0f,dwps3FontShader);
    }
}
static void DWPS3_DottedLine(float x1,float y1,float x2,float y2,const float *c)
{
    int i,steps;
    float dx=x2-x1,dy=y2-y1,len=sqrtf(dx*dx+dy*dy);
    steps=(int)(len/12.0f);
    if(steps<1)steps=1;
    if(steps>8)steps=8;
    for(i=0;i<=steps;i++)
    {
        float t=(float)i/(float)steps;
        DWPS3_Rect(x1+dx*t-1.25f,y1+dy*t-1.25f,2.5f,2.5f,c);
    }
}
static void DWPS3_DrawCasterWire(const refdef_t *fd,const float *color)
{
    const msurface_t *m;
    const srfBspSurface_t *s;
    int k,triangles,step,i;
    if(dwps3SurfaceId<0 || !tr.world ||
       dwps3SurfaceId>=tr.world->numWorldSurfaces)return;
    m=&tr.world->surfaces[dwps3SurfaceId];
    if(!m->data || (*m->data!=SF_FACE && *m->data!=SF_GRID &&
       *m->data!=SF_TRIANGLES))return;
    s=(const srfBspSurface_t*)m->data;
    if(!s->verts || !s->indexes || s->numIndexes<3)return;
    triangles=s->numIndexes/3;
    if(triangles<=0)return;
    step=(triangles+11)/12; /* max 12 sample triangles per visible frame */
    for(k=0;k<triangles;k+=step)
    {
        int ids[3],e;
        float x[3],y[3];
        qboolean valid=qtrue;
        for(i=0;i<3;i++)
        {
            ids[i]=s->indexes[k*3+i];
            if(ids[i]<0 || ids[i]>=s->numVerts){valid=qfalse;break;}
        }
        if(!valid)continue;
        for(i=0;i<3;i++)
            if(!DWPS3_Project(fd,s->verts[ids[i]].xyz,&x[i],&y[i]))
                {valid=qfalse;break;}
        if(!valid)continue;
        for(e=0;e<3;e++)
            DWPS3_DottedLine(x[e],y[e],x[(e+1)%3],y[(e+1)%3],color);
    }
}
void DWPS3_DrawOverlay(const refdef_t *fd)
{
    static const float cyan[4]={0.20f,0.94f,1.0f,0.86f};
    static const float amber[4]={1.0f,0.72f,0.12f,0.98f};
    static const float green[4]={0.20f,1.0f,0.36f,0.98f};
    static const float dark[4]={0.04f,0.07f,0.10f,0.67f};
    int i;
    float top;
    char label[96];
    if(!dwps3Overlay || !fd || !tr.registered || !tr.world ||
       fd->rdflags&(RDF_NOWORLDMODEL|RDF_SKYBOXPORTAL))return;
    if(!dwps3WhiteShader)dwps3WhiteShader=RE_RegisterShaderNoMip("white");
    if(!dwps3FontShader)dwps3FontShader=RE_RegisterShaderNoMip("gfx/2d/hudchars");
    if(!dwps3WhiteShader || !dwps3FontShader)return;
    top=fd->y+18.0f;
    DWPS3_Rect(fd->x+11.0f,top-7.0f,284.0f,28.0f+
        (dwps3Count>0?dwps3Count:1)*15.0f,dark);
    if(dwpsSelected>=0 && dwpsSelected<dwpsNumRules)
    {
        const dwpsRule_t *r=&dwpsRules[dwpsSelected];
        snprintf(label,sizeof(label),"PCPS SELECTED LIGHT %d",dwps3SelectedId);
        DWPS3_Text(fd->x+17.0f,top,label,green);
        for(i=0;i<tr.refdef.num_dlights;i++)
        {
            const dlight_t *l=&tr.refdef.dlights[i];
            if(DWPS_SameSource(r,l))
            {
                float sx,sy;
                if(DWPS3_Project(fd,l->origin,&sx,&sy))
                {
                    char num[24];
                    snprintf(num,sizeof(num),"LIGHT %d",i);
                    DWPS3_Rect(sx-5,sy-5,10,10,green);
                    DWPS3_Text(sx+8,sy-10,num,green);
                }
                break;
            }
        }
    }
    else DWPS3_Text(fd->x+17,top,
         dwps3Count>0?"PCPS PICK PREVIEW / CONFIRM":"PCPS NO ACTIVE LIGHT",amber);
    for(i=0;i<dwps3Count;i++)
    {
        const dwps3Candidate_t *c=&dwps3Candidates[i];
        int live=DWPS3_LiveIndex(c);
        float sx,sy;
        const float *color=i==dwps3Preview?amber:cyan;
        snprintf(label,sizeof(label),"%d: LIGHT %d SLOT %d %s",
           i+1,c->index,c->slot,i==dwps3Preview?"TARGET":"");
        DWPS3_Text(fd->x+17,top+17+i*15.0f,label,color);
        if(live>=0 && DWPS3_Project(fd,c->origin,&sx,&sy))
        {
            char name[24];
            snprintf(name,sizeof(name),"%d",live);
            DWPS3_Rect(sx-4,sy-4,8,8,color);
            DWPS3_Text(sx+7,sy-11,name,color);
        }
    }
    if(dwps3SurfaceId>=0 && tr.world &&
       dwps3SurfaceId<tr.world->numWorldSurfaces)
    {
        DWPS3_DrawCasterWire(fd,cyan);
        snprintf(label,sizeof(label),"BSP %d SELECTED",dwps3SurfaceId);
        DWPS3_Text(fd->x+17,top+17+dwps3Count*15.0f,label,cyan);
    }
    RE_SetColor(NULL);
}
