#!/usr/bin/env python3
from pathlib import Path
import sys,hashlib,json
src=Path(sys.argv[1]).resolve()
p=src/"SP/code/rend2/tr_iflc_self.inc"
s=p.read_text()
marker="static void R_IFLC_SelfPolicyKey(int ownerIndex,iflcSelfFixture_t *out)\n"
assert s.count(marker)==1
helper=r'''
/* V1.5 manual-part selection.
 * The user-picked surface defines where the own-body component starts.  It no
 * longer has to fit the flame-centered AUTO window.  Growth is deliberately
 * local and stops at large structural planes, so a hanging bowl/cage can be
 * selected without adopting the ceiling, floor or wall it touches.  More than
 * one disconnected own-body part can be bound by repeating dw_fl_self_pick.
 */
static qboolean R_IFLC_ManualSurfaceSafe(int index,const vec3_t ownerOrigin,
    const vec3_t protectN[32],const float protectD[32],int protectCount)
{
    const srfBspSurface_t *b=R_IFLC_FixtureMesh(index);const msurface_t *surface;
    vec3_t lo,hi,n;float d,dx,dy,dz,dist=0;int i,j;
    if(!tr.world||index<0||index>=tr.world->numWorldSurfaces||!b||
       b->numVerts<3||b->numVerts>4096||b->numIndexes>12288)return qfalse;
    surface=&tr.world->surfaces[index];
    if(!R_IFLC_FixtureOpaque(surface)||surface->shader->numDeforms||surface->shader->polygonOffset)return qfalse;
    R_IFLC_FixtureBounds(b,lo,hi);dx=hi[0]-lo[0];dy=hi[1]-lo[1];dz=hi[2]-lo[2];
    /* A room plane is large in two axes. Long thin rods/straps remain valid. */
    if((dx>144&&dy>144)||(dx>144&&dz>144)||(dy>144&&dz>144))return qfalse;
    for(i=0;i<3;++i){float a=MAX(MAX(lo[i]-ownerOrigin[i],ownerOrigin[i]-hi[i]),0);dist+=a*a;}
    if(dist>256.0f*256.0f)return qfalse;
    if(R_IFLC_FixturePlane(b,n,&d))for(j=0;j<protectCount;++j){
        float side=DotProduct(protectN[j],n);
        if(fabsf(fabsf(side)-1)<.001f&&fabsf(protectD[j]-(side>0?d:-d))<.25f)return qfalse;
    }
    return qtrue;
}

static qboolean R_IFLC_BuildManualPartOne(int ownerIndex,int seed,iflcSelfFixture_t *out)
{
    int candidates[IFLC_SELF_CANDIDATES],n=0,i,j,k,seedCandidate=-1;
    qboolean included[IFLC_SELF_CANDIDATES],changed;
    vec3_t seedLo,seedHi,seedCenter,low,high,protectN[32],unionLo,unionHi;
    float protectD[32];int protectCount=0,vertices=0,startCount=out->count;
    const srfBspSurface_t *seedMesh=R_IFLC_FixtureMesh(seed);
    if(!seedMesh)return qfalse;
    R_IFLC_FixtureBounds(seedMesh,seedLo,seedHi);
    for(k=0;k<3;++k)seedCenter[k]=(seedLo[k]+seedHi[k])*.5f;
    low[0]=seedCenter[0]-96;high[0]=seedCenter[0]+96;
    low[1]=seedCenter[1]-96;high[1]=seedCenter[1]+96;
    low[2]=seedCenter[2]-128;high[2]=seedCenter[2]+128;
    /* Record nearby large architecture planes. A small BSP fragment coplanar
     * with one of them is also structural and cannot join the manual body. */
    for(i=0;i<tr.world->numWorldSurfaces;++i){
        const srfBspSurface_t *b=R_IFLC_FixtureMesh(i);vec3_t lo,hi,norm;
        float d,dx,dy,dz,dist=0;
        if(!b||!R_IFLC_FixtureOpaque(&tr.world->surfaces[i])||!R_IFLC_FixturePlane(b,norm,&d))continue;
        R_IFLC_FixtureBounds(b,lo,hi);dx=hi[0]-lo[0];dy=hi[1]-lo[1];dz=hi[2]-lo[2];
        if(!((dx>160&&dy>160)||(dx>160&&dz>160)||(dy>160&&dz>160)))continue;
        for(k=0;k<3;++k){float a=MAX(MAX(lo[k]-seedCenter[k],seedCenter[k]-hi[k]),0);dist+=a*a;}
        if(dist>224.0f*224.0f)continue;
        for(j=0;j<protectCount;++j)if(fabsf(fabsf(DotProduct(protectN[j],norm))-1)<.001f&&
            fabsf(protectD[j]-(DotProduct(protectN[j],norm)>0?d:-d))<.25f)break;
        if(j<protectCount)continue;if(protectCount>=32)return qfalse;
        VectorCopy(norm,protectN[protectCount]);protectD[protectCount++]=d;
    }
    if(!R_IFLC_ManualSurfaceSafe(seed,s_iflcOwners[ownerIndex].origin,protectN,protectD,protectCount))return qfalse;
    for(i=0;i<tr.world->numWorldSurfaces;++i){
        const srfBspSurface_t *b=R_IFLC_FixtureMesh(i);vec3_t lo,hi;
        if(!b)continue;R_IFLC_FixtureBounds(b,lo,hi);
        if(!R_IFLC_FixtureInside(lo,hi,low,high))continue;
        if(!R_IFLC_ManualSurfaceSafe(i,s_iflcOwners[ownerIndex].origin,protectN,protectD,protectCount))continue;
        if(n>=IFLC_SELF_CANDIDATES)return qfalse;
        candidates[n]=i;if(i==seed)seedCandidate=n;++n;
    }
    if(seedCandidate<0)return qfalse;
    memset(included,0,sizeof(included));included[seedCandidate]=qtrue;
    do{changed=qfalse;
        for(i=0;i<n;++i)if(!included[i])for(j=0;j<n;++j)if(included[j]&&
            R_IFLC_SelfContact(R_IFLC_FixtureMesh(candidates[i]),R_IFLC_FixtureMesh(candidates[j]))){
                included[i]=qtrue;changed=qtrue;break;
            }
    }while(changed);
    ClearBounds(unionLo,unionHi);
    for(i=0;i<n;++i)if(included[i]){
        const srfBspSurface_t *b=R_IFLC_FixtureMesh(candidates[i]);qboolean duplicate=qfalse;
        for(j=0;j<out->count;++j)if(out->surfaces[j]==candidates[i]){duplicate=qtrue;break;}
        if(duplicate)continue;
        if(out->count>=IFLC_SELF_CAP||out->count-startCount>=32)return qfalse;
        out->surfaces[out->count++]=candidates[i];vertices+=b->numVerts;
        if(vertices>1024)return qfalse;
        for(j=0;j<b->numVerts;++j)AddPointToBounds(b->verts[j].xyz,unionLo,unionHi);
    }
    if(out->count==startCount)return qfalse;
    if(unionHi[0]-unionLo[0]>160||unionHi[1]-unionLo[1]>160||unionHi[2]-unionLo[2]>224)return qfalse;
    return qtrue;
}

static qboolean R_IFLC_BuildManualParts(int ownerIndex,const iflcProfile_t *profile,
    iflcSelfFixture_t *out)
{
    int i;memset(out,0,sizeof(*out));out->built=qtrue;
    if(!profile||profile->selfSeedCount<1||profile->selfSeedCount>8)return qfalse;
    for(i=0;i<profile->selfSeedCount;++i)
        if(!R_IFLC_BuildManualPartOne(ownerIndex,profile->selfSeeds[i],out)){out->count=0;return qfalse;}
    if(!out->count)return qfalse;
    R_IFLC_SelfPolicyKey(ownerIndex,out);
    return qtrue;
}

'''
# helper calls policy key, so add forward declaration before helper.
s=s.replace(marker,"static void R_IFLC_SelfPolicyKey(int ownerIndex,iflcSelfFixture_t *out);\n\n"+helper+marker)
old="    if(!tr.world || !profile || !R_IFLC_SelfBounds(ownerIndex,flameLo,flameHi,anchor)) return qfalse;\n    /* Accepted V1.2 groups already proved the support wall, shaft and body."
new="    if(!tr.world || !profile || !R_IFLC_SelfBounds(ownerIndex,flameLo,flameHi,anchor)) return qfalse;\n    if(profile->selfSeedCount) return R_IFLC_BuildManualParts(ownerIndex,profile,out);\n    /* Accepted V1.2 groups already proved the support wall, shaft and body."
assert s.count(old)==1
s=s.replace(old,new)
p.write_text(s)
p=src/"SP/code/rend2/tr_iflc.inc";s=p.read_text()
old='ri.Printf(PRINT_WARNING,"IFLC: not a safe small connected fixture; wall/floor/ambiguous geometry protected. No change.\\n"); return;'
new='ri.Printf(PRINT_WARNING,"IFLC: selected body part is unsafe or reaches protected architecture. Aim at a more local solid part; wall/floor/ceiling remain protected. No change.\\n"); return;'
assert s.count(old)==1;s=s.replace(old,new)
old='ri.Printf(PRINT_ALL,"IFLC: bound body surface %d (%d connected surfaces). Use dw_fl_set selfshadow 0 and dw_fl_save.\\n",selected,test.count);'
new='ri.Printf(PRINT_ALL,"IFLC V1.5: bound body part seed=%d localSurfaces=%d. Repeat dw_fl_self_pick for another disconnected part, then use dw_fl_set selfshadow 0 and dw_fl_save.\\n",selected,test.count);'
assert s.count(old)==1;s=s.replace(old,new)
p.write_text(s)
# proof
changed=["SP/code/rend2/tr_iflc.inc","SP/code/rend2/tr_iflc_self.inc"]
print("IFLC15_MANUAL_PART_PATCH_APPLIED",changed)
