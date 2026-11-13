#!/usr/bin/env python3
from pathlib import Path
import re,sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "source")/"SP"/"code"
g=(root/"game/g_destructible_lights_v1.inc").read_text()
c=(root/"cgame/cg_ents.c").read_text()
m=(root/"qcommon/msg.c").read_text()

checks=[
 ("protocol documents density 10-bit", re.search(r'NETF\(\s*density\s*\)\s*,\s*10',m) is not None),
 ("protocol effect3Time 32-bit", re.search(r'NETF\(\s*effect3Time\s*\)\s*,\s*32',m) is not None),
 ("game switch marker on effect3Time","e->s.effect3Time = DW_DLV14_SWITCH_MAGIC;" in g),
 ("game lamp marker on effect3Time","e->s.effect3Time=DW_DLV14_LAMP_MAGIC;" in g),
 ("density no longer used as marker","e->s.density = DW_DLV14_SWITCH_MAGIC;" not in g and "e->s.density=DW_DLV14_LAMP_MAGIC;" not in g),
 ("cgame switch checks effect3Time","s1->effect3Time == DW_DLV14_SWITCH_MAGIC" in c),
 ("cgame lamp checks effect3Time","s1->effect3Time == DW_DLV14_LAMP_MAGIC" in c),
 ("cgame no density magic checks","s1->density == DW_DLV14_SWITCH_MAGIC" not in c and "s1->density == DW_DLV14_LAMP_MAGIC" not in c),
 ("switch snapshot proof","DW_DLV15 SWITCH_SNAPSHOT" in c),
 ("lamp snapshot proof","DW_DLV15 LAMP_SNAPSHOT" in c),
 ("direct model path retained","trap_R_RegisterModel(path)" in c),
 ("lamp off shader retained","darkwolf/dlv14_lamp_off" in c),
 ("broadcast retained","SVF_BROADCAST" in g),
]
bad=[n for n,ok in checks if not ok]
if bad:
    raise SystemExit("V1.5 tests failed: "+", ".join(bad))
print("DW_DESTRUCTIBLE_LIGHTS_V15_STATIC_TESTS_PASS",len(checks))
