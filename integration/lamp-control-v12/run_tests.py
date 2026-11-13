#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "source")/"SP"/"code"/"rend2"
lc=(root/"tr_lamp_control_v1.inc").read_text()
v12=(root/"tr_lamp_control_v12.inc").read_text()
scene=(root/"tr_scene.c").read_text()

checks=[
 ("fresh v12 registry",'DW_LC1_FILE "darkwolf_lamp_control_v12.txt"' in lc),
 ("old registry ignored",'DW_LC1_FILE "darkwolf_lamp_control_v1.txt"' not in lc),
 ("old cone picker removed from lamp command",
  "return R_DWLC12_PickExact(forwardOut, lateralOut);" in lc and
  "R_StaticPromoteFindCrosshairFixture(&forwardDistance" not in lc),
 ("helper after IFLC ELSS",
  '#include "tr_iflc.inc"\n#include "tr_elss.inc"\n#include "tr_lamp_control_v12.inc"' in scene),
 ("real runtime dlight gate","R_DWLC12_RuntimeLampDlight" in v12),
 ("fire excluded","dl->iflcOptIn || dl->fireVolumetricSource || dl->transientBlast" in v12),
 ("stable id mapping","dl->staticPromoteFixtureId" in v12 and "dl->physicalElectricOwnerId" in v12),
 ("surface hit","R_ELSS_FirstHit(hitPoint, &hitSurface, &hitDistance)" in v12),
 ("visibility guard","R_IFLC_LineVisible(s_iflcViewOrigin, light->candidate.origin)" in v12),
 ("512 max distance","forward > 512.0f" in v12),
 ("ELSS strict ray","strictRadius = 10.0f + forward * 0.035f" in v12),
 ("housing proximity","hitRadius = MIN(128.0f, MAX(56.0f, radius * 0.45f + 16.0f))" in v12),
 ("disabled repickable","if (!active[i] && !disabled)" in v12),
 ("class rejected not selectable","Active real DLight OR our own disabled fixture" in v12),
 ("ambiguity refuses mutation","ambiguous crosshair" in v12 and "return NULL;" in v12),
 ("V11 hard filter preserved","R_DWLC11_FindBlockedNativeRuntimeDlight" in lc),
 ("hard dlight compaction preserved","tr.refdef.num_dlights = out;" in lc),
]
bad=[name for name,ok in checks if not ok]
if bad:
    raise SystemExit("Lamp Control V1.2 tests failed: "+", ".join(bad))
print("DW_LAMP_CONTROL_V12_STATIC_TESTS_PASS",len(checks))
