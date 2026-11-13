#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "source")/"SP"/"code"
g=(root/"game/g_destructible_lights_v1.inc").read_text()
r=(root/"rend2/tr_destructible_lights_v1.inc").read_text()
c=(root/"cgame/cg_ents.c").read_text()

checks=[
 ("switch network marker","DW_DLV14_SWITCH_MAGIC" in g and "e->s.density = DW_DLV14_SWITCH_MAGIC" in g),
 ("lamp network marker","DW_DLV14_LAMP_MAGIC" in g and "e->s.density=DW_DLV14_LAMP_MAGIC" in g),
 ("switch state networked","e->s.effect2Time = on ? 1 : 0" in g),
 ("visual state update","DW_Lights_UpdateVisualStates(circuit);" in g),
 ("proxy exact fixture","e->s.otherEntityNum2=fixtureId;" in g),
 ("proxy surface normal","VectorMA(tr.endpos,2.0f,normal,origin);" in g and "G_SetAngle(e,angles);" in g),
 ("dead exact id",'Com_sprintf(value,sizeof(value),"id:%d",self->s.otherEntityNum2);' in g),
 ("renderer exact dead id","Q_stricmpn(s,\"id:\",3)" in r and "R_DLV1_FixtureDead(light)" in r),
 ("cgame direct switch","trap_R_RegisterModel(path)" in c and "CG_DLV14_CustomGeneral" in c),
 ("cgame modelindex bypass","if (CG_DLV14_CustomGeneral(cent))" in c),
 ("switch guaranteed fallback","ent.reType=RT_SPRITE;" in c and "cgs.media.whiteShader" in c),
 ("visual markers broadcast","SVF_BROADCAST" in g),
 ("lamp off mask","darkwolf/dlv14_lamp_off" in c and "!s1->effect2Time" in c),
]
bad=[n for n,ok in checks if not ok]
if bad:
    raise SystemExit("V1.4 tests failed: "+", ".join(bad))
print("DW_DESTRUCTIBLE_LIGHTS_V14_STATIC_TESTS_PASS",len(checks))
