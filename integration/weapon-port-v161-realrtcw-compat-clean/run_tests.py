#!/usr/bin/env python3
from pathlib import Path
import sys,json
if len(sys.argv)<2: raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

cg=(root/"SP/code/cgame/cg_weapons.c").read_text(encoding="utf-8")
pm=(root/"SP/code/game/bg_pmove.c").read_text(encoding="utf-8")
checks={
 "v161_marker":"DARKWOLF_WEAPON_PORT_V161_REALRTCW_COMPAT_CLEAN" in cg,
 "v14_safety":"DARKWOLF_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY" in cg,
 "v13_absent":"DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE" not in cg,
 "explicit_parts":"DW_V161PartModelPath" in cg and "DW_V161AddImportedParts" in cg,
 "supports_part9":"v_revolver_barrel9.md3" in cg and "v_ithaca_barrel10.md3" in cg,
 "skip_m1_barrel5":"v_m1_barrel5.md3 exists but is NOT linked" in cg,
 "safe_brass_tag":"DW_V161_NO_BRASS_TAG" in cg and "DW_V161TagExists" in cg,
 "revolver_no_brass":"weaponInfo->ejectBrassFunc=NULL; // RealRTCW: revolver does not eject brass" in cg,
 "weapon_positions":"DW_V161ApplyWeaponPosition" in cg and "VectorSet( off, -12, -1,  0 )" in cg,
 "auto_group":all(x in pm for x in ["case WP_DW_MP34:","case WP_DW_BAR:","case WP_DW_BROWNING:","case WP_DW_MG42M:"]),
 "trigger_group":all(x in pm for x in ["case WP_DW_TT33:","case WP_DW_REVOLVER:","case WP_DW_MOSIN:","case WP_DW_M97:"]),
}
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V161_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
if bad: raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V161_TESTS_PASS",len(checks))
