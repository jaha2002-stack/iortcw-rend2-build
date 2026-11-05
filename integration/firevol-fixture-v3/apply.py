#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve(); ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
H=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()

expected={
 'tr_backend.c':'c205f59d4993695e06afb43692f8386e2153fe598f04a4cfbc7538124fbce749',
 'tr_iflc.inc':'318c2eba928b70badb238bc567a3e9a025d95d99c57498d6af68508d7bc64b5c',
 'tr_init.c':'312f2cc7cb1e295c05790df01826925fad5b415ba5d74e023a05d8a8a096ccb3',
 'tr_local.h':'6bb152e1b7635fc154186ea484593f524d358d6a8b89a4172bc2e6efdfcf3e6c'}
for p,h in expected.items():
    a=H(p); assert a==h,(p,a,h)

def rep(s,a,b,label):
    c=s.count(a); assert c==1,(label,c); return s.replace(a,b,1)

# IFLC: build read-only world-surface catalog regardless of editor master and expose a
# world-only owner lookup. Never feed model/draw indices to this API.
p=root/'tr_iflc.inc'; s=p.read_text()
s=rep(s,'\tif (!enabled && !s_iflcReady) return;\n\tif (!R_IFLC_EnsureCatalog() || s_iflcCatalogOverflow) return;',
      '\t/* FireVol Fixture V3 needs map-scoped world-surface ownership even when the editor is off. */\n\tif (!R_IFLC_EnsureCatalog() || s_iflcCatalogOverflow) return;',
      'iflc always catalog')
marker='qboolean R_IFLC_VolumeOverride(int surfaceIndex, const char *shaderName, const vec3_t origin, float *gain)\n'
api=r'''/* DARKWOLF_FIREVOL_FIXTURE_OWNER_V3: world surfaces only.
 * Non-world FireVol anchors use primitive/entity identity in the backend. */
int R_IFLC_FireOwnerForWorldSurface(int surfaceIndex)
{
    int i, owner;
    if (!s_iflcReady || s_iflcCatalogOverflow || !tr.world ||
        strcmp(s_iflcMap, tr.world->baseName) ||
        surfaceIndex < 0 || surfaceIndex >= tr.world->numWorldSurfaces)
        return 0;
    for (i = 0; i < s_iflcSurfaceCount; ++i) {
        if (s_iflcSurfaces[i].surfaceIndex != surfaceIndex) continue;
        owner = s_iflcSurfaces[i].owner;
        if (owner < 0 || owner >= s_iflcOwnerCount || s_iflcOwners[owner].ambiguous) return 0;
        return owner + 1;
    }
    return 0;
}

'''
assert s.count(marker)==1; s=s.replace(marker,api+marker,1); p.write_text(s)

# Public cvars/API.
p=root/'tr_local.h'; s=p.read_text()
s=rep(s,'extern cvar_t *r_dwFireLightControl;\n',
      'extern cvar_t *r_dwFireLightControl;\nextern cvar_t *r_dwFireVolFixtureV3;\nextern cvar_t *r_dwFireVolFixtureDiag;\nextern cvar_t *r_dwFireVolGeometryScale;\nextern cvar_t *r_dwFireVolGeometryMin;\n',
      'extern cvars')
s=rep(s,'int R_IFLC_SurfaceSelfFixture(int surfaceIndex);\n',
      'int R_IFLC_SurfaceSelfFixture(int surfaceIndex);\nint R_IFLC_FireOwnerForWorldSurface(int surfaceIndex);\n',
      'owner api declaration')
p.write_text(s)

p=root/'tr_init.c'; s=p.read_text()
s=rep(s,'cvar_t  *r_dwFireLightControl; // DARKWOLF_IFLC_V1, explicit opt-in master.\n',
      'cvar_t  *r_dwFireLightControl; // DARKWOLF_IFLC_V1, explicit opt-in master.\ncvar_t  *r_dwFireVolFixtureV3; // source-aware physical FireVol owner\ncvar_t  *r_dwFireVolFixtureDiag;\ncvar_t  *r_dwFireVolGeometryScale;\ncvar_t  *r_dwFireVolGeometryMin;\n',
      'cvar declarations')
