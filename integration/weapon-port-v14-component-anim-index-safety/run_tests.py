#!/usr/bin/env python3
from pathlib import Path
import sys,json,re

if len(sys.argv)<2:
    raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")

root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

cg=(root/"SP/code/cgame/cg_weapons.c").read_text(encoding="utf-8")
gw=(root/"SP/code/game/g_weapon.c").read_text(encoding="utf-8")
pm=(root/"SP/code/game/bg_pmove.c").read_text(encoding="utf-8")

m=re.search(r'qboolean CG_GetPartFramesFromWeap\(.*?\n\}',cg,re.S)
if not m:
    raise SystemExit("FAIL no CG_GetPartFramesFromWeap")
fn=m.group(0)

checks={
    "marker":"DARKWOLF_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY" in fn,
    "mask_togglebit":"animNumber = cent->pe.weap.animationNumber & ~ANIM_TOGGLEBIT;" in fn,
    "hard_lower_bound":"animNumber < 0" in fn,
    "hard_upper_bound":"animNumber >= MAX_WP_ANIMATIONS" in fn,
    "safe_loop":"for ( i = 0; i < animNumber; i++ )" in fn,
    "raw_loop_removed":"for ( i = 0; i < cent->pe.weap.animationNumber; i++ )" not in fn,
    "array_access_inside_safe_loop":"wi->weapAnimations[i].moveSpeed" in fn and "wi->weapAnimations[i].numFrames" in fn,
    "v13_freeze_absent":"DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE" not in cg,
    "v12_fire_safe_present":"DARKWOLF_WEAPON_PORT_V12_FIRE_SAFE" in cg,
    "server_fire_intact":"case WP_DW_MP44:" in gw and "case WP_DW_PPSH:" in gw and "Bullet_Fire" in gw,
    "pm_attack_state_intact":"case WP_DW_MP44:" in pm and "case WP_DW_PPSH:" in pm and "PM_ContinueWeaponAnim( weapattackanim )" in pm,
}
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
if bad:
    raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY_TESTS_PASS",len(checks))
