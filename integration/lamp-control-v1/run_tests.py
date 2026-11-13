#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "source") / "SP" / "code"
scene = (root / "rend2/tr_scene.c").read_text()
init = (root / "rend2/tr_init.c").read_text()
local = (root / "rend2/tr_local.h").read_text()
inc = (root / "rend2/tr_lamp_control_v1.inc").read_text()

checks = [
    ("renderer only include", '#include "tr_lamp_control_v1.inc"' in scene),
    ("persistent registry", 'DW_LC1_FILE "darkwolf_lamp_control_v1.txt"' in inc),
    ("exact persistent picker", "R_StaticPromoteFindCrosshairFixture" in inc),
    ("disabled remains pickable", "persistent fixture registry, not the current" in inc),
    ("promoted selection gated", "allowed && !R_DWLC1_FixtureEnabled(light)" in scene),
    ("physical owner precedes hard filter",
     scene.find("R_DarkWolfAssignPhysicalElectricOwnerIds();") >= 0 and
     scene.find("R_DWLC1_FilterDisabledSceneDlights") >
     scene.find("R_DarkWolfAssignPhysicalElectricOwnerIds();")),
    ("hard refdef compaction", "tr.refdef.num_dlights = out;" in inc),
    ("stale tail cleared", "memset(&tr.refdef.dlights[i], 0, sizeof(tr.refdef.dlights[i]));" in inc),
    ("physical owner alias used", "physicalElectricOwnerId >= 0" in inc),
    ("toggle command", 'ri.Cmd_AddCommand( "dw_lamp_toggle", R_DWLC1_Toggle_f );' in init),
    ("off command", 'ri.Cmd_AddCommand( "dw_lamp_off", R_DWLC1_Off_f );' in init),
    ("on command", 'ri.Cmd_AddCommand( "dw_lamp_on", R_DWLC1_On_f );' in init),
    ("list command", 'ri.Cmd_AddCommand( "dw_lamp_list", R_DWLC1_List_f );' in init),
    ("restore command", 'ri.Cmd_AddCommand( "dw_lamp_restore_all", R_DWLC1_RestoreAll_f );' in init),
    ("no switch code", "dw_switch" not in inc),
    ("no destruction proxy", "dw_destructible_lamp" not in inc and "ProxyDie" not in inc and "die=" not in inc),
    ("no cgame command prototypes", "CG_DW" not in local),
]

bad = [name for name, ok in checks if not ok]
if bad:
    raise SystemExit("DW Lamp Control V1 tests failed: " + ", ".join(bad))

print("DW_LAMP_CONTROL_V1_STATIC_TESTS_PASS", len(checks))