a='\tr_dwFireLightControl = ri.Cvar_Get( "r_dwFireLightControl", "0", CVAR_ARCHIVE );\n\tri.Cvar_CheckRange(r_dwFireLightControl, 0.0f, 1.0f, qtrue);\n'
b=a+'\tr_dwFireVolFixtureV3 = ri.Cvar_Get( "r_dwFireVolFixtureV3", "1", CVAR_ARCHIVE );\n\tri.Cvar_CheckRange(r_dwFireVolFixtureV3, 0.0f, 1.0f, qtrue);\n\tr_dwFireVolFixtureDiag = ri.Cvar_Get( "r_dwFireVolFixtureDiag", "0", 0 );\n\tri.Cvar_CheckRange(r_dwFireVolFixtureDiag, 0.0f, 1.0f, qtrue);\n\tr_dwFireVolGeometryScale = ri.Cvar_Get( "r_dwFireVolGeometryScale", "0.55", CVAR_ARCHIVE );\n\tri.Cvar_CheckRange(r_dwFireVolGeometryScale, 0.25f, 1.0f, qfalse);\n\tr_dwFireVolGeometryMin = ri.Cvar_Get( "r_dwFireVolGeometryMin", "96", CVAR_ARCHIVE );\n\tri.Cvar_CheckRange(r_dwFireVolGeometryMin, 64.0f, 180.0f, qfalse);\n'
s=rep(s,a,b,'cvar registration'); p.write_text(s)

p=root/'tr_backend.c'; s=p.read_text()

# Persist source identity in registry. surfaceIndex alone is not globally meaningful:
# BMODEL uses global BSP surface index, MDV uses model-local index, POLY/flare/entity use drawIndex.
old='''\tqboolean latchValid;
\tint latchedFlameSurface;
\tvec3_t latchedFlameOrigin;
\tchar latchedShader[MAX_QPATH];
\tint latchedAtMs;
'''
new='''\tqboolean latchValid;
\tint latchedFlameSurface;
\tvec3_t latchedFlameOrigin;
\tchar latchedShader[MAX_QPATH];
\tint latchedAtMs;
\tint latchedPrimitive; // FIREVOL_PRIM_* identity domain
\tint latchedEntityNum; // stable owner for BMODEL/model/entity sources
\tint latchedShaderIndex;
\tchar latchedModelName[MAX_QPATH];
'''
# only pool slot, not selection: first occurrence
assert s.count(old)>=2
s=s.replace(old,new,1)

