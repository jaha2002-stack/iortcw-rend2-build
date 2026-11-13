#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "source")/"SP"/"code"
r=(root/"rend2/tr_destructible_lights_v1.inc").read_text()
g=(root/"game/g_destructible_lights_v1.inc").read_text()

checks=[
    ("renderer exact registry build","R_StaticPromoteBuildPersistentRegistry()" in r),
    ("renderer exact crosshair picker","R_StaticPromoteFindCrosshairFixture(&forwardDistance, &lateralDistance)" in r),
    ("old custom picker removed","cone = MAX(30.0f, along * 0.12f)" not in r),
    ("exact bind proof","DW_DLV13 BOUND EXACT" in r),
    ("map reload safety","s_dwDlv1LoadedMap" in r),
    ("switch uses G_SetAngle","G_SetAngle(e,angles);" in g),
    ("old unsynced angle copy removed","VectorCopy(angles,e->s.angles);" not in g),
    ("switch forced network visible","SVF_NOCLIENT" in g and "EF_NODRAW" in g),
    ("surface normal offset","VectorMA(tr.endpos,1.50f,normal,origin);" in g),
]
bad=[name for name,ok in checks if not ok]
if bad: raise SystemExit("V1.3 checks failed: "+", ".join(bad))
print("DW_DESTRUCTIBLE_LIGHTS_V13_STATIC_TESTS_PASS",len(checks))
