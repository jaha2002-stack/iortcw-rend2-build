#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source")
ENTS = ROOT / "SP/code/cgame/cg_ents.c"
EFFECTS = ROOT / "SP/code/cgame/cg_effects.c"
MARK = "DARKWOLF_SPOTLIGHT_DEATH_LOCALVOL_SYNC_V445"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"ERROR {label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)

ents = ENTS.read_text(encoding="utf-8")
effects = EFFECTS.read_text(encoding="utf-8")

if MARK in ents:
    print("DarkWolf spotlight death/local-volumetric sync v4.4.5 already applied")
    raise SystemExit(0)

required_ents = [
    "DARKWOLF_LOCAL_VOLUMETRIC_V0_1",
    "DARKWOLF_REF_LOCALVOL_SPOTLIGHT",
    "CG_Spotlight( cent, color, cent->currentState.origin, normalized_direction, 999, 4096, 10, fov, 0 );",
    'trap_Cvar_VariableStringBuffer("r_volumetricLocal", localVolEnabled, sizeof(localVolEnabled));',
]
for marker in required_ents:
    if marker not in ents:
        raise SystemExit("ERROR cgame parent contract missing: " + marker)

# The retail spotlight lifecycle is authoritative: game/g_misc.c sets s.frame=1
# in spotlight_die(), and the original CG_Spotlight() immediately stops beam,
# impact light and flare when that state reaches cgame. Keep the DarkWolf
# local-volumetric bridge on exactly the same liveness predicate.
dead_gate = """\tif ( cent->currentState.frame == 1 ) {    // dead\n\t\treturn;\n\t}\n"""
if dead_gate not in effects:
    raise SystemExit("ERROR original CG_Spotlight dead-state gate missing")

old = """\t\t\ttrap_Cvar_VariableStringBuffer(\"r_volumetricLocal\", localVolEnabled, sizeof(localVolEnabled));\n\t\t\tif (localVolEnabled[0] == '1')\n"""
new = """\t\t\ttrap_Cvar_VariableStringBuffer(\"r_volumetricLocal\", localVolEnabled, sizeof(localVolEnabled));\n\t\t\t// DARKWOLF_SPOTLIGHT_DEATH_LOCALVOL_SYNC_V445\n\t\t\t// Match the original CG_Spotlight death gate: a broken ET_SPOTLIGHT_EF\n\t\t\t// must not keep submitting its data-only local-volumetric cone.\n\t\t\tif (cent->currentState.frame != 1 && localVolEnabled[0] == '1')\n"""
ents = replace_once(ents, old, new, "local-volumetric spotlight liveness gate")
ENTS.write_text(ents, encoding="utf-8")
print("Applied " + MARK)