# Helpers are inserted after pool globals: they only depend on already-defined anchors and pool type.
marker='static qboolean s_fireV07SingleValid = qfalse;\n'
helpers=r'''#define FIREVOL_FIXKEY_NONE 0
#define FIREVOL_FIXKEY_WORLD_IFLC 1
#define FIREVOL_FIXKEY_BMODEL 2
#define FIREVOL_FIXKEY_MODEL 3
#define FIREVOL_FIXKEY_ENTITY 4

typedef struct {
    int kind;
    int a;
    int b;
} fireVolumetricFixtureKeyV3_t;

static qboolean RB_FireVFixtureV3KeyEqual(const fireVolumetricFixtureKeyV3_t *a,
    const fireVolumetricFixtureKeyV3_t *b)
{
    return a && b && a->kind > 0 && a->kind == b->kind && a->a == b->a && a->b == b->b;
}

static qboolean RB_FireVFixtureV3KeyForAnchor(const fireVolumetricV07Anchor_t *a,
    fireVolumetricFixtureKeyV3_t *out)
{
    int token;
    if (!out) return qfalse;
    memset(out,0,sizeof(*out));
    if (!a || !a->semanticFire) return qfalse;
    if (a->primitive == FIREVOL_PRIM_WORLD) {
        token=R_IFLC_FireOwnerForWorldSurface(a->surfaceIndex);
        if (token<=0) return qfalse;
        out->kind=FIREVOL_FIXKEY_WORLD_IFLC; out->a=token; out->b=0; return qtrue;
    }
    if (a->primitive == FIREVOL_PRIM_BMODEL && a->entityNum != REFENTITYNUM_WORLD) {
        out->kind=FIREVOL_FIXKEY_BMODEL; out->a=a->entityNum; out->b=a->shaderIndex; return qtrue;
    }
    if ((a->primitive == FIREVOL_PRIM_MDV || a->primitive == FIREVOL_PRIM_MODEL_FALLBACK) &&
        a->entityNum >= 0 && a->entityNum != REFENTITYNUM_WORLD) {
        out->kind=FIREVOL_FIXKEY_MODEL; out->a=a->entityNum; out->b=a->shaderIndex; return qtrue;
    }
    if ((a->primitive == FIREVOL_PRIM_ENTITY || a->primitive == FIREVOL_PRIM_FLARE) &&
        a->entityNum >= 0 && a->entityNum != REFENTITYNUM_WORLD) {
        out->kind=FIREVOL_FIXKEY_ENTITY; out->a=a->entityNum; out->b=a->shaderIndex; return qtrue;
    }
    /* Cgame POLY/drawIndex is transient. Failing open is safer than false owner merges. */
    return qfalse;
}

static qboolean RB_FireVFixtureV3KeyForPool(const fireVolumetricV07PoolSlot_t *p,
    fireVolumetricFixtureKeyV3_t *out)
{
    int token;
    if (!out) return qfalse;
    memset(out,0,sizeof(*out));
    if (!p || !p->valid || !p->latchValid) return qfalse;
    if (p->latchedPrimitive == FIREVOL_PRIM_WORLD) {
        token=R_IFLC_FireOwnerForWorldSurface(p->latchedFlameSurface);
        if (token<=0) return qfalse;
        out->kind=FIREVOL_FIXKEY_WORLD_IFLC; out->a=token; return qtrue;
    }
    if (p->latchedPrimitive == FIREVOL_PRIM_BMODEL && p->latchedEntityNum != REFENTITYNUM_WORLD) {
        out->kind=FIREVOL_FIXKEY_BMODEL; out->a=p->latchedEntityNum; out->b=p->latchedShaderIndex; return qtrue;
    }
    if ((p->latchedPrimitive == FIREVOL_PRIM_MDV || p->latchedPrimitive == FIREVOL_PRIM_MODEL_FALLBACK) &&
        p->latchedEntityNum >= 0 && p->latchedEntityNum != REFENTITYNUM_WORLD) {
        out->kind=FIREVOL_FIXKEY_MODEL; out->a=p->latchedEntityNum; out->b=p->latchedShaderIndex; return qtrue;
    }
    if ((p->latchedPrimitive == FIREVOL_PRIM_ENTITY || p->latchedPrimitive == FIREVOL_PRIM_FLARE) &&
        p->latchedEntityNum >= 0 && p->latchedEntityNum != REFENTITYNUM_WORLD) {
        out->kind=FIREVOL_FIXKEY_ENTITY; out->a=p->latchedEntityNum; out->b=p->latchedShaderIndex; return qtrue;
    }
    return qfalse;
}

static qboolean RB_FireVFixtureV3KeyForCatalogSurface(int surfaceIndex,
    fireVolumetricFixtureKeyV3_t *out)
{
    int token;
    if (!out) return qfalse;
    memset(out,0,sizeof(*out));
    token=R_IFLC_FireOwnerForWorldSurface(surfaceIndex);
    if (token<=0) return qfalse;
    out->kind=FIREVOL_FIXKEY_WORLD_IFLC; out->a=token; return qtrue;
}

static int RB_FireVFixtureV3CurrentAnchor(const fireVolumetricFixtureKeyV3_t *key,
    vec3_t centroid)
{
    int i,count=0,rep=-1,repSurface=0x7fffffff;
    VectorClear(centroid);
    if (!key || key->kind<=0) return -1;
    for(i=0;i<s_fireV07AnchorCount;++i) {
        fireVolumetricFixtureKeyV3_t ak;
        const fireVolumetricV07Anchor_t *a=&s_fireV07Anchors[i];
        if(!RB_FireVFixtureV3KeyForAnchor(a,&ak)||!RB_FireVFixtureV3KeyEqual(key,&ak)) continue;
        VectorAdd(centroid,a->origin,centroid); count++;
        if(rep<0 || a->surfaceIndex<repSurface){rep=i;repSurface=a->surfaceIndex;}
    }
    if(count<=0) return -1;
    VectorScale(centroid,1.0f/(float)count,centroid);
    return rep;
}

static void RB_FireVFixtureV3RefreshRegistry(void)
{
    int slot;
    if(!r_dwFireVolFixtureV3||!r_dwFireVolFixtureV3->integer) return;
    for(slot=0;slot<FIREVOL07_MAX_POOL;++slot) {
        fireVolumetricV07PoolSlot_t *p=&s_fireV07Pool[slot];
        fireVolumetricFixtureKeyV3_t key;
        vec3_t center,delta;
        int rep;
        if(!RB_FireVFixtureV3KeyForPool(p,&key)) continue;
        rep=RB_FireVFixtureV3CurrentAnchor(&key,center);
        if(rep<0) continue;
        VectorSubtract(center,p->latchedFlameOrigin,delta);
        if(DotProduct(delta,delta)>1.0f) {
            VectorCopy(center,p->latchedFlameOrigin);
            p->radiusStateValid=qfalse;
        }
        /* Stable representative prevents a moving BMODEL from leaving multiple cache identities. */
        p->latchedFlameSurface=s_fireV07Anchors[rep].surfaceIndex;
        p->latchedPrimitive=s_fireV07Anchors[rep].primitive;
        p->latchedEntityNum=s_fireV07Anchors[rep].entityNum;
        p->latchedShaderIndex=s_fireV07Anchors[rep].shaderIndex;
        Q_strncpyz(p->latchedShader,s_fireV07Anchors[rep].shaderName,sizeof(p->latchedShader));
        Q_strncpyz(p->latchedModelName,s_fireV07Anchors[rep].modelName,sizeof(p->latchedModelName));
    }
}

static int RB_FireVFixtureV3FindPoolForAnchor(const fireVolumetricV07Anchor_t *a)
{
    int slot; fireVolumetricFixtureKeyV3_t ak;
    if(!r_dwFireVolFixtureV3||!r_dwFireVolFixtureV3->integer||!RB_FireVFixtureV3KeyForAnchor(a,&ak)) return -1;
    for(slot=0;slot<FIREVOL07_MAX_POOL;++slot){fireVolumetricFixtureKeyV3_t pk;
        if(RB_FireVFixtureV3KeyForPool(&s_fireV07Pool[slot],&pk)&&RB_FireVFixtureV3KeyEqual(&ak,&pk))return slot;}
    return -1;
}

static int RB_FireVFixtureV3FindPoolForCatalogSurface(int surfaceIndex)
{
    int slot; fireVolumetricFixtureKeyV3_t ek;
    if(!r_dwFireVolFixtureV3||!r_dwFireVolFixtureV3->integer||!RB_FireVFixtureV3KeyForCatalogSurface(surfaceIndex,&ek)) return -1;
    for(slot=0;slot<FIREVOL07_MAX_POOL;++slot){fireVolumetricFixtureKeyV3_t pk;
        if(RB_FireVFixtureV3KeyForPool(&s_fireV07Pool[slot],&pk)&&RB_FireVFixtureV3KeyEqual(&ek,&pk))return slot;}
    return -1;
}

'''
assert s.count(marker)==1; s=s.replace(marker,helpers+marker,1)

