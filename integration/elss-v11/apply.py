#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
p=src/'SP/code/rend2/tr_elss.inc'
s=p.read_text()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(s.encode())=='fb680b71233ca6346507819e46c4ae9e06cd3b3d7fb91b6d235c5394e6df7130',sha(s.encode())
before=s

marker='''static unsigned int R_ELSS_PolicyKey(const elssProfile_t *p,const int *surfaces,int count)
{
    unsigned int h=R_IFLC_Hash(surfaces,count*sizeof(int))^s_elssFingerprint^R_IFLC_Hash(p->key,(int)strlen(p->key))^0xe15e5511u;return h?h:1u;
}
'''
assert s.count(marker)==1
helper=r'''
static qboolean R_ELSS_SurfaceCenter(int index,vec3_t center,vec3_t lo,vec3_t hi)
{
    if(!R_IFLC_SelfSurfaceBoundsAny(index,lo,hi))return qfalse;
    center[0]=(lo[0]+hi[0])*.5f;center[1]=(lo[1]+hi[1])*.5f;center[2]=(lo[2]+hi[2])*.5f;
    return qtrue;
}

/* V1.1 Component Pick fallback. If the literal first BSP hit is protected
 * architecture, search only compact surfaces that are both close to the same
 * view ray and close to the already selected physical electric owner.
 * Large/coplanar architecture stays rejected and ambiguous candidates refuse. */
static qboolean R_ELSS_FindHousingNearCrosshair(const elssOwner_t *o,int *surfaceOut)
{
    int i,best=-1;float bestScore=1e30f,secondScore=1e30f;
    if(!o||!surfaceOut||!s_iflcViewValid||!R_IFLC_LineVisible(s_iflcViewOrigin,o->origin))return qfalse;
    for(i=0;i<tr.world->numWorldSurfaces;++i){
        vec3_t center,lo,hi,d;float forward,lateral2,halfDiag,owner2,threshold,score,hit;
        if(!R_ELSS_ManualSurfaceSafe(o,i)||!R_ELSS_SurfaceCenter(i,center,lo,hi))continue;
        owner2=R_IFLC_SelfBoundsDistanceSquared(o->origin,lo,hi);if(owner2>112.0f*112.0f)continue;
        VectorSubtract(center,s_iflcViewOrigin,d);forward=DotProduct(d,s_iflcViewForward);if(forward<1.0f||forward>512.0f)continue;
        lateral2=MAX(0.0f,DotProduct(d,d)-forward*forward);
        halfDiag=.5f*sqrtf((hi[0]-lo[0])*(hi[0]-lo[0])+(hi[1]-lo[1])*(hi[1]-lo[1])+(hi[2]-lo[2])*(hi[2]-lo[2]));
        threshold=MIN(56.0f,MAX(10.0f,halfDiag+8.0f+forward*.012f));
        if(lateral2>threshold*threshold)continue;
        if(R_IFLC_RaySurface(&tr.world->surfaces[i],s_iflcViewOrigin,s_iflcViewForward,512.0f,&hit))
            score=hit*.00001f+sqrtf(owner2)*.0001f;
        else
            score=1.0f+sqrtf(lateral2)/(threshold+1.0f)+sqrtf(owner2)*.002f;
        if(score<bestScore){secondScore=bestScore;bestScore=score;best=i;}
        else if(score<secondScore)secondScore=score;
    }
    if(best<0)return qfalse;
    if(secondScore<1e29f&&secondScore-bestScore<.08f)return qfalse;
    *surfaceOut=best;return qtrue;
}

/* Preserve the V1 connected-flood policy first. This exact-component builder
 * is only the fallback when that policy cannot be formed. It binds only the
 * explicitly selected compact BSP surfaces and therefore cannot grow into a
 * neighboring stand, wall, floor or ceiling. Existing DW_ELSS 1 profiles keep
 * the same format and automatically obtain this safer fallback on reload. */
static qboolean R_ELSS_BuildExact(const elssProfile_t *p,const elssOwner_t *o,elssFixture_t *out)
{
    int i,j,vertices=0;vec3_t groupLo,groupHi;
    if(!p||!o||!out||!p->used||p->seedCount<=0)return qfalse;
    memset(out,0,sizeof(*out));out->built=qtrue;ClearBounds(groupLo,groupHi);
    for(i=0;i<p->seedCount;++i){
        vec3_t lo,hi;qboolean duplicate=qfalse;const srfBspSurface_t *b;
        if(!R_ELSS_ManualSurfaceSafe(o,p->seeds[i])||!R_IFLC_SelfSurfaceBoundsAny(p->seeds[i],lo,hi))return qfalse;
        for(j=0;j<out->count;++j)if(out->surfaces[j]==p->seeds[i]){duplicate=qtrue;break;}
        if(duplicate)continue;
        if(out->count>=ELSS_MAX_SURFACES)return qfalse;
        b=R_IFLC_FixtureMesh(p->seeds[i]);if(!b)return qfalse;
        out->surfaces[out->count++]=p->seeds[i];vertices+=b->numVerts;
        AddPointToBounds(lo,groupLo,groupHi);AddPointToBounds(hi,groupLo,groupHi);
    }
    if(!out->count||vertices<3)return qfalse;
    if(groupHi[0]-groupLo[0]>192||groupHi[1]-groupLo[1]>192||groupHi[2]-groupLo[2]>256)return qfalse;
    out->key=R_ELSS_PolicyKey(p,out->surfaces,out->count)^0x11ec7a01u;if(!out->key)out->key=1u;
    return qtrue;
}
'''
s=s.replace(marker,marker+helper)

