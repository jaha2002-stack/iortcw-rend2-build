#!/usr/bin/env python3
from pathlib import Path
import math, sys

root=Path(sys.argv[1])
s=(root/"tr_backend.c").read_text()

required=[
    "DARKWOLF_FIREVOL_CHATEAU_FOLLOW_V5",
    "RB_FireV5WorldToEntityLocal",
    "RB_FireV5PredictBmodelPool",
    "RB_FireV5BmodelClusterDedup",
    "FIREVOL_V5_BMODEL_HOLD_MS 5000",
    "FIREVOL_V5_BMODEL_MOVING_WEIGHT 0.38f",
    "FIREVOL_V5_WORLD_PLUME_Z_OFFSET 10.0f",
    "FIREVOL_CONTINUITY_V5 map=%s",
]
for x in required:
    assert x in s, x

assert "#define FIREVOL081_RENDER_CAP 8" in s
assert "p->latchedPrimitive!=FIREVOL_PRIM_BMODEL" in s
assert "realConflict" in s
assert "renderVolumeOrigin[2]-=FIREVOL_V5_WORLD_PLUME_Z_OFFSET" in s
assert "VectorCopy(sel->latchedFlameOrigin, anchoredDl.origin)" in s
assert "RB_FireV5BmodelHoldActive(pool,nowMs)" in s
assert "bmodelDetached && bmodelMoving" in s

# Chateau V4 log: synthetic companion entity 5 remains close enough to the
# moving real owner entity 6 to be one physical fireplace group.
synthetic=(-1095.3,2601.3,393.7)
real_positions=[
    (-1083.0,2622.4,399.4),
    (-1083.0,2518.4,399.4),
    (-1084.3,2538.2,412.2),
]
for p in real_positions:
    d=math.sqrt(sum((a-b)**2 for a,b in zip(synthetic,p)))
    assert d < 112.0, d

# Crypt1 stays on the WORLD path; V5 does not raise the 8-source budget.
assert "latchedPrimitive!=FIREVOL_PRIM_BMODEL||b->latchedPrimitive!=FIREVOL_PRIM_BMODEL" in s
print("PASS FireVol Chateau V5 architecture checks")