# Copy source identity whenever an anchor/cat creates a pool.
anchor_assign='''\t\t\t\tpool->latchedFlameSurface = s_fireV07Anchors[anchor].surfaceIndex;
\t\t\t\tVectorCopy(s_fireV07Anchors[anchor].origin, pool->latchedFlameOrigin);
\t\t\t\tQ_strncpyz(pool->latchedShader, s_fireV07Anchors[anchor].shaderName, sizeof(pool->latchedShader));
\t\t\t\tpool->latchedAtMs = nowMs;
'''
anchor_new=anchor_assign+'''\t\t\t\tpool->latchedPrimitive = s_fireV07Anchors[anchor].primitive;
\t\t\t\tpool->latchedEntityNum = s_fireV07Anchors[anchor].entityNum;
\t\t\t\tpool->latchedShaderIndex = s_fireV07Anchors[anchor].shaderIndex;
\t\t\t\tQ_strncpyz(pool->latchedModelName, s_fireV07Anchors[anchor].modelName, sizeof(pool->latchedModelName));
'''
s=rep(s,anchor_assign,anchor_new,'pass2 anchor identity')

anchor2='''\t\t\t\tpool->latchedFlameSurface = anchor->surfaceIndex;
\t\t\t\tVectorCopy(anchor->origin, pool->latchedFlameOrigin);
\t\t\t\tQ_strncpyz(pool->latchedShader, anchor->shaderName, sizeof(pool->latchedShader));
\t\t\t\tpool->latchedAtMs = nowMs;
'''
anchor2new=anchor2+'''\t\t\t\tpool->latchedPrimitive = anchor->primitive;
\t\t\t\tpool->latchedEntityNum = anchor->entityNum;
\t\t\t\tpool->latchedShaderIndex = anchor->shaderIndex;
\t\t\t\tQ_strncpyz(pool->latchedModelName, anchor->modelName, sizeof(pool->latchedModelName));
'''
s=rep(s,anchor2,anchor2new,'pass2b anchor identity')

