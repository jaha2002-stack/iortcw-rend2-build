#!/usr/bin/env python3
from pathlib import Path
import sys,json
if len(sys.argv)<2: raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

cg=(root/"SP/code/cgame/cg_weapons.c").read_text(encoding="utf-8")
cc=(root/"SP/code/cgame/cg_consolecmds.c").read_text(encoding="utf-8")
cl=(root/"SP/code/cgame/cg_local.h").read_text(encoding="utf-8")
cd=(root/"SP/code/cgame/cg_draw.c").read_text(encoding="utf-8")
gw=(root/"SP/code/game/g_weapon.c").read_text(encoding="utf-8")

checks={
 "marker":"DARKWOLF_WEAPON_PORT_V164_ADS_CALIBRATOR_ANGLE_DEBUG" in cg,
 "actual_weapon_first":"cg.predictedPlayerState.weapon" in cg and "CG_DWADSCurrentWeapon" in cg,
 "position_command":'"dw_ads_cal", CG_DWADSCal_f' in cc,
 "angle_command":'"dw_ads_ang", CG_DWADSAng_f' in cc,
 "debug_command":'"dw_ads_debug", CG_DWADSDebug_f' in cc,
 "angle_storage":"dwAdsAngMP40" in cg and "dwAdsAngSten" in cg,
 "angles_applied":"angles[PITCH] += (*ang)[0] * ads;" in cg and "angles[YAW]   += (*ang)[1] * ads;" in cg,
 "debug_crosshair":"CG_DWADSDebugCrosshair()" in cd,
 "reset_both":"VectorClear( *cal );" in cg and "VectorClear( *ang );" in cg,
 "prototypes":"CG_DWADSAng_f" in cl and "CG_DWADSDebugCrosshair" in cl,
 "v163_ballistics_preserved":"DARKWOLF_WEAPON_PORT_V163_ADS_BALLISTIC_ALIGNMENT" in gw and "spread = 0.0f;" in gw,
}
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V164_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
if bad: raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V164_TESTS_PASS",len(checks))
