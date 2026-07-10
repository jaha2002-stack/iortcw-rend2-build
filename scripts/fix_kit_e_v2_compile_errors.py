#!/usr/bin/env python3
"""
Kit E v2.2 compile fix.

Fixes the v2.1 compile error:
    tr_init.c:1:1: error: unknown type name 'cvar_t'
    conflicting types for r_dlightDistance...

Cause:
E v2 cvar definitions were inserted before tr_init.c includes, so cvar_t was not
defined yet.  This script moves the real definitions after #include "tr_local.h"
and keeps only extern declarations in tr_local.h.

Also removes qglReadBuffer(GL_COLOR_ATTACHMENT0_EXT), which produced an implicit
declaration warning and is not needed for rendering the FBO color target.
"""

from pathlib import Path
import re

CVAR_NAMES = [
    "r_dlightDistanceMapSize",
    "r_dlightDistanceColorTest",
    "r_dlightDistanceSkipGeometry",
    "r_dlightDistanceDebug",
    "r_dlightDistanceBias",
    "r_dlightDistanceStrength",
]

SETS = [
    (Path("SP/code/rend2/tr_init.c"), Path("SP/code/rend2/tr_local.h"), Path("SP/code/rend2")),
    (Path("MP/code/rend2/tr_init.c"), Path("MP/code/rend2/tr_local.h"), Path("MP/code/rend2")),
]

def load(p):
    return p.read_text(encoding="utf-8", errors="replace")

def save(p, s):
    p.write_text(s, encoding="utf-8")

def remove_distance_cvar_lines(s):
    for name in CVAR_NAMES:
        s = re.sub(rf"(?m)^\s*(?:extern\s+)?cvar_t\s*\*\s*{re.escape(name)}\s*;\s*$", "", s)
    return s

def fix_local(local_path):
    s = load(local_path)

    # Remove every existing E v2 cvar line, whether extern or not, then add clean externs.
    s = remove_distance_cvar_lines(s)

    block = "\n".join([f"extern cvar_t *{name};" for name in CVAR_NAMES]) + "\n"

    if "extern cvar_t *r_dlightMode;" in s:
        s = s.replace("extern cvar_t *r_dlightMode;", "extern cvar_t *r_dlightMode;\n" + block, 1)
    else:
        s += "\n" + block

    save(local_path, s)
    print(f"Kit E v2.2: fixed extern declarations in {local_path}")

def insert_after_tr_local_include(s, block):
    # Best location: right after #include "tr_local.h"
    m = re.search(r'(?m)^#include\s+"tr_local\.h"\s*$', s)
    if m:
        return s[:m.end()] + "\n" + block + s[m.end():]

    # Fallback: after the last #include line.
    includes = list(re.finditer(r'(?m)^\s*#include\s+.*$', s))
    if includes:
        pos = includes[-1].end()
        return s[:pos] + "\n" + block + s[pos:]

    # Last resort: top of file, but this should not happen in tr_init.c.
    return block + "\n" + s

def fix_init(init_path):
    s = load(init_path)

    # Remove all bad/pre-existing E v2 cvar definitions/declarations.
    s = remove_distance_cvar_lines(s)

    block = "\n".join([f"cvar_t *{name};" for name in CVAR_NAMES]) + "\n"

    # Insert after tr_local.h include, where cvar_t is known.
    s = insert_after_tr_local_include(s, block)

    save(init_path, s)
    print(f"Kit E v2.2: fixed real definitions in {init_path}")

def fix_other_c_files(rend2_dir, init_path):
    for cfile in rend2_dir.glob("*.c"):
        if cfile == init_path:
            continue
        s = load(cfile)
        fixed = remove_distance_cvar_lines(s)

        # qglReadBuffer is not declared in this renderer build; remove it.
        fixed = re.sub(r'(?m)^\s*qglReadBuffer\s*\(\s*GL_COLOR_ATTACHMENT0_EXT\s*\)\s*;\s*$', "", fixed)

        if fixed != s:
            save(cfile, fixed)
            print(f"Kit E v2.2: cleaned {cfile}")

for init_path, local_path, rend2_dir in SETS:
    fix_local(local_path)
    fix_init(init_path)
    fix_other_c_files(rend2_dir, init_path)

print("Kit E v2.2 compile fix completed.")
