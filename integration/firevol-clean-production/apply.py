#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1])
p=root/"tr_backend.c"
s=p.read_text()

old="""#define FIREVOL_V6_BMODEL_PLUME_Z_OFFSET 12.0f
"""
new="""#define FIREVOL_V6_BMODEL_PLUME_Z_OFFSET 12.0f
// CLEAN PRODUCTION: fireplace-specific visual alignment.
// Keep Crypt1/world-torch offset unchanged; only the two Chateau fireplace classes differ.
#define FIREVOL_PROD_STATIC_FIREPLACE_PLUME_Z_OFFSET 10.0f
#define FIREVOL_PROD_BMODEL_PLUME_Z_OFFSET 2.0f
"""
if old not in s:
    raise SystemExit("production constants anchor not found")
s=s.replace(old,new,1)

old="""\t\tVectorCopy(sel->latchedFlameOrigin,renderVolumeOrigin);
\t\tif (pool && pool->latchedPrimitive==FIREVOL_PRIM_WORLD) renderVolumeOrigin[2]-=FIREVOL_V5_WORLD_PLUME_Z_OFFSET;
\t\telse if (pool && pool->latchedPrimitive==FIREVOL_PRIM_BMODEL && RB_FireV5BmodelHoldActive(pool,nowMs))
\t\t\trenderVolumeOrigin[2]-=FIREVOL_V6_BMODEL_PLUME_Z_OFFSET;
"""
new="""\t\tVectorCopy(sel->latchedFlameOrigin,renderVolumeOrigin);
\t\tif (pool && pool->latchedPrimitive==FIREVOL_PRIM_WORLD) {
\t\t\tif (pool->fireV6StaticFireplaceStable)
\t\t\t\trenderVolumeOrigin[2]-=FIREVOL_PROD_STATIC_FIREPLACE_PLUME_Z_OFFSET;
\t\t\telse
\t\t\t\trenderVolumeOrigin[2]-=FIREVOL_V5_WORLD_PLUME_Z_OFFSET;
\t\t} else if (pool && pool->latchedPrimitive==FIREVOL_PRIM_BMODEL && RB_FireV5BmodelHoldActive(pool,nowMs)) {
\t\t\trenderVolumeOrigin[2]-=FIREVOL_PROD_BMODEL_PLUME_Z_OFFSET;
\t\t}
"""
if old not in s:
    raise SystemExit("production render-origin anchor not found")
s=s.replace(old,new,1)

old='''\t\tri.Printf(PRINT_ALL,"FIREVOL_CONTINUITY_V6 map=%s staticFireplaceSuppressed=%d staticFireplaceSuppressedTotal=%d staticFireplaceRawMin=%.0f staticFireplaceRadius=%.0f bmodelPlumeZOffset=-%.0f selected=%d rendered=%d\\n",
\t\t\ttr.world?tr.world->baseName:"<none>",continuityV6StaticFireplaceDroppedFrame,s_fireV6StaticFireplaceSuppressedTotal,
\t\t\tFIREVOL_V6_STATIC_FIREPLACE_RAW_RADIUS_MIN,FIREVOL_V6_STATIC_FIREPLACE_COMPANION_RADIUS,
\t\t\tFIREVOL_V6_BMODEL_PLUME_Z_OFFSET,selectedCount,renderedCount);
'''
new='''\t\tri.Printf(PRINT_ALL,"FIREVOL_CONTINUITY_V6 map=%s staticFireplaceSuppressed=%d staticFireplaceSuppressedTotal=%d staticFireplaceRawMin=%.0f staticFireplaceRadius=%.0f bmodelPlumeZOffset=-%.0f selected=%d rendered=%d\\n",
\t\t\ttr.world?tr.world->baseName:"<none>",continuityV6StaticFireplaceDroppedFrame,s_fireV6StaticFireplaceSuppressedTotal,
\t\t\tFIREVOL_V6_STATIC_FIREPLACE_RAW_RADIUS_MIN,FIREVOL_V6_STATIC_FIREPLACE_COMPANION_RADIUS,
\t\t\tFIREVOL_PROD_BMODEL_PLUME_Z_OFFSET,selectedCount,renderedCount);
\t\tri.Printf(PRINT_ALL,"FIREVOL_CLEAN_PRODUCTION map=%s staticFireplaceZ=-%.0f movingBmodelZ=-%.0f worldTorchZ=-%.0f selected=%d rendered=%d\\n",
\t\t\ttr.world?tr.world->baseName:"<none>",FIREVOL_PROD_STATIC_FIREPLACE_PLUME_Z_OFFSET,
\t\t\tFIREVOL_PROD_BMODEL_PLUME_Z_OFFSET,FIREVOL_V5_WORLD_PLUME_Z_OFFSET,selectedCount,renderedCount);
'''
if old not in s:
    raise SystemExit("production diagnostic anchor not found")
s=s.replace(old,new,1)

p.write_text(s)

# Clean Production must never enable diagnostic overlays by default.
import re
pinit=root/"tr_init.c"
si=pinit.read_text()
for name in ("r_dwFireVolContinuityDiag","r_dwFireVolFixtureDiag"):
    pat=re.compile(r'(ri\.Cvar_Get\(\s*"' + re.escape(name) + r'"\s*,\s*)"[^"]+"')
    si,n=pat.subn(r'\1"0"',si,count=1)
    if n!=1:
        raise SystemExit("production diagnostic default anchor not found: "+name)
pinit.write_text(si)

# Emit the relevant defaults into build proof.
for line in si.splitlines():
    if any(k in line for k in (
        "r_dwFireVolFlashFix","r_dwFireVolWarmupGuard","r_dwFireVolEnergyGuard",
        "r_dwFireVolFLCFade","r_dwFireVolFixtureV3","r_dwFireVolFixtureDiag",
        "r_dwFireVolContinuityV4","r_dwFireVolContinuityDiag",
        "r_dwFireVolWorldGeometryScale","r_dwFireVolIFLCPriority")):
        print("PROD_DEFAULT:",line.strip())

print("PASS Clean Production fireplace alignment patch")