catalog='''\t\t\t\t\tpool->latchedFlameSurface = entry->surfaceIndex;
\t\t\t\t\tVectorCopy(entry->origin, pool->latchedFlameOrigin);
\t\t\t\t\tQ_strncpyz(pool->latchedShader, catalogShader, sizeof(pool->latchedShader));
\t\t\t\t\tpool->latchedAtMs = nowMs;
'''
catalog_new=catalog+'''\t\t\t\t\tpool->latchedPrimitive = FIREVOL_PRIM_WORLD;
\t\t\t\t\tpool->latchedEntityNum = REFENTITYNUM_WORLD;
\t\t\t\t\tpool->latchedShaderIndex = entry->shaderIndex;
\t\t\t\t\tQ_strncpyz(pool->latchedModelName, "<world>", sizeof(pool->latchedModelName));
'''
s=rep(s,catalog,catalog_new,'pass2c world identity')

# Refresh moving fixture owners before reacquisition/used-anchor bookkeeping.
a='''\t\tfor (slot = 0; slot < MAX_DLIGHTS; ++slot)
\t\t\tfallbackOwnerUsed[slot] = qfalse;

\t\t// Pass 1: reacquire registry entries.'''
b='''\t\tfor (slot = 0; slot < MAX_DLIGHTS; ++slot)
\t\t\tfallbackOwnerUsed[slot] = qfalse;

\t\t/* V3: one moving physical fixture updates one registry owner instead of leaving
\t\t * old latched positions behind (the Chateau secret fireplace case). */
\t\tRB_FireVFixtureV3RefreshRegistry();

\t\t// Pass 1: reacquire registry entries.'''
s=rep(s,a,b,'refresh before pass1')

