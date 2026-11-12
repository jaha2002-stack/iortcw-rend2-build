#!/usr/bin/env python3
from pathlib import Path
import sys,json,re
if len(sys.argv)<2: raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)
s=(root/"SP/code/game/ai_cast_fight.c").read_text(encoding="utf-8")

weaps=[
"WP_DW_MP44","WP_DW_PPSH","WP_DW_MP34","WP_DW_BAR","WP_DW_TT33",
"WP_DW_DUAL_TT33","WP_DW_REVOLVER","WP_DW_HDM","WP_DW_MOSIN",
"WP_DW_M1GARAND","WP_DW_G43","WP_DW_M97","WP_DW_BROWNING","WP_DW_MG42M"
]
start=s.index("float AICast_GetWeaponSoundRange")
end=s.index("qboolean AICast_StopAndAttack",start)
fn=s[start:end]
checks={
 "marker":"DARKWOLF_WEAPON_PORT_V162_SP_FIRE_SOUND_RANGE_SAFETY" in s,
 "record_bounds_guard":"lastWeaponFiredWeaponNum >= MAX_WEAPONS" in s,
 "all_imported_ids_in_sound_switch":all(("case    "+w+":") in fn for w in weaps),
 "fatal_default_retained_for_truly_unknown":"AICast_GetWeaponSoundRange: unknown weapon index" in fn,
 "mp44_covered":"case    WP_DW_MP44:" in fn,
 "ppsh_covered":"case    WP_DW_PPSH:" in fn,
 "id34_45_covered":all(("case    "+w+":") in fn for w in weaps[2:]),
}
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V162_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
if bad: raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V162_TESTS_PASS",len(checks))
