#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1])
p=root/"tr_backend.c"
s=p.read_text()

def rep(old,new):
    global s
    if old not in s:
        raise SystemExit("V6 anchor not found: "+old[:100])
    s=s.replace(old,new,1)

rep(
"""\tqboolean fireV5BmodelLocalValid;
\tvec3_t fireV5BmodelLocalOrigin;
\tint fireV5BmodelHoldUntilMs;
\t// Production v1: radius stabilization belongs to fixture identity, never to a shared render-slot index.
""",
"""\tqboolean fireV5BmodelLocalValid;
\tvec3_t fireV5BmodelLocalOrigin;
\tint fireV5BmodelHoldUntilMs;
\t// DARKWOLF_FIREVOL_CHATEAU_FINAL_V6: one stable owner for a large static WORLD fireplace.
\tqboolean fireV6StaticFireplaceStable;
\t// Production v1: radius stabilization belongs to fixture identity, never to a shared render-slot index.
""")

rep(
"""#define FIREVOL_V5_BMODEL_MOVING_RADIUS 112.0f
#define FIREVOL_V5_WORLD_PLUME_Z_OFFSET 10.0f
""",
"""#define FIREVOL_V5_BMODEL_MOVING_RADIUS 112.0f
#define FIREVOL_V5_WORLD_PLUME_Z_OFFSET 10.0f
// DARKWOLF_FIREVOL_CHATEAU_FINAL_V6: final narrow corrections.
#define FIREVOL_V6_STATIC_FIREPLACE_RAW_RADIUS_MIN 360.0f
#define FIREVOL_V6_STATIC_FIREPLACE_COMPANION_RADIUS 192.0f
#define FIREVOL_V6_BMODEL_PLUME_Z_OFFSET 12.0f
""")

rep("static int s_fireV4WorldSuppressedTotal=0;\n\nstatic qboolean RB_FireV4WorldNear",
    "static int s_fireV4WorldSuppressedTotal=0;\nstatic int s_fireV6StaticFireplaceSuppressedTotal=0;\n\nstatic qboolean RB_FireV4WorldNear")

anchor="static qboolean RB_FireV5BmodelNear(const fireVolumetricV07PoolSlot_t *a,\n"
func=r'''// DARKWOLF_FIREVOL_CHATEAU_FINAL_V6: consolidate large static WORLD fireplace companions.
static int RB_FireV6StaticFireplaceDedup(int *liveIndex,int *liveShadowSlot,
    qboolean *liveSynthetic,qboolean *renderChosen)
{
    int seed,slot,dropped=0;
    for(seed=0;seed<FIREVOL07_MAX_POOL;++seed){
        fireVolumetricV07PoolSlot_t *owner=&s_fireV07Pool[seed];
        const dlight_t *dl;
        int localDropped=0;
        if(!owner->valid||!owner->latchValid||owner->latchedPrimitive!=FIREVOL_PRIM_WORLD)continue;
        if(owner->sourceClass==FIREVOL082_SOURCE_SYNTHETIC)continue;
        if(liveIndex[seed]<0||liveIndex[seed]>=backEnd.refdef.num_dlights)continue;
        dl=&backEnd.refdef.dlights[liveIndex[seed]];
        if(RB_IFLC_BaseRadius(dl)<FIREVOL_V6_STATIC_FIREPLACE_RAW_RADIUS_MIN)continue;
        for(slot=0;slot<FIREVOL07_MAX_POOL;++slot){
            fireVolumetricV07PoolSlot_t *q=&s_fireV07Pool[slot];
            if(slot==seed||!q->valid||!q->latchValid||q->latchedPrimitive!=FIREVOL_PRIM_WORLD)continue;
            if(q->sourceClass!=FIREVOL082_SOURCE_SYNTHETIC)continue;
            if(!RB_FireV4WorldNear(owner,q,FIREVOL_V6_STATIC_FIREPLACE_COMPANION_RADIUS))continue;
            RB_FireVFixtureV3Drop(slot,liveIndex,liveShadowSlot,liveSynthetic,renderChosen);
            localDropped++; dropped++;
        }
        if(localDropped>0) owner->fireV6StaticFireplaceStable=qtrue;
    }
    s_fireV6StaticFireplaceSuppressedTotal+=dropped;
    return dropped;
}

'''
rep(anchor,func+anchor)

rep(
"""\t\tif (r_dwFireVolContinuityV4 && r_dwFireVolContinuityV4->integer && pool &&
\t\t\tpool->latchedPrimitive == FIREVOL_PRIM_WORLD && r_dwFireVolWorldGeometryScale)
\t\t\tcompactScale=Com_Clamp(0.25f,1.0f,r_dwFireVolWorldGeometryScale->value);
\t\tclampMin=compactMin;
\t\ttarget=Com_Clamp(compactMin,maxRadius,rawRadius*compactScale);
\t} else target = Com_Clamp(minRadius, maxRadius, rawRadius);
\tsmoothMs = Com_Clamp(50.0f, 3000.0f, s_rVolumetricFireRadiusSmoothMs->value);
""",
"""\t\tif (r_dwFireVolContinuityV4 && r_dwFireVolContinuityV4->integer && pool &&
\t\t\tpool->latchedPrimitive == FIREVOL_PRIM_WORLD && r_dwFireVolWorldGeometryScale)
\t\t\tcompactScale=Com_Clamp(0.25f,1.0f,r_dwFireVolWorldGeometryScale->value);
\t\tclampMin=compactMin;
\t\ttarget=Com_Clamp(compactMin,maxRadius,rawRadius*compactScale);
\t} else target = Com_Clamp(minRadius, maxRadius, rawRadius);
\tif(pool->fireV6StaticFireplaceStable && pool->radiusStateValid) target=pool->radiusStateValue;
\tsmoothMs = Com_Clamp(50.0f, 3000.0f, s_rVolumetricFireRadiusSmoothMs->value);
""")

