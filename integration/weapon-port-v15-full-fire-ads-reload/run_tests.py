#!/usr/bin/env python3
from pathlib import Path
import sys,json,re
if len(sys.argv)<2: raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)
cg=(root/"SP/code/cgame/cg_weapons.c").read_text(encoding="utf-8")
pm=(root/"SP/code/game/bg_pmove.c").read_text(encoding="utf-8")
checks={
 "v14_component_index_fix_preserved":"animNumber = cent->pe.weap.animationNumber & ~ANIM_TOGGLEBIT;" in cg and "animNumber >= MAX_WP_ANIMATIONS" in cg,
 "v13_freeze_absent":"DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE" not in cg,
 "v15_marker":"DARKWOLF_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD" in cg and "DARKWOLF_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD" in pm,
 "mp44_fire_sound":'sound/weapons/mp44/mp44_fire.wav' in cg,
 "mp44_far_sound":'sound/weapons/mp44/mp44_far.wav' in cg,
 "mp44_reload_sound":'sound/weapons/mp44/mp44_reload.wav' in cg,
 "ppsh_fire_sound":'sound/weapons/ppsh/ppsh_fire.wav' in cg,
 "ppsh_far_sound":'sound/weapons/ppsh/ppsh_far.wav' in cg,
 "ppsh_reload_sound":'sound/weapons/ppsh/ppsh_reload.wav' in cg,
 "brass_restored":cg.count("weaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass;")>=2,
 "muzzle_dlight_restored":cg.count("MAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );")>=3,
 "v12_flash_suppression_removed":"flash.hModel = 0;" not in cg or "weaponNum == WP_DW_MP44 || weaponNum == WP_DW_PPSH" not in cg[cg.find("flash.hModel = 0;")-200:cg.find("flash.hModel = 0;")+200],
 "reload_gate_mp44":"weapon != WP_DW_MP44" in pm,
 "reload_gate_ppsh":"weapon != WP_DW_PPSH" in pm,
 "reload_animation_kept":"PM_ContinueWeaponAnim( WEAP_RELOAD1 );" in pm,
 "reload_moves_ammo":"PM_ReloadClip( pm->ps->weapon )" in pm,
 "ads_rear_sight":"rearSightBack" in cg and "sightPoint" in cg and "eyeClearance" in cg,
 "old_muzzle_center_ads_removed":"VectorSubtract(sight.origin,cg.refdef.vieworg,d)" not in cg,
}
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V15_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
if bad: raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V15_TESTS_PASS",len(checks))