# Prevent a second synthetic admission for a known owner.
a='''\t\t\tif (!RB_FireV082SyntheticAnchorEligible(anchor))
\t\t\t\tcontinue;
\t\t\tif (RB_FireV082AnchorSpatiallyCovered(anchor, 32.0f))
'''
b='''\t\t\tif (!RB_FireV082SyntheticAnchorEligible(anchor))
\t\t\t\tcontinue;
\t\t\tif (RB_FireVFixtureV3FindPoolForAnchor(anchor) >= 0)
\t\t\t\tcontinue;
\t\t\tif (RB_FireV082AnchorSpatiallyCovered(anchor, 32.0f))
'''
s=rep(s,a,b,'anchor owner admission guard')
a='''\t\t\t\tif (RB_FireVFinalPoolForCatalog(entry) >= 0)
\t\t\t\t\tcontinue;
\t\t\t\tif (RB_FireVStableDistanceWeight(entry->origin) <= 0.001f)
'''
b='''\t\t\t\tif (RB_FireVFinalPoolForCatalog(entry) >= 0)
\t\t\t\t\tcontinue;
\t\t\t\tif (RB_FireVFixtureV3FindPoolForCatalogSurface(entry->surfaceIndex) >= 0)
\t\t\t\t\tcontinue;
\t\t\t\tif (RB_FireVStableDistanceWeight(entry->origin) <= 0.001f)
'''
s=rep(s,a,b,'catalog owner admission guard')

# Dedup helper after stable-resident clear, where resident eviction API is available.
marker='static float RB_FireVStableCandidatePriority(FBO_t *srcFbo, int poolSlot,\n'
dedup=r'''static int s_fireVFixtureV3SuppressedTotal=0;

static int RB_FireVFixtureV3Rank(const fireVolumetricV07PoolSlot_t *p,int liveIndex,qboolean liveSynthetic)
{
    if(!p||!p->valid)return -1;
    if(liveIndex>=0)return 500+(p->sourceClass==FIREVOL082_SOURCE_STRICT?20:0)+(p->nativeOrdinal>=0?10:0);
    if(liveSynthetic)return 300;
    if(p->sourceClass!=FIREVOL082_SOURCE_SYNTHETIC)return 200;
    return 100;
}

static void RB_FireVFixtureV3Drop(int slot,int *liveIndex,int *liveShadowSlot,qboolean *liveSynthetic,qboolean *renderChosen)
{
    int r;
    if(slot<0||slot>=FIREVOL07_MAX_POOL)return;
    r=RB_FireVStableResidentIndexForPool(slot);
    if(r>=0)RB_FireVStableClearResident(r);
    memset(&s_fireV07Pool[slot],0,sizeof(s_fireV07Pool[slot]));
    liveIndex[slot]=-1;liveShadowSlot[slot]=-1;liveSynthetic[slot]=qfalse;renderChosen[slot]=qfalse;
    s_fireV07PoolChangeCount++;
}

static int RB_FireVFixtureV3Dedup(int *liveIndex,int *liveShadowSlot,qboolean *liveSynthetic,qboolean *renderChosen)
{
    fireVolumetricFixtureKeyV3_t keys[FIREVOL07_MAX_POOL];
    int winners[FIREVOL07_MAX_POOL],groups=0,slot,g,dropped=0;
    if(!r_dwFireVolFixtureV3||!r_dwFireVolFixtureV3->integer)return 0;
    for(g=0;g<FIREVOL07_MAX_POOL;++g){memset(&keys[g],0,sizeof(keys[g]));winners[g]=-1;}
    for(slot=0;slot<FIREVOL07_MAX_POOL;++slot){
        fireVolumetricFixtureKeyV3_t k; int rank,wr;
        if(!RB_FireVFixtureV3KeyForPool(&s_fireV07Pool[slot],&k))continue;
        for(g=0;g<groups&&!RB_FireVFixtureV3KeyEqual(&k,&keys[g]);++g){}
        if(g==groups){keys[groups]=k;winners[groups++]=slot;continue;}
        rank=RB_FireVFixtureV3Rank(&s_fireV07Pool[slot],liveIndex[slot],liveSynthetic[slot]);
        wr=RB_FireVFixtureV3Rank(&s_fireV07Pool[winners[g]],liveIndex[winners[g]],liveSynthetic[winners[g]]);
        if(rank>wr)winners[g]=slot;
        else if(rank==wr&&s_fireV07Pool[slot].createdMs<s_fireV07Pool[winners[g]].createdMs)winners[g]=slot;
    }
    for(slot=0;slot<FIREVOL07_MAX_POOL;++slot){
        fireVolumetricFixtureKeyV3_t k;
        if(!RB_FireVFixtureV3KeyForPool(&s_fireV07Pool[slot],&k))continue;
        for(g=0;g<groups&&!RB_FireVFixtureV3KeyEqual(&k,&keys[g]);++g){}
        if(g<groups&&winners[g]!=slot){RB_FireVFixtureV3Drop(slot,liveIndex,liveShadowSlot,liveSynthetic,renderChosen);dropped++;}
    }
    s_fireVFixtureV3SuppressedTotal+=dropped;
    return dropped;
}

'''
assert s.count(marker)==1; s=s.replace(marker,dedup+marker,1)

