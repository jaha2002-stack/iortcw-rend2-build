#!/usr/bin/env python3
from pathlib import Path
import sys,json,re
if len(sys.argv)<2: raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

pm=(root/"SP/code/game/bg_pmove.c").read_text(encoding="utf-8")
cg=(root/"SP/code/cgame/cg_weapons.c").read_text(encoding="utf-8")
misc=(root/"SP/code/game/bg_misc.c").read_text(encoding="utf-8")

checks={
 "v14_safety_present":"DARKWOLF_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY" in cg,
 "v13_freeze_absent":"DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE" not in cg,
 "reload_marker":"DARKWOLF_WEAPON_PORT_V15_RELOAD_RANGE_FIX" in pm,
 "reload_mp44_allowed":"weapon != WP_DW_MP44" in pm,
 "reload_ppsh_allowed":"weapon != WP_DW_PPSH" in pm,
 "reload_state_path":"PM_ContinueWeaponAnim( WEAP_RELOAD1 )" in pm and "WEAPON_RELOADING" in pm and "EV_FILL_CLIP" in pm,
 "reload_finish_path":"PM_ReloadClip( pm->ps->weapon )" in pm,
 "mp44_ammo_table":"WP_DW_MP44 / 32" in misc,
 "ppsh_ammo_table":"WP_DW_PPSH / 33" in misc,
 "full_effects_marker":"DARKWOLF_WEAPON_PORT_V15_FULL_EFFECTS_RELOAD_ADS_EYELINE" in cg,
 "mp44_custom_fire":'sound/weapons/mp44/mp44_fire.wav' in cg,
 "mp44_custom_far":'sound/weapons/mp44/mp44_far.wav' in cg,
 "mp44_custom_reload":'sound/weapons/mp44/mp44_reload.wav' in cg,
 "ppsh_custom_fire":'sound/weapons/ppsh/ppsh_fire.wav' in cg,
 "ppsh_custom_far":'sound/weapons/ppsh/ppsh_far.wav' in cg,
 "ppsh_custom_reload":'sound/weapons/ppsh/ppsh_reload.wav' in cg,
 "brass_restored":"weaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass" in cg,
 "dlight_restored":"MAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 )" in cg,
 "v12_flash_suppression_removed":"flash.hModel = 0;" not in cg[cg.find("DARKWOLF_WEAPON_PORT_V15_FULL_EFFECTS_RELOAD_ADS_EYELINE"):],
 "ads_marker":"DARKWOLF_WEAPON_PORT_V15_ADS_EYELINE" in cg,
 "ads_mp40_relief":"eyeRelief = ( weaponNum == WP_STEN ) ? 10.0f : 8.0f" in cg,
 "ads_bore_offset":"boreBelowEye = 1.25f" in cg,
}
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V15_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n")
if bad: raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V15_TESTS_PASS",len(checks))
