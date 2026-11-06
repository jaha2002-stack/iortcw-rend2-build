from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()

anchor='#define ELSS_MANUAL_BASE 1\n'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'#define ELSS_SEED_GROUP (-1)\n#define ELSS_SEED_EXACT (-2)\n')

marker='''static unsigned int R_ELSS_PolicyKey(const elssProfile_t *p,const elssFixture_t *out)\n'''
assert s.count(marker)==1
helper=r'''static qboolean R_ELSS_RayBounds(const vec3_t lo,const vec3_t hi,float maxDistance,float *hit)
{
    float tmin=0.0f,tmax=maxDistance;int k;
    for(k=0;k<3;++k){
        float mn=lo[k]-2.0f,mx=hi[k]+2.0f,o=s_iflcViewOrigin[k],d=s_iflcViewForward[k],a,b;
        if(fabsf(d)<0.00001f){if(o<mn||o>mx)return qfalse;continue;}
        a=(mn-o)/d;b=(mx-o)/d;if(a>b){float q=a;a=b;b=q;}
        if(a>tmin)tmin=a;if(b<tmax)tmax=b;if(tmin>tmax)return qfalse;
    }
    if(tmax<0.0f||tmin>maxDistance)return qfalse;if(tmin<0.0f)tmin=0.0f;if(hit)*hit=tmin;return qtrue;
}
/* If the precise first hit is protected architecture, search only for a
 * strictly safe compact BSP surface of the already-selected physical lamp
 * intersecting the same crosshair ray. Architecture rules are never relaxed. */
static qboolean R_ELSS_PickSafeSurfaceNearRay(const elssOwner_t *o,int blockedSurface,float blockedHit,int *surfaceOut,float *hitOut)
{
    int i,best=-1;float bestScore=1e30f,bestHit=0,maxDistance=MIN(512.0f,blockedHit+24.0f);
    if(surfaceOut)*surfaceOut=-1;if(hitOut)*hitOut=0;if(!o||!tr.world)return qfalse;
    for(i=0;i<tr.world->numWorldSurfaces;++i){
        vec3_t lo,hi;float h,owner2,score;
        if(i==blockedSurface||!R_ELSS_ManualSurfaceSafe(o,i)||!R_IFLC_SelfSurfaceBoundsAny(i,lo,hi))continue;
        owner2=R_IFLC_SelfBoundsDistanceSquared(o->origin,lo,hi);if(owner2>128.0f*128.0f)continue;
        if(!R_ELSS_RayBounds(lo,hi,maxDistance,&h)||h>blockedHit+16.0f)continue;
        score=h+sqrtf(owner2)*0.02f;
        if(score<bestScore){bestScore=score;bestHit=h;best=i;}
    }
    if(best<0)return qfalse;if(surfaceOut)*surfaceOut=best;if(hitOut)*hitOut=bestHit;return qtrue;
}

'''
s=s.replace(marker,helper+marker)

old='''    for(i=0;i<p->seedCount;++i){
        if(p->seedTris[i]>=0){unsigned char omit[ELSS_MAX_TRIM_TRIANGLES];int triCount=0,removed=0;if(!R_ELSS_ComponentMask(o,p->seeds[i],p->seedTris[i],omit,&triCount,&removed)||!R_ELSS_AddTrim(out,p->seeds[i],triCount,omit,removed)){memset(out,0,sizeof(*out));out->built=qtrue;return qfalse;}}
        else wholeSeeds[wholeCount++]=p->seeds[i];
    }
'''
new='''    for(i=0;i<p->seedCount;++i){
        if(p->seedTris[i]>=0){unsigned char omit[ELSS_MAX_TRIM_TRIANGLES];int triCount=0,removed=0;if(!R_ELSS_ComponentMask(o,p->seeds[i],p->seedTris[i],omit,&triCount,&removed)||!R_ELSS_AddTrim(out,p->seeds[i],triCount,omit,removed)){memset(out,0,sizeof(*out));out->built=qtrue;return qfalse;}}
        else if(p->seedTris[i]==ELSS_SEED_EXACT){
            const srfBspSurface_t *b;int q,duplicate=0;
            if(!R_ELSS_ManualSurfaceSafe(o,p->seeds[i])){memset(out,0,sizeof(*out));out->built=qtrue;return qfalse;}
            for(q=0;q<out->count;++q)if(out->surfaces[q]==p->seeds[i]){duplicate=1;break;}
            if(!duplicate){if(out->count>=ELSS_MAX_SURFACES){memset(out,0,sizeof(*out));out->built=qtrue;return qfalse;}out->surfaces[out->count++]=p->seeds[i];b=R_IFLC_FixtureMesh(p->seeds[i]);if(b&&b->numIndexes>=3)out->removedTriangles+=b->numIndexes/3;}
        }
        else wholeSeeds[wholeCount++]=p->seeds[i];
    }
'''
assert s.count(old)==1
s=s.replace(old,new)

