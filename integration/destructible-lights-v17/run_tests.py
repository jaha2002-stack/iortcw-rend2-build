#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "source")/"SP"/"code"
r=(root/"rend2/tr_destructible_lights_v1.inc").read_text()
g=(root/"game/g_destructible_lights_v1.inc").read_text()
c=(root/"cgame/cg_ents.c").read_text()
scene=(root/"rend2/tr_scene.c").read_text()

checks=[
 ("exact origin cvar created",'ri.Cvar_Get("dw_dl_lastOrigin", "0 0 0", 0);' in r),
 ("exact origin published",'ri.Cvar_Set("dw_dl_lastOrigin"' in r),
 ("off dlight array compacted","tr.refdef.num_dlights = out;" in r),
 ("removed dlight tail zeroed","memset(&tr.refdef.dlights[i], 0, sizeof(tr.refdef.dlights[i]));" in r),
 ("physical owner then off filter",
  scene.find("R_DarkWolfAssignPhysicalElectricOwnerIds();") >= 0 and
  scene.find("R_DLV1_FilterDisabledSceneDlights") >
  scene.find("R_DarkWolfAssignPhysicalElectricOwnerIds();")),
 ("staticpromote off gating","allowed && !R_DLV1_FixtureEnabled(light)" in scene),
 ("proxy exact origin networked","VectorCopy(exactOrigin,e->s.origin2);" in g),
 ("visual uses exact fixture origin","VectorCopy(s1->origin2,ent.origin);" in c),
 ("destroyed proxy retained","self->classname=\\"dw_destroyed_lamp\\";" in g),
 ("destroyed proxy no collision","self->r.contents=0;" in g and "self->clipmask=0;" in g),
 ("destroyed visual locked off","self->s.effect2Time=0;" in g),
 ("switch compact scale","? 0.64f : 0.24f;" in c),
 ("switch collision reduced","VectorSet(e->r.mins,-2,-7,-10);" in g),
 ("v16 real assets retained","DW_DLV16 SWITCH_ASSET" in c and "DW_DLV16 LAMP_OFF_ASSET" in c),
]
bad=[n for n,ok in checks if not ok]
if bad:
    raise SystemExit("V1.7 tests failed: "+", ".join(bad))
print("DW_DESTRUCTIBLE_LIGHTS_V17_STATIC_TESTS_PASS",len(checks))