old='static qboolean R_ELSS_BuildManual(const elssProfile_t *p,const elssOwner_t *o,elssFixture_t *out)
{'
assert s.count(old)==1
s=s.replace(old,'static qboolean R_ELSS_BuildFlood(const elssProfile_t *p,const elssOwner_t *o,elssFixture_t *out)
{',1)
tail='''    if(!out->count||vertices<3){out->count=0;return qfalse;}if(groupHi[0]-groupLo[0]>192||groupHi[1]-groupLo[1]>192||groupHi[2]-groupLo[2]>256){out->count=0;return qfalse;}out->key=R_ELSS_PolicyKey(p,out->surfaces,out->count);return qtrue;
}

static void R_ELSS_PrepareProfileFixture'''
assert s.count(tail)==1
s=s.replace(tail,'''    if(!out->count||vertices<3){out->count=0;return qfalse;}if(groupHi[0]-groupLo[0]>192||groupHi[1]-groupLo[1]>192||groupHi[2]-groupLo[2]>256){out->count=0;return qfalse;}out->key=R_ELSS_PolicyKey(p,out->surfaces,out->count);return qtrue;
}
static qboolean R_ELSS_BuildManual(const elssProfile_t *p,const elssOwner_t *o,elssFixture_t *out)
{
    if(R_ELSS_BuildFlood(p,o,out))return qtrue;
    return R_ELSS_BuildExact(p,o,out);
}

static void R_ELSS_PrepareProfileFixture''')

old='''void R_ELSS_SelfPick_f(void)
{
    int surface=-1,p,i;float hit;vec3_t target;elssProfile_t candidate;elssFixture_t test;elssOwner_t *o;if(!R_ELSS_Selected()||!s_iflcViewValid)return;o=&s_elssOwners[s_elssSelected];if(!R_ELSS_FirstHit(target,&surface,&hit)){ri.Printf(PRINT_ALL,"ELSS: aim at a solid part of the selected lamp housing.\n");return;}if(!R_IFLC_LineVisible(s_iflcViewOrigin,target)){ri.Printf(PRINT_WARNING,"ELSS: selected body part is occluded; no change.\n");return;}if(!R_ELSS_ManualSurfaceSafe(o,surface)){ri.Printf(PRINT_WARNING,"ELSS: surface %d is architecture, too large, translucent/deformed, or too far from this lamp. No change.\n",surface);return;}p=R_ELSS_FindProfile(o->key);if(p>=0)candidate=s_elssProfiles[p];else{memset(&candidate,0,sizeof(candidate));candidate.used=qtrue;Q_strncpyz(candidate.key,o->key,sizeof(candidate.key));}for(i=0;i<candidate.seedCount;++i)if(candidate.seeds[i]==surface){ri.Printf(PRINT_ALL,"ELSS: this body part is already bound.\n");return;}if(candidate.seedCount>=ELSS_MAX_SEEDS){ri.Printf(PRINT_WARNING,"ELSS: body binding limit reached.\n");return;}candidate.seeds[candidate.seedCount++]=surface;if(!R_ELSS_BuildManual(&candidate,o,&test)){ri.Printf(PRINT_WARNING,"ELSS: safe local body group could not be formed; aim at another solid housing part. No change.\n");return;}
    p=R_ELSS_ProfileSlot(o->key,qtrue);if(p<0)return;s_elssProfiles[p]=candidate;s_elssDirty=qtrue;R_ELSS_ResetFixtures();ri.Printf(PRINT_ALL,"ELSS: bound body surface %d; safeLocalGroup=%d surfaces manualSeeds=%d. Use dw_el_set selfshadow 0 and dw_el_save.\n",surface,test.count,candidate.seedCount);
}'''
new='''void R_ELSS_SelfPick_f(void)
{
    int surface=-1,p,i,firstSurface=-1;float hit;vec3_t target;elssProfile_t candidate;elssFixture_t test;elssOwner_t *o;qboolean fallback=qfalse;
    if(!R_ELSS_Selected()||!s_iflcViewValid)return;o=&s_elssOwners[s_elssSelected];
    if(!R_ELSS_FirstHit(target,&surface,&hit)){ri.Printf(PRINT_ALL,"ELSS: aim at a solid part of the selected lamp housing.\n");return;}
    firstSurface=surface;
    if(!R_IFLC_LineVisible(s_iflcViewOrigin,target)){ri.Printf(PRINT_WARNING,"ELSS: selected body part is occluded; no change.\n");return;}
    if(!R_ELSS_ManualSurfaceSafe(o,surface)){
        if(!R_ELSS_FindHousingNearCrosshair(o,&surface)){ri.Printf(PRINT_WARNING,"ELSS: surface %d is protected architecture/too large and no unique safe housing part is close enough to this crosshair. No change.\n",firstSurface);return;}
        fallback=qtrue;
    }
    p=R_ELSS_FindProfile(o->key);if(p>=0)candidate=s_elssProfiles[p];else{memset(&candidate,0,sizeof(candidate));candidate.used=qtrue;Q_strncpyz(candidate.key,o->key,sizeof(candidate.key));}
    for(i=0;i<candidate.seedCount;++i)if(candidate.seeds[i]==surface){ri.Printf(PRINT_ALL,"ELSS: this body part is already bound.\n");return;}
    if(candidate.seedCount>=ELSS_MAX_SEEDS){ri.Printf(PRINT_WARNING,"ELSS: body binding limit reached.\n");return;}
    candidate.seeds[candidate.seedCount++]=surface;
    if(!R_ELSS_BuildManual(&candidate,o,&test)){ri.Printf(PRINT_WARNING,"ELSS: safe exact body component could not be formed; aim at another solid housing part. No change.\n");return;}
    p=R_ELSS_ProfileSlot(o->key,qtrue);if(p<0)return;s_elssProfiles[p]=candidate;s_elssDirty=qtrue;R_ELSS_ResetFixtures();
    if(fallback)ri.Printf(PRINT_ALL,"ELSS V1.1: protected surface %d ignored; bound nearby safe body surface %d; ownBodySurfaces=%d manualSeeds=%d. Use dw_el_set selfshadow 0 and dw_el_save.\n",firstSurface,surface,test.count,candidate.seedCount);
    else ri.Printf(PRINT_ALL,"ELSS V1.1: bound body surface %d; ownBodySurfaces=%d manualSeeds=%d. Use dw_el_set selfshadow 0 and dw_el_save.\n",surface,test.count,candidate.seedCount);
}'''
assert s.count(old)==1
s=s.replace(old,new)

p.write_text(s)
after=s
proof={
 "version":"ELSS V1.1 Component Pick",
 "base_run":41982135692,
 "base_version":"ELSS V1.0.1 Persistence Fix",
 "changed":["SP/code/rend2/tr_elss.inc"],
 "profile_format":"DW_ELSS 1 unchanged",
 "persistence_fix_preserved":True,
 "component_policy":"V1 connected flood first, exact picked compact surfaces fallback",
 "protected_hit_policy":"never suppress protected first hit; optional unique compact owner-local crosshair fallback",
 "shadow_slot_preserved":True,
 "direct_preserved":True,
 "local_volumetric_preserved":True,
 "other_casters_preserved":True,
 "iflc_v15u_unchanged":True,
 "glsl_unchanged":True,
 "map_specific_production_logic":False
}
(ev/'ELSS_V11_SOURCE_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
(ev/'ELSS_V11_TR_ELSS_SHA256.txt').write_text(sha(after.encode())+'  tr_elss.inc\n')
print('ELSS_V11_COMPONENT_PICK_APPLIED',sha(after.encode()))
