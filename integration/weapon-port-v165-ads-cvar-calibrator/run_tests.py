#!/usr/bin/env python3
from pathlib import Path
import sys,json
if len(sys.argv)<2: raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)
cg=(root/"SP/code/cgame/cg_weapons.c").read_text(encoding="utf-8")
cm=(root/"SP/code/cgame/cg_main.c").read_text(encoding="utf-8")
gd=(root/"SP/code/cgame/cg_draw.c").read_text(encoding="utf-8")
gw=(root/"SP/code/game/g_weapon.c").read_text(encoding="utf-8")
names=[
"cg_dwAdsDebug",
"cg_dwAdsMP40Right","cg_dwAdsMP40Up","cg_dwAdsMP40Forward",
"cg_dwAdsMP40Pitch","cg_dwAdsMP40Yaw","cg_dwAdsMP40Roll",
"cg_dwAdsStenRight","cg_dwAdsStenUp","cg_dwAdsStenForward",
"cg_dwAdsStenPitch","cg_dwAdsStenYaw","cg_dwAdsStenRoll"
]
checks={
 "marker":"DARKWOLF_WEAPON_PORT_V165_ADS_CVAR_CALIBRATOR" in cg and "DARKWOLF_WEAPON_PORT_V165_ADS_CVAR_CALIBRATOR" in cm,
 "all_cvars_registered":all(('trap_Cvar_Register( NULL, "'+n+'"') in cm for n in names),
 "archive_flags":cm.count("CVAR_ARCHIVE") >= 13,
 "renderer_pos_reads":"CG_DWADSReadPosForWeapon( weaponNum, cal )" in cg,
 "renderer_ang_reads":"CG_DWADSReadAngForWeapon( ps->weapon, ang )" in cg,
 "debug_reads_cvar":'CG_DWADSReadFloat( "cg_dwAdsDebug" )' in cg,
 "wrapper_sets_cvar":'trap_Cvar_Set( "cg_dwAdsMP40Right", a );' in cg and 'trap_Cvar_Set( "cg_dwAdsStenPitch", a );' in cg,
 "debug_crosshair_preserved":"CG_DWADSDebugCrosshair()" in gd,
 "v163_ballistics_preserved":"DARKWOLF_WEAPON_PORT_V163_ADS_BALLISTIC_ALIGNMENT" in gw and "spread = 0.0f;" in gw,
}
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V165_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
if bad: raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V165_TESTS_PASS",len(checks))