# Per-function diag clock/counters.
s=rep(s,'\tstatic int lastResidencyDiagMs = 0;\n',
      '\tstatic int lastResidencyDiagMs = 0;\n\tstatic int lastFixtureV3DiagMs = 0;\n',
      'diag clock')
s=rep(s,'\tint v084VisibleFixtureHolds = 0;\n',
      '\tint v084VisibleFixtureHolds = 0;\n\tint fixtureV3DroppedFrame = 0;\n',
      'diag counter')

# Hard dedup before residency. This is intentionally after real/synthetic reacquire/admission
# so winner selection can prefer current real DLight.
marker='\t\t// Production v1 Pass 3: persistent eight-slot active residency. Existing owners are retained;\n'
insert='''\t\t/* Fixture V3 architectural boundary: one source-aware physical fixture before
\t\t * stable residency and before synthetic shadow-cache hint publication. */
\t\tfixtureV3DroppedFrame += RB_FireVFixtureV3Dedup(liveIndex,liveShadowSlot,liveSynthetic,renderChosen);

'''
assert s.count(marker)==1;s=s.replace(marker,insert+marker,1)

# Geometry: small torch 205 -> ~113 geometry radius; large fireplace 410 -> 220.
# Physical attenuation/cubemap radius remains unchanged.
old='\ttarget = Com_Clamp(minRadius, maxRadius, rawRadius);\n'
new='''\tif(r_dwFireVolFixtureV3&&r_dwFireVolFixtureV3->integer&&r_dwFireVolGeometryScale&&r_dwFireVolGeometryMin) {
\t\tfloat compactMin=Com_Clamp(64.0f,180.0f,r_dwFireVolGeometryMin->value);
\t\tfloat compactScale=Com_Clamp(0.25f,1.0f,r_dwFireVolGeometryScale->value);
\t\ttarget=Com_Clamp(compactMin,maxRadius,rawRadius*compactScale);
\t} else target = Com_Clamp(minRadius, maxRadius, rawRadius);
'''
# There are two geometry radius functions. Replace both.
assert s.count(old)==2,('geometry target count',s.count(old));s=s.replace(old,new,2)

