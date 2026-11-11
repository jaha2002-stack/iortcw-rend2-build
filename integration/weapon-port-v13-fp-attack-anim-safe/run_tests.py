#!/usr/bin/env python3
from pathlib import Path
import sys,json,re
if len(sys.argv)<2: raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)
cg=(root/"SP/code/cgame/cg_weapons.c").read_text(encoding="utf-8")
gw=(root/"SP/code/game/g_weapon.c").read_text(encoding="utf-8")
pm=(root/"SP/code/game/bg_pmove.c").read_text(encoding="utf-8")

checks={
 "marker":"DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE" in cg,
 "mp44_safe_frame":'( ps->weapon == WP_DW_MP44 ) ? 0 : 8' in cg,
 "both_new_weapons_guard":"ps->weapon == WP_DW_MP44 || ps->weapon == WP_DW_PPSH" in cg,
 "all_fire_anims":"WEAP_ATTACK1 || dwAnim == WEAP_ATTACK2 || dwAnim == WEAP_ATTACK_LASTSHOT" in cg,
 "freezes_old_and_new_frame":"hand.oldframe = dwSafeFrame;" in cg and "hand.frame = dwSafeFrame;" in cg,
 "zero_backlerp":"hand.backlerp = 0.0f;" in cg,
 "runtime_marker":'DW_WEAPON_PORT_V13_FP_ATTACK_SAFE weapon=%d anim=%d frame=%d' in cg,
 "v12_still_present":"DARKWOLF_WEAPON_PORT_V12_FIRE_SAFE" in cg,
 "server_fire_intact":"case WP_DW_MP44:" in gw and "case WP_DW_PPSH:" in gw and "Bullet_Fire" in gw,
 "pm_attack_state_intact":"case WP_DW_MP44:" in pm and "case WP_DW_PPSH:" in pm and "PM_ContinueWeaponAnim( weapattackanim )" in pm,
}
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
if bad: raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE_TESTS_PASS",len(checks))
