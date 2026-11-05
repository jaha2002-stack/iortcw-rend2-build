#!/usr/bin/env python3
from pathlib import Path
import re, sys

root=Path(sys.argv[1])
b=(root/"tr_backend.c").read_text()
init=(root/"tr_init.c").read_text()

required=[
    "FIREVOL_PROD_STATIC_FIREPLACE_PLUME_Z_OFFSET 4.0f",
    "FIREVOL_PROD_BMODEL_PLUME_Z_OFFSET 6.0f",
    "FIREVOL_CLEAN_PRODUCTION map=%s",
    "pool->fireV6StaticFireplaceStable",
    "RB_FireV5BmodelHoldActive(pool,nowMs)",
    "RB_FireV6StaticFireplaceDedup",
    "RB_FireV5BmodelClusterDedup",
    "RB_FireV4WorldClusterDedup",
]
for x in required:
    assert x in b, x

# Accepted budgets and Crypt1 behavior are preserved.
assert "#define FIREVOL081_RENDER_CAP 8" in b
assert "#define FIREVOL_V5_WORLD_PLUME_Z_OFFSET 10.0f" in b
assert "r_dwFireVolWorldGeometryScale" in b
assert "r_dwFireVolIFLCPriority" in b

# The static fireplace gets its own offset; normal WORLD torches retain -10.
assert "if (pool->fireV6StaticFireplaceStable)" in b
assert "renderVolumeOrigin[2]-=FIREVOL_PROD_STATIC_FIREPLACE_PLUME_Z_OFFSET" in b
assert "renderVolumeOrigin[2]-=FIREVOL_V5_WORLD_PLUME_Z_OFFSET" in b

# The moving BMODEL keeps V5 ownership/follow logic, only the final visual offset changes.
assert "renderVolumeOrigin[2]-=FIREVOL_PROD_BMODEL_PLUME_Z_OFFSET" in b
assert "fireV5BmodelLocalOrigin" in b
assert "FIREVOL_V5_BMODEL_HOLD_MS 5000" in b

# Production diagnostics must remain opt-in (default zero).
for name in ("r_dwFireVolContinuityDiag","r_dwFireVolFixtureDiag"):
    pos=init.find(name)
    assert pos>=0, name
    window=init[pos:pos+500]
    assert '"0"' in window, f"{name} default not zero"

print("PASS Clean Production regression gates")
