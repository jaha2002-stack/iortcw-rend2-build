#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1])
b=(root/"tr_backend.c").read_text()

required=[
    "DARKWOLF_FIREVOL_CRYPT1_SLOT6_REANCHOR_V1",
    "RB_FireV07NameLooksBurnScorchDecal",
    'RB_FireV07ContainsToken(name, "/decals/")',
    'RB_FireV07ContainsToken(name, "burn")',
    'RB_FireV07ContainsToken(name, "scorch")',
    "if (RB_FireV07NameLooksBurnScorchDecal(name))",
]
for x in required:
    assert x in b, x

# Production flame families and prior weapon-stream exclusion must remain.
for x in [
    '"fire", "flame", "torch", "blaze", "burn", "ember", "flamethrower", NULL',
    "RB_FireV085NameLooksWeaponStream(name)",
    'strstr(shaderName, "xflame")',
    'strstr(shaderName, "torch_ember")',
]:
    assert x in b, x

# Existing stricter synthetic/fallback safety remains present.
assert "Never synthesize from generic scorch/burn decals" in b
assert "burn/scorch decals can no longer create DLight-backed entries" in b

# Scope lock: the patch changes classification only; it must not change render budget,
# geometry radius parameters, Crypt1/Chateau offsets, IFLC gain, or shadow cache logic.
for x in [
    "#define FIREVOL081_RENDER_CAP 8",
    "RB_FireVStableGeometryRadius",
    "FIREVOL_PROD_STATIC_FIREPLACE_PLUME_Z_OFFSET 10.0f",
    "FIREVOL_PROD_BMODEL_PLUME_Z_OFFSET 72.0f",
    "FIREVOL_PROD_CHATEAU_FIREPLACE_GAIN 1.35f",
    "RB_IFLC_FireVolumeGain",
    "RB_FireVolProductionFindCachedShadow",
]:
    assert x in b, x

# Static sanity model of the intended classifier delta.
def blocked(name):
    n=name.lower()
    decal=("/decals/" in n or "decals/" in n)
    return decal and ("burn" in n or "scorch" in n)

assert blocked("textures/decals/burnm_01a")
assert blocked("textures/decals/scorch_01")
assert not blocked("textures/sfx/xflame1")
assert not blocked("models/mapobjects/torch/torch_ember")
assert not blocked("textures/liquids/fire_pool")

print("PASS Crypt1 Slot6 Reanchor V1 regression gates")
