#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "source")/"SP"/"code"
checks={
  "game/g_destructible_lights_v1.inc":[
    "DARKWOLF_DESTRUCTIBLE_LIGHTS_V11",
    'DW_DLV11_SWITCH_FILE "darkwolf_switches_v11.txt"',
    "trap_FS_FOpenFile",
    "trap_FS_Write",
    "tr.plane.normal",
    "vectoangles(r->normal,angles)",
    "toggle_on.md3","toggle_off.md3",
    "knife_on.md3","knife_off.md3",
    "rotary_on.md3","rotary_off.md3",
    "savegame_loading",
    "DW_Lights_SaveSwitchRegistry",
    "DW_Lights_LoadSwitchRegistry",
    "DW_Lights_RemoveSwitch",
    "DW_Lights_ListSwitches",
  ],
  "cgame/cg_destructible_lights_v1.inc":[
    "DARKWOLF_DESTRUCTIBLE_LIGHTS_V11",
    "dw_switch_remove","dw_switch_list",
    "toggle|knife|rotary"
  ],
  "cgame/cg_consolecmds.c":[
    '{ "dw_switch_remove", CG_DWSwitchRemove_f }',
    '{ "dw_switch_list", CG_DWSwitchList_f }'
  ]
}
for rel,needles in checks.items():
    p=root/rel
    if not p.exists(): raise SystemExit("missing "+rel)
    s=p.read_text()
    for n in needles:
        if n not in s: raise SystemExit(f"missing {n!r} in {rel}")

g=(root/"game/g_destructible_lights_v1.inc").read_text()
for legacy in ("electronics/phone.md3","electronics/loudspeaker2.md3"):
    if legacy in g: raise SystemExit("legacy placeholder model remains: "+legacy)

if "VectorMA(tr.endpos,0.75f,normal,origin)" not in g:
    raise SystemExit("surface-normal offset missing")
if "DW_Lights_SpawnSwitchRecord(&s_dwSwitchPersist[i])" not in g:
    raise SystemExit("map restart restore path missing")

print("DW_DESTRUCTIBLE_LIGHTS_V11_STATIC_TESTS_PASS",sum(map(len,checks.values())))
