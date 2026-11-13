#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "source")/"SP"/"code"
c=(root/"cgame/cg_ents.c").read_text()

checks=[
 ("vfs probe","CG_DLV16_VfsBytes" in c and "trap_FS_FOpenFile" in c),
 ("custom model bytes diagnostic","DW_DLV16 SWITCH_ASSET" in c and "vfsBytes=%d" in c),
 ("stock model fallback","DW_DLV16_StockSwitchFallback" in c and "SWITCH_STOCK_FALLBACK" in c),
 ("toggle stock fallback","models/mapobjects/electronics/alarmbox.md3" in c),
 ("knife stock fallback","models/mapobjects/electronics/phone.md3" in c),
 ("rotary stock fallback","models/mapobjects/electronics/loudspeaker2.md3" in c),
 ("lamp loose tga probe",'CG_DLV16_VfsBytes("gfx/darkwolf/dlv14_lamp_off.tga")' in c),
 ("lamp direct tga registration",'trap_R_RegisterShaderNoMip("gfx/darkwolf/dlv14_lamp_off.tga")' in c),
 ("lamp diagnostic","DW_DLV16 LAMP_OFF_ASSET" in c),
 ("ceiling mask enlarged",'? 10.0f : 10.0f' in c),
 ("dark stock mask fallback","ent.shaderRGBA[0]=22" in c and "ent.shaderRGBA[3]=240" in c),
 ("v15 snapshot marker preserved","DW_DLV15 SWITCH_SNAPSHOT" in c and "DW_DLV15 LAMP_SNAPSHOT" in c),
]
bad=[n for n,ok in checks if not ok]
if bad:
    raise SystemExit("V1.6 tests failed: "+", ".join(bad))
print("DW_DESTRUCTIBLE_LIGHTS_V16_STATIC_TESTS_PASS",len(checks))