# Runtime selected-owner telemetry: meaningful local state, not all 128 registry entries.
marker='\tif (s_rVolumetricFireDiag && s_rVolumetricFireDiag->integer &&\n'
diag=r'''	if(r_dwFireVolFixtureDiag&&r_dwFireVolFixtureDiag->integer&&
		(lastFixtureV3DiagMs==0||nowMs-lastFixtureV3DiagMs>=1000))
	{
		fireVolumetricFixtureKeyV3_t seen[FIREVOL081_RENDER_CAP];
		int seenCount=0,unknown=0,real=0,synth=0,si;
		for(si=0;si<selectedCount;++si){
			fireVolumetricV07Selection_t *sv=&selected[si];
			fireVolumetricV07PoolSlot_t *pp=(sv->poolSlot>=0&&sv->poolSlot<FIREVOL07_MAX_POOL)?&s_fireV07Pool[sv->poolSlot]:NULL;
			fireVolumetricFixtureKeyV3_t k;int q,known=RB_FireVFixtureV3KeyForPool(pp,&k)?1:0;
			if(sv->syntheticVolumeOnly)synth++;else real++;
			if(!known)unknown++;
			else{for(q=0;q<seenCount&&!RB_FireVFixtureV3KeyEqual(&k,&seen[q]);++q){} if(q==seenCount&&seenCount<FIREVOL081_RENDER_CAP)seen[seenCount++]=k;}
			if(pp)ri.Printf(PRINT_ALL,
				"FIREVOL_FIXTURE_V3_SLOT map=%s selectedIndex=%d pool=%d keyKind=%d keyA=%d keyB=%d primitive=%d entity=%d surface=%d sourceClass=%d synthetic=%d origin=%.1f,%.1f,%.1f geometryRadius=%.1f\n",
				tr.world?tr.world->baseName:"<none>",si,sv->poolSlot,known?k.kind:0,known?k.a:0,known?k.b:0,
				pp->latchedPrimitive,pp->latchedEntityNum,pp->latchedFlameSurface,pp->sourceClass,
				sv->syntheticVolumeOnly?1:0,pp->latchedFlameOrigin[0],pp->latchedFlameOrigin[1],pp->latchedFlameOrigin[2],
				pp->radiusStateValid?pp->radiusStateValue:0.0f);
		}
		ri.Printf(PRINT_ALL,
			"FIREVOL_FIXTURE_V3 map=%s selectedPhysical=%d unknownSelected=%d realSelected=%d syntheticSelected=%d duplicatesSuppressed=%d duplicatesSuppressedTotal=%d selected=%d rendered=%d geometryScale=%.2f geometryMin=%.0f\n",
			tr.world?tr.world->baseName:"<none>",seenCount,unknown,real,synth,fixtureV3DroppedFrame,
			s_fireVFixtureV3SuppressedTotal,selectedCount,renderedCount,
			r_dwFireVolGeometryScale?r_dwFireVolGeometryScale->value:1.0f,
			r_dwFireVolGeometryMin?r_dwFireVolGeometryMin->value:96.0f);
		lastFixtureV3DiagMs=nowMs;
	}

'''
# V07 contains multiple old diag markers in V1; insert before the final one inside V07.
v7start=s.index('static void RB_VolumetricFireV07(')
v7end=s.index('\n\nstatic void RB_VolumetricFire(',v7start)
v7=s[v7start:v7end]
assert v7.count(marker)>=1,('v7 diag markers',v7.count(marker))
pos=v7.rfind(marker);v7=v7[:pos]+diag+v7[pos:];s=s[:v7start]+v7+s[v7end:]

p.write_text(s)

proof={
 'version':'DarkWolf FireVol Fixture Owner V3 TEST',
 'base_run':42011094909,
 'requested_base_run':41982135692,
 'v2_carried_forward':False,
 'fixes':[
  'world IFLC owner API rejects non-world indices',
  'BMODEL/model/entity owners use primitive+entity+shader identity',
  'moving owner refreshes one registry latch instead of leaving old positions',
  'one physical fixture before residency/shadow-cache',
  'compact fire geometry scales raw radius without changing direct light/cubemap radius'],
 'defaults':{'r_dwFireVolFixtureV3':1,'r_dwFireVolGeometryScale':0.55,'r_dwFireVolGeometryMin':96},
 'sha256':{p:H(p) for p in ['tr_backend.c','tr_iflc.inc','tr_init.c','tr_local.h']}}
(ev/'FIREVOL_FIXTURE_V3_SOURCE_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
print('FIREVOL_FIXTURE_V3_APPLIED',json.dumps(proof,sort_keys=True))