rep(
"""\tint continuityV4DroppedFrame = 0, continuityV4WorldGroups = 0, continuityV4PriorityGroups = 0, continuityV4MovingFallbacks = 0;
\tint continuityV5BmodelDroppedFrame = 0;
""",
"""\tint continuityV4DroppedFrame = 0, continuityV4WorldGroups = 0, continuityV4PriorityGroups = 0, continuityV4MovingFallbacks = 0;
\tint continuityV5BmodelDroppedFrame = 0;
\tint continuityV6StaticFireplaceDroppedFrame = 0;
""")

rep(
"""\t\tfixtureV3DroppedFrame += RB_FireVFixtureV3Dedup(liveIndex,liveShadowSlot,liveSynthetic,renderChosen);
\t\tcontinuityV5BmodelDroppedFrame += RB_FireV5BmodelClusterDedup(liveIndex,liveShadowSlot,liveSynthetic,renderChosen);
\t\tcontinuityV4DroppedFrame += RB_FireV4WorldClusterDedup(liveIndex,liveShadowSlot,liveSynthetic,renderChosen,
""",
"""\t\tfixtureV3DroppedFrame += RB_FireVFixtureV3Dedup(liveIndex,liveShadowSlot,liveSynthetic,renderChosen);
\t\tcontinuityV5BmodelDroppedFrame += RB_FireV5BmodelClusterDedup(liveIndex,liveShadowSlot,liveSynthetic,renderChosen);
\t\tcontinuityV6StaticFireplaceDroppedFrame += RB_FireV6StaticFireplaceDedup(liveIndex,liveShadowSlot,liveSynthetic,renderChosen);
\t\tcontinuityV4DroppedFrame += RB_FireV4WorldClusterDedup(liveIndex,liveShadowSlot,liveSynthetic,renderChosen,
""")

rep(
"""\t\tVectorCopy(sel->latchedFlameOrigin,renderVolumeOrigin);
\t\tif (pool && pool->latchedPrimitive==FIREVOL_PRIM_WORLD) renderVolumeOrigin[2]-=FIREVOL_V5_WORLD_PLUME_Z_OFFSET;
""",
"""\t\tVectorCopy(sel->latchedFlameOrigin,renderVolumeOrigin);
\t\tif (pool && pool->latchedPrimitive==FIREVOL_PRIM_WORLD) renderVolumeOrigin[2]-=FIREVOL_V5_WORLD_PLUME_Z_OFFSET;
\t\telse if (pool && pool->latchedPrimitive==FIREVOL_PRIM_BMODEL && RB_FireV5BmodelHoldActive(pool,nowMs))
\t\t\trenderVolumeOrigin[2]-=FIREVOL_V6_BMODEL_PLUME_Z_OFFSET;
""")

rep(
"""\t\tri.Printf(PRINT_ALL,"FIREVOL_CONTINUITY_V5 map=%s bmodelSuppressed=%d bmodelCompanionRadius=%.0f bmodelHoldMs=%d movingFallbacks=%d worldPlumeZOffset=-%.0f selected=%d rendered=%d\\n",
\t\t\ttr.world?tr.world->baseName:"<none>",continuityV5BmodelDroppedFrame,FIREVOL_V5_BMODEL_COMPANION_RADIUS,
\t\t\tFIREVOL_V5_BMODEL_HOLD_MS,continuityV4MovingFallbacks,FIREVOL_V5_WORLD_PLUME_Z_OFFSET,selectedCount,renderedCount);
""",
"""\t\tri.Printf(PRINT_ALL,"FIREVOL_CONTINUITY_V5 map=%s bmodelSuppressed=%d bmodelCompanionRadius=%.0f bmodelHoldMs=%d movingFallbacks=%d worldPlumeZOffset=-%.0f selected=%d rendered=%d\\n",
\t\t\ttr.world?tr.world->baseName:"<none>",continuityV5BmodelDroppedFrame,FIREVOL_V5_BMODEL_COMPANION_RADIUS,
\t\t\tFIREVOL_V5_BMODEL_HOLD_MS,continuityV4MovingFallbacks,FIREVOL_V5_WORLD_PLUME_Z_OFFSET,selectedCount,renderedCount);
\t\tri.Printf(PRINT_ALL,"FIREVOL_CONTINUITY_V6 map=%s staticFireplaceSuppressed=%d staticFireplaceSuppressedTotal=%d staticFireplaceRawMin=%.0f staticFireplaceRadius=%.0f bmodelPlumeZOffset=-%.0f selected=%d rendered=%d\\n",
\t\t\ttr.world?tr.world->baseName:"<none>",continuityV6StaticFireplaceDroppedFrame,s_fireV6StaticFireplaceSuppressedTotal,
\t\t\tFIREVOL_V6_STATIC_FIREPLACE_RAW_RADIUS_MIN,FIREVOL_V6_STATIC_FIREPLACE_COMPANION_RADIUS,
\t\t\tFIREVOL_V6_BMODEL_PLUME_Z_OFFSET,selectedCount,renderedCount);
""")

p.write_text(s)
print("PASS FireVol Chateau Final V6 patch")