start=s.index('void R_ELSS_SelfPick_f(void)\n{')
end=s.index('\nvoid R_ELSS_Set_f(void)',start)
newfunc=r'''void R_ELSS_SelfPick_f(void)
{
    int surface=-1,seedTri=-1,seedMode=ELSS_SEED_GROUP,p,i;float hit,triHit;vec3_t target;elssProfile_t candidate;elssFixture_t test;elssOwner_t *o;qboolean wholeSafe;
    if(!R_ELSS_Selected()||!s_iflcViewValid)return;o=&s_elssOwners[s_elssSelected];
    if(!R_ELSS_FirstHit(target,&surface,&hit)){ri.Printf(PRINT_ALL,"ELSS: aim at a solid part of the selected lamp housing.\n");return;}
    if(!R_IFLC_LineVisible(s_iflcViewOrigin,target)){ri.Printf(PRINT_WARNING,"ELSS: selected body part is occluded; no change.\n");return;}
    wholeSafe=R_ELSS_ManualSurfaceSafe(o,surface);
    if(!wholeSafe){
        unsigned char omit[ELSS_MAX_TRIM_TRIANGLES];int triCount=0,removed=0;
        if(R_ELSS_HitTriangle(surface,&seedTri,&triHit)&&R_ELSS_ComponentMask(o,surface,seedTri,omit,&triCount,&removed))seedMode=seedTri;
        else {
            int fallback=-1;float fallbackHit=0;
            if(!R_ELSS_PickSafeSurfaceNearRay(o,surface,hit,&fallback,&fallbackHit)){
                ri.Printf(PRINT_WARNING,"ELSS V1.1: surface %d is protected/shared architecture and no compact lamp-body surface was found on this crosshair ray. No change.\n",surface);return;
            }
            ri.Printf(PRINT_ALL,"ELSS V1.1: protected surface %d kept; using compact housing surface %d behind/along the same crosshair ray.\n",surface,fallback);
            surface=fallback;seedTri=-1;seedMode=ELSS_SEED_EXACT;wholeSafe=qtrue;
        }
    }
    p=R_ELSS_FindProfile(o->key);if(p>=0)candidate=s_elssProfiles[p];else{memset(&candidate,0,sizeof(candidate));for(i=0;i<ELSS_MAX_SEEDS;++i)candidate.seedTris[i]=ELSS_SEED_GROUP;candidate.used=qtrue;Q_strncpyz(candidate.key,o->key,sizeof(candidate.key));}
    for(i=0;i<candidate.seedCount;++i)if(candidate.seeds[i]==surface&&(candidate.seedTris[i]<0||seedMode<0||candidate.seedTris[i]==seedMode)){ri.Printf(PRINT_ALL,"ELSS: this body part is already bound.\n");return;}
    if(candidate.seedCount>=ELSS_MAX_SEEDS){ri.Printf(PRINT_WARNING,"ELSS: body binding limit reached.\n");return;}
    candidate.seeds[candidate.seedCount]=surface;candidate.seedTris[candidate.seedCount]=seedMode;++candidate.seedCount;
    if(!R_ELSS_BuildManual(&candidate,o,&test)&&seedMode==ELSS_SEED_GROUP){
        candidate.seedTris[candidate.seedCount-1]=ELSS_SEED_EXACT;seedMode=ELSS_SEED_EXACT;
        if(!R_ELSS_BuildManual(&candidate,o,&test)){ri.Printf(PRINT_WARNING,"ELSS: exact selected body surface did not validate; no change.\n");return;}
    } else if(!test.built||(!test.count&&!test.trimCount)) { ri.Printf(PRINT_WARNING,"ELSS: safe local body selection could not be formed; no change.\n");return; }
    p=R_ELSS_ProfileSlot(o->key,qtrue);if(p<0)return;s_elssProfiles[p]=candidate;s_elssDirty=qtrue;R_ELSS_ResetFixtures();
    if(seedMode>=0)ri.Printf(PRINT_ALL,"ELSS V1.1: bound connected component surface %d triangle %d; ownBodySurfaces=%d ownBodyTriangles=%d manualSeeds=%d. Use dw_el_set selfshadow 0 and dw_el_save.\n",surface,seedMode,test.count,test.removedTriangles,candidate.seedCount);
    else if(seedMode==ELSS_SEED_EXACT)ri.Printf(PRINT_ALL,"ELSS V1.1: bound exact compact body surface %d; ownBodySurfaces=%d ownBodyTriangles=%d manualSeeds=%d. Use dw_el_set selfshadow 0 and dw_el_save.\n",surface,test.count,test.removedTriangles,candidate.seedCount);
    else ri.Printf(PRINT_ALL,"ELSS: bound body surface %d; ownBodySurfaces=%d ownBodyTriangles=%d manualSeeds=%d. Use dw_el_set selfshadow 0 and dw_el_save.\n",surface,test.count,test.removedTriangles,candidate.seedCount);
}'''
s=s[:start]+newfunc+s[end:]
s=s.replace('int seedTris[ELSS_MAX_SEEDS]; /* -1 = legacy whole-surface seed, >=0 = connected triangle component */',
            'int seedTris[ELSS_MAX_SEEDS]; /* -1=legacy connected group, -2=exact safe surface, >=0=triangle component */')
p.write_text(s)
print('ELSS_V11_EXACT_PICK_REFINEMENT_APPLIED')
