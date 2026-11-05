#!/usr/bin/env python3
from pathlib import Path
import math, sys

root=Path(sys.argv[1])
s=(root/"tr_backend.c").read_text()

required=[
    "DARKWOLF_FIREVOL_CHATEAU_FINAL_V6",
    "RB_FireV6StaticFireplaceDedup",
    "FIREVOL_V6_STATIC_FIREPLACE_RAW_RADIUS_MIN 360.0f",
    "FIREVOL_V6_STATIC_FIREPLACE_COMPANION_RADIUS 192.0f",
    "FIREVOL_V6_BMODEL_PLUME_Z_OFFSET 12.0f",
    "fireV6StaticFireplaceStable",
    "FIREVOL_CONTINUITY_V6 map=%s",
]
for x in required:
    assert x in s, x

assert "#define FIREVOL081_RENDER_CAP 8" in s
assert s.index("RB_FireV6StaticFireplaceDedup(liveIndex") < s.index("RB_FireV4WorldClusterDedup(liveIndex")
assert "q->sourceClass!=FIREVOL082_SOURCE_SYNTHETIC" in s
assert "owner->sourceClass==FIREVOL082_SOURCE_SYNTHETIC" in s
assert "RB_IFLC_BaseRadius(dl)<FIREVOL_V6_STATIC_FIREPLACE_RAW_RADIUS_MIN" in s
assert "RB_FireV5BmodelHoldActive(pool,nowMs)" in s
assert "renderVolumeOrigin[2]-=FIREVOL_V6_BMODEL_PLUME_Z_OFFSET" in s

# Chateau V5 log: the static fireplace has one real WORLD owner and five synthetic companions.
real=(-1247.5,320.0,69.1)
companions=[
    (-1247.5,448.0,69.1),
    (-1254.0,468.7,-6.0),
    (-1224.0,384.0,70.0),
    (-1293.3,392.4,-20.0),
    (-1254.0,299.3,-6.0),
]
for p in companions:
    d=math.sqrt(sum((a-b)**2 for a,b in zip(real,p)))
    assert d < 192.0, d

# Observed V5 compact geometry: Chateau real fireplace 183.0..186.5 at world scale 0.45,
# Crypt1 real WORLD sources 103.8..154.7. The raw-radius gate cleanly separates them.
assert 183.0/0.45 > 360.0
assert 154.7/0.45 < 360.0

# Moving Chateau BMODEL is far from the static fireplace and remains on the proven V5 path.
moving=(-167.0,966.1,71.4)
d=math.sqrt(sum((a-b)**2 for a,b in zip(real,moving)))
assert d > 1000.0

print("PASS FireVol Chateau Final V6 architecture checks")

# verifier-trigger-v2
