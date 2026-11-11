#!/usr/bin/env python3
from pathlib import Path
import sys, json, hashlib

MARK="DARKWOLF_WEAPON_PORT_V11_HD_MODEL_LIMIT"

if len(sys.argv) < 2:
    raise SystemExit("usage: apply.py <source-root> [evidence-dir]")

root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True, exist_ok=True)

p=root/"SP/code/qcommon/qfiles.h"
before=p.read_text(encoding="utf-8")
if MARK in before:
    print("already applied")
    raise SystemExit(0)

s=before
repls=[
    ("#define SHADER_MAX_VERTEXES 4000",
     "#define SHADER_MAX_VERTEXES 16384 // "+MARK+": supports RealRTCW HD weapon surfaces"),
    ("#define MD3_MAX_TRIANGLES   8192    // per surface",
     "#define MD3_MAX_TRIANGLES   16384   // per surface - "+MARK),
    ("#define MD3_MAX_VERTS       4096    // per surface",
     "#define MD3_MAX_VERTS       16384   // per surface - "+MARK),
]
for old,new in repls:
    if s.count(old)!=1:
        raise SystemExit(f"anchor mismatch for {old!r}: {s.count(old)}")
    s=s.replace(old,new,1)

p.write_text(s,encoding="utf-8")
proof={
    "feature":"DarkWolf Weapon Port V1.1 HD Model Limit",
    "base_run":42975214092,
    "base_sha":"9c63be6044274e393016761633f5e3f80faa2964",
    "shader_max_vertexes_old":4000,
    "shader_max_vertexes_new":16384,
    "md3_max_verts_old":4096,
    "md3_max_verts_new":16384,
    "md3_max_triangles_old":8192,
    "md3_max_triangles_new":16384,
    "asset_requirements":{
        "mp44_v_mp44_max_verts":10241,
        "mp44_v_mp44_triangles":12255,
        "mp44_3rd_verts":5867,
        "ppsh_v_ppsh_max_verts":7920,
        "ppsh_v_ppsh_triangles":8399,
        "ppsh_3rd_verts":5631
    },
    "before_sha256":hashlib.sha256(before.encode()).hexdigest(),
    "after_sha256":hashlib.sha256(s.encode()).hexdigest()
}
(ev/"DW_WEAPON_PORT_V11_HD_MODEL_LIMIT_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V11_HD_MODEL_LIMIT_APPLY_PASS")
