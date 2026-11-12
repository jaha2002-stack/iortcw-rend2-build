#!/usr/bin/env python3
from pathlib import Path
import sys,json
if len(sys.argv)<2: raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)
cg=(root/"SP/code/cgame/cg_weapons.c").read_text(encoding="utf-8")
cm=(root/"SP/code/cgame/cg_main.c").read_text(encoding="utf-8")
cl=(root/"SP/code/cgame/cg_local.h").read_text(encoding="utf-8")
gw=(root/"SP/code/game/g_weapon.c").read_text(encoding="utf-8")

names=[
"cg_dwAdsDebug",
"cg_dwAdsMP40Right","cg_dwAdsMP40Up","cg_dwAdsMP40Forward",
"cg_dwAdsMP40Pitch","cg_dwAdsMP40Yaw","cg_dwAdsMP40Roll",
"cg_dwAdsStenRight","cg_dwAdsStenUp","cg_dwAdsStenForward",
"cg_dwAdsStenPitch","cg_dwAdsStenYaw","cg_dwAdsStenRoll"
]
checks={
 "marker":"DARKWOLF_WEAPON_PORT_V166_FINAL_ADS_TRANSFORM_CALIBRATOR" in cm,
 "vmcvar_globals":all(("vmCvar_t "+n+";") in cm for n in names),
 "vmcvar_externs":all(("extern vmCvar_t "+n+";") in cl for n in names),
 "cvar_table":all(('&'+n+', "'+n+'"') in cm for n in names),
 "no_null_registration":'trap_Cvar_Register( NULL, "cg_dwAdsMP40Pitch"' not in cm,
 "direct_pos_values":"cg_dwAdsStenUp.value" in cg and "cg_dwAdsMP40Forward.value" in cg,
 "direct_ang_values":"cg_dwAdsStenPitch.value" in cg and "cg_dwAdsMP40Yaw.value" in cg,
 "final_rotation_helper":"CG_DWADSApplyFinalGunRotation" in cg,
 "final_rotation_after_position":'CG_PositionEntityOnTag( &gun, parent, "tag_weapon", 0, NULL );\n\t\t\tCG_DWADSApplyFinalGunRotation( &gun, weaponNum, ads );' in cg,
 "early_rotation_removed":'angles[PITCH] += ang[0] * ads;' not in cg,
 "debug_direct":"return cg_dwAdsDebug.integer ? qtrue : qfalse;" in cg,
 "v163_ballistics":"DARKWOLF_WEAPON_PORT_V163_ADS_BALLISTIC_ALIGNMENT" in gw and "spread = 0.0f;" in gw,
}
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V166_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
if bad: raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V166_TESTS_PASS",len(checks))
