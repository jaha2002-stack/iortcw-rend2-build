#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "source")/"SP"/"code"/"rend2"
inc=(root/"tr_lamp_control_v1.inc").read_text()
scene=(root/"tr_scene.c").read_text()

checks=[
 ("native resolver helper","R_DWLC11_FindBlockedNativeRuntimeDlight" in inc),
 ("production exact native resolver","R_StaticPromoteUSLRDFindNativeRuntimeDlight(light)" in inc),
 ("bounded fallback","const float maxDist = 96.0f;" in inc),
 ("ambiguity protection","const float ambiguityMargin = 18.0f;" in inc),
 ("authored native preferred","pass == 0 && !dl->nativeAuthoredDlight" in inc),
 ("blocked native tagged exact fixture",
  "blocked->staticPromoteFixtureId = light->candidate.entityOrdinal;" in scene),
 ("no intensity-only native block","blocked->radius = 0.0f;" not in scene),
 ("no color-only native block","VectorClear(blocked->color);" not in scene),
 ("promoted exact veto","dl->staticPromoteFixtureId >= 0" in inc and
                         "!R_DWLC1_FixtureIdEnabled(dl->staticPromoteFixtureId)" in inc),
 ("synthetic owner veto","dl->physicalElectricOwnerId > 0" in inc and
                          "!R_DWLC1_FixtureIdEnabled(dl->physicalElectricOwnerId)" in inc),
 ("old ternary removed","physicalElectricOwnerId >= 0 ?" not in inc),
 ("native ordinal diagnostic","nativeOrdinal=%d" in inc),
 ("hard array compaction","tr.refdef.num_dlights = out;" in inc),
 ("tail cleared","memset(&tr.refdef.dlights[i], 0, sizeof(tr.refdef.dlights[i]));" in inc),
 ("staticpromote gating preserved","allowed && !R_DWLC1_FixtureEnabled(light)" in scene),
 ("owner assignment before hard filter",
  scene.find("R_DarkWolfAssignPhysicalElectricOwnerIds();") >= 0 and
  scene.find("R_DWLC1_FilterDisabledSceneDlights") >
  scene.find("R_DarkWolfAssignPhysicalElectricOwnerIds();")),
]
bad=[n for n,ok in checks if not ok]
if bad:
    raise SystemExit("Lamp Control V1.1 tests failed: "+", ".join(bad))
print("DW_LAMP_CONTROL_V11_STATIC_TESTS_PASS",len(checks))
