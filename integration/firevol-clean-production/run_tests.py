#!/usr/bin/env python3
from pathlib import Path
import re, sys

root=Path(sys.argv[1])
b=(root/"tr_backend.c").read_text()
init=(root/"tr_init.c").read_text()

required=[
    "FIREVOL_PROD_STATIC_FIREPLACE_PLUME_Z_OFFSET 10.0f",
    "FIREVOL_PROD_BMODEL_PLUME_Z_OFFSET 72.0f",\n    "FIREVOL_PROD_CHATEAU_FIREPLACE_GAIN 1.35f",
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
assert "renderVolumeOrigin[2]-=FIREVOL_PROD_BMODEL_PLUME_Z_OFFSET" in b\nassert "volumeGain *= FIREVOL_PROD_CHATEAU_FIREPLACE_GAIN" in b
assert "fireV5BmodelLocalOrigin" in b
assert "FIREVOL_V5_BMODEL_HOLD_MS 5000" in b

def cvar_default(name):
    for line in init.splitlines():
        if "ri.Cvar_Get" in line and ('"' + name + '"') in line:
            parts=line.split('"')
            assert len(parts) >= 4, line
            return parts[3]
    raise AssertionError("missing cvar registration: "+name)

# Production diagnostics are opt-in only.
assert cvar_default("r_dwFireVolContinuityDiag")=="0"
assert cvar_default("r_dwFireVolFixtureDiag")=="0"

# Accepted FireVol fixes must be active without any /exec test pack.
expected_on={
    "r_dwFireVolFlashFix":"1",
    "r_dwFireVolWarmupGuard":"1",
    "r_dwFireVolEnergyGuard":"1",
    "r_dwFireVolFLCFade":"1",
    "r_dwFireVolFixtureV3":"1",
    "r_dwFireVolContinuityV4":"1",
}
for name,val in expected_on.items():
    assert cvar_default(name)==val, f"{name} default={cvar_default(name)} expected={val}"

print("PASS Clean Production regression gates")

# clean-production-final-trigger

# final-production-trigger-2
