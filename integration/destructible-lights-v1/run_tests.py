#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "source")/"SP"/"code"
checks={
"rend2/tr_scene.c":[
'#include "tr_destructible_lights_v1.inc"',
'R_DLV1_FixtureEnabled(light)',
'R_DLV1_FilterDisabledSceneDlights(&dlightDiagInjectedIndex)'
],
"rend2/tr_init.c":['dw_dlr_bind','dw_dlr_unbind','dw_dlr_list'],
"game/g_cmds.c":['g_destructible_lights_v1.inc','DW_Lights_ClientCommand','dw_light_switch'],
"game/g_main.c":['DW_Lights_InitMap();'],
"game/g_funcs.h":['DW_Lights_SwitchUse','DW_Lights_ProxyDie'],
"game/g_func_decs.h":['DW_Lights_SwitchUse','DW_Lights_ProxyDie'],
"cgame/cg_consolecmds.c":['cg_destructible_lights_v1.inc','dw_lamp_bind','dw_switch_add','dw_circuit'],
"rend2/tr_destructible_lights_v1.inc":['DW_DLV1_BIND_FILE','physicalElectricOwnerId','dw_dl_deadCount'],
"game/g_destructible_lights_v1.inc":['alarmbox.md3','phone.md3','loudspeaker2.md3','takedamage=qtrue']
}
for rel,needles in checks.items():
    p=root/rel
    if not p.exists(): raise SystemExit("missing "+rel)
    s=p.read_text()
    for n in needles:
        if n not in s: raise SystemExit(f"missing {n} in {rel}")
# hard safety: no budget increases or unrelated renderer shader edits.
scene=(root/"rend2/tr_scene.c").read_text()
if "DW_DLV1_MAX_CIRCUITS 16" in scene: raise SystemExit("include leaked into scene")
print("DW_DESTRUCTIBLE_LIGHTS_V1_STATIC_TESTS_PASS",sum(map(len,checks.values())))
