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
pub=(root/"SP/code/game/bg_public.h").read_text(encoding="utf-8")
checks={
 "marker":"DARKWOLF_WEAPON_PORT_V12_FIRE_SAFE" in cg,
 "ids_preserved":re.search(r"WP_DW_MP44,\s*//\s*32",pub) is not None and re.search(r"WP_DW_PPSH,\s*//\s*33",pub) is not None and re.search(r"WP_NUM_WEAPONS\s*//\s*34",pub) is not None,
 "mp44_server_bullet":"case WP_DW_MP44:" in gw and "DW_MP44_SPREAD" in gw and "DW_MP44_DAMAGE" in gw,
 "ppsh_server_bullet":"case WP_DW_PPSH:" in gw and "DW_PPSH_SPREAD" in gw and "DW_PPSH_DAMAGE" in gw,
 "attack_animation_groups":"case WP_DW_MP44:" in pm and "case WP_DW_PPSH:" in pm,
 "no_new_weapon_brass":cg.count("weaponInfo->ejectBrassFunc=NULL") >= 2,
 "no_new_weapon_muzzle_dlight":cg.count("VectorClear( weaponInfo->flashDlightColor ); // no shadowed muzzle dlight") == 2,
 "new_weapon_flash_suppressed":"weaponNum == WP_DW_MP44 || weaponNum == WP_DW_PPSH" in cg and "flash.hModel = 0;" in cg,
 "stock_safe_fire_audio":cg.count('weaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/mp40/mp40f1.wav");') >= 2,
 "standard_impact_group":re.search(r"case WP_MP40:\s*case WP_DW_MP44:\s*case WP_DW_PPSH:\s*case WP_FG42:",cg) is not None,
 "dormant_fire_proof":'DW_WEAPON_PORT_V12_FIRE weapon=%d' in gw and 'g_debugBullets.integer & 8' in gw,
}
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V12_FIRE_SAFE_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
if bad: raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V12_FIRE_SAFE_TESTS_PASS",len(checks))
