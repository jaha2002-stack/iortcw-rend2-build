#!/usr/bin/env python3
"""Reuse accepted fixture proofs and join actual T-junction housing contacts.
Only explicit own-body rules change; accepted AUTO and electric logic do not.
"""
from pathlib import Path
import sys
src=Path(sys.argv[1]);p=src/'SP/code/rend2/tr_iflc_self.inc';s=p.read_text()
anchor='/* Explicit profile is passed so validation never partially changes live state. */'
helper=r'''
/* BSP triangulation need not retain matching vertices at a T junction.
 * A frame bar can terminate within a roof triangle. Require two separated
 * contact points on the actual triangles, not merely overlapping bounds or
 * one shared corner; structural planes remain excluded before this graph. */
static qboolean R_IFLC_SelfPointOnMesh(const vec3_t point,const srfBspSurface_t *mesh)
{
    int i;
    for(i=0;i+2<mesh->numIndexes;i+=3) {
        unsigned int ai=mesh->indexes[i],bi=mesh->indexes[i+1],ci=mesh->indexes[i+2];
        vec3_t u,v,w,n;float uu,uv,vv,wu,wv,den,x,y;
        const float *a,*b,*c;
        if(ai>=(unsigned int)mesh->numVerts||bi>=(unsigned int)mesh->numVerts||ci>=(unsigned int)mesh->numVerts)return qfalse;
        a=mesh->verts[ai].xyz;b=mesh->verts[bi].xyz;c=mesh->verts[ci].xyz;
        VectorSubtract(b,a,u);VectorSubtract(c,a,v);VectorSubtract(point,a,w);
        CrossProduct(u,v,n);
        if(VectorNormalize(n)<.001f || fabsf(DotProduct(n,w))>.125f)continue;
        uu=DotProduct(u,u);uv=DotProduct(u,v);vv=DotProduct(v,v);
        wu=DotProduct(w,u);wv=DotProduct(w,v);den=uu*vv-uv*uv;
        if(den<.000001f)continue;
        x=(vv*wu-uv*wv)/den;y=(uu*wv-uv*wu)/den;
        if(x>=-.0001f && y>=-.0001f && x+y<=1.0001f)return qtrue;
    }
    return qfalse;
}
static qboolean R_IFLC_SelfContact(const srfBspSurface_t *a,const srfBspSurface_t *b)
{
    vec3_t alo,ahi,blo,bhi,first;
    int i,side; qboolean haveFirst=qfalse;
    if(!a||!b)return qfalse;
    R_IFLC_FixtureBounds(a,alo,ahi);R_IFLC_FixtureBounds(b,blo,bhi);
    for(i=0;i<3;++i)if(alo[i]>bhi[i]+.125f||blo[i]>ahi[i]+.125f)return qfalse;
    if(R_IFLC_FixtureAdjacent(a,b))return qtrue;
    for(side=0;side<2;++side) {
        const srfBspSurface_t *from=side?b:a,*to=side?a:b;
        for(i=0;i<from->numVerts;++i)if(R_IFLC_SelfPointOnMesh(from->verts[i].xyz,to)) {
            if(haveFirst && R_IFLC_DistanceSquared(first,from->verts[i].xyz)>.0625f)return qtrue;
            if(!haveFirst){VectorCopy(from->verts[i].xyz,first);haveFirst=qtrue;}
        }
    }
    return qfalse;
}
static void R_IFLC_SelfPolicyKey(int ownerIndex,iflcSelfFixture_t *out)
{
    out->key=R_IFLC_Hash(out->surfaces,out->count*sizeof(int))^s_iflcFingerprint^
        R_IFLC_Hash(s_iflcOwners[ownerIndex].key,(int)strlen(s_iflcOwners[ownerIndex].key))^0x14a1f1c1u;
    if(!out->key)out->key=1;
}

'''
assert s.count(anchor)==1;s=s.replace(anchor,helper+anchor)
anchor='    height=flameHi[2]-flameLo[2];'
replacement=r'''    /* Accepted V1.2 groups already proved the support wall, shaft and body.
     * Do not reject those groups merely because unrelated architecture creates
     * more than 32 nearby planes in the broader generic housing search.
     * Manual seeds outside this proven group still require the generic guard. */
    R_IFLC_PrepareFixture(ownerIndex);
    if(s_iflcFixtures[ownerIndex].count>0) {
        qboolean contained=qtrue;
        const iflcFixture_t *proven=&s_iflcFixtures[ownerIndex];
        for(i=0;i<profile->selfSeedCount;++i) {
            for(j=0;j<proven->count&&proven->surfaces[j]!=profile->selfSeeds[i];++j){}
            if(j==proven->count){contained=qfalse;break;}
        }
        if(contained && proven->count<=IFLC_SELF_CAP) {
            out->count=proven->count;
            memcpy(out->surfaces,proven->surfaces,out->count*sizeof(int));
            R_IFLC_SelfPolicyKey(ownerIndex,out);
            return qtrue;
        }
    }
    height=flameHi[2]-flameLo[2];'''
assert s.count(anchor)==1;s=s.replace(anchor,replacement)
old='R_IFLC_FixtureAdjacent(R_IFLC_FixtureMesh(candidates[i]),R_IFLC_FixtureMesh(candidates[j])))'
assert s.count(old)==1;s=s.replace(old,'R_IFLC_SelfContact(R_IFLC_FixtureMesh(candidates[i]),R_IFLC_FixtureMesh(candidates[j])))')
old='    out->key=R_IFLC_Hash(out->surfaces,out->count*sizeof(int))^s_iflcFingerprint^\n        R_IFLC_Hash(s_iflcOwners[ownerIndex].key,(int)strlen(s_iflcOwners[ownerIndex].key))^0x14a1f1c1u;\n    if(!out->key)out->key=1;\n    return qtrue;'
assert s.count(old)==1;s=s.replace(old,'    R_IFLC_SelfPolicyKey(ownerIndex,out);\n    return qtrue;')
p.write_text(s)
print('EXPLICIT_SELF_T_JUNCTION_REFINEMENT_APPLIED')
