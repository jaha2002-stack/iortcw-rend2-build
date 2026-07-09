#!/usr/bin/env python3
# Kit D v1.1 linker hotfix
# Fixes: multiple definition of r_dlightShadowShaderMode / Strength / Bias / etc.

from pathlib import Path
import re

CVAR_NAMES = [
    "r_dlightShadows",
    "r_dlightShadowMaxLights",
    "r_dlightShadowMapSize",
    "r_dlightShadowBias",
    "r_dlightShadowFilter",
    "r_dlightShadowDebug",
    "r_dlightShadowDebugEvery",
    "r_dlightShadowMinRadius",
    "r_dlightShadowMinIntensity",
    "r_dlightShadowDepthPass",
    "r_dlightShadowDepthFaces",
    "r_dlightShadowUseLightView",
    "r_dlightShadowNear",
    "r_dlightShadowFarScale",
    "r_dlightShadowShaderMode",
    "r_dlightShadowShaderStrength",
    "r_dlightShadowShaderBias",
    "r_dlightShadowShaderDebugScale",
    "r_dlightShadowShaderLog",
    "r_dlightShadowShaderLogEvery",
]

CVAR_DEFS = "\n".join([f"cvar_t *{n};" for n in CVAR_NAMES]) + "\n"

SETS = [
    (Path("SP/code/rend2/tr_init.c"), Path("SP/code/rend2/tr_local.h")),
    (Path("MP/code/rend2/tr_init.c"), Path("MP/code/rend2/tr_local.h")),
]

def load(p):
    return p.read_text(encoding="utf-8", errors="replace")

def save(p, s):
    p.write_text(s, encoding="utf-8")

def fix_header(local_path):
    s = load(local_path)

    # The critical fix: any Kit D cvar declaration in tr_local.h must be extern.
    for name in CVAR_NAMES:
        s = re.sub(
            rf"(?m)^\s*(?:extern\s+)?cvar_t\s*\*\s*{re.escape(name)}\s*;\s*$",
            f"extern cvar_t *{name};",
            s
        )

    # If some declarations were missing, add them near r_dlightMode extern.
    missing = [name for name in CVAR_NAMES if f"extern cvar_t *{name};" not in s]
    if missing:
        block = "\n".join([f"extern cvar_t *{name};" for name in missing]) + "\n"
        if "extern cvar_t *r_dlightMode;" in s:
            s = s.replace("extern cvar_t *r_dlightMode;", "extern cvar_t *r_dlightMode;\n" + block, 1)
        else:
            s += "\n" + block

    save(local_path, s)
    print(f"fixed header externs: {local_path}")

def fix_init(init_path):
    s = load(init_path)

    # Remove duplicate Kit D cvar definitions/declarations in tr_init.c only, then add exactly one block.
    for name in CVAR_NAMES:
        s = re.sub(rf"(?m)^\s*(?:extern\s+)?cvar_t\s*\*\s*{re.escape(name)}\s*;\s*$", "", s)

    if "cvar_t *r_dlightMode;" in s:
        s = s.replace("cvar_t *r_dlightMode;", "cvar_t *r_dlightMode;\n" + CVAR_DEFS, 1)
    else:
        includes = list(re.finditer(r"(?m)^\s*#include\s+.*$", s))
        if includes:
            pos = includes[-1].end()
            s = s[:pos] + "\n" + CVAR_DEFS + s[pos:]
        else:
            s = CVAR_DEFS + "\n" + s

    save(init_path, s)
    print(f"fixed single definitions in init: {init_path}")

def remove_accidental_defs_from_other_c_files(root, init_path):
    # Safety: if any accidental non-extern Kit D cvar definitions got inserted into other .c files, remove them.
    for cfile in root.glob("code/rend2/*.c"):
        if cfile == init_path:
            continue
        s = load(cfile)
        original = s
        for name in CVAR_NAMES:
            s = re.sub(rf"(?m)^\s*cvar_t\s*\*\s*{re.escape(name)}\s*;\s*$", "", s)
        if s != original:
            save(cfile, s)
            print(f"removed accidental cvar defs from: {cfile}")

for init_path, local_path in SETS:
    fix_header(local_path)
    fix_init(init_path)
    remove_accidental_defs_from_other_c_files(init_path.parents[2], init_path)

print("Kit D v1.1 linker hotfix completed.")
