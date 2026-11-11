#!/usr/bin/env python3
from pathlib import Path
import re, sys, json

if len(sys.argv)<2:
    raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

s=(root/"SP/code/qcommon/qfiles.h").read_text(encoding="utf-8")
def val(name):
    m=re.search(r"#define\s+"+re.escape(name)+r"\s+(\d+)",s)
    if not m:
        raise SystemExit("missing "+name)
    return int(m.group(1))

shader=val("SHADER_MAX_VERTEXES")
indexes=val("SHADER_MAX_INDEXES") if re.search(r"#define\s+SHADER_MAX_INDEXES\s+\d+",s) else shader*6
md3v=val("MD3_MAX_VERTS")
md3t=val("MD3_MAX_TRIANGLES")

# Actual maxima audited from DW_RealRTCW_WeaponPort_V1_MP44_PPSh.pk3.
req_v=10241
req_t=12255
checks={
    "marker":"DARKWOLF_WEAPON_PORT_V11_HD_MODEL_LIMIT" in s,
    "shader_capacity":shader > req_v,
    "index_capacity":shader*6 > req_t*3,
    "md3_vertex_capacity":md3v > req_v,
    "md3_triangle_capacity":md3t > req_t,
    "chosen_shader_limit_is_16384":shader==16384,
    "chosen_md3_vert_limit_is_16384":md3v==16384,
    "chosen_md3_tri_limit_is_16384":md3t==16384,
}
for k,v in checks.items():
    if not v:
        raise SystemExit("FAIL "+k)
(ev/"DW_WEAPON_PORT_V11_HD_MODEL_LIMIT_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
print("DW_WEAPON_PORT_V11_HD_MODEL_LIMIT_TESTS_PASS",len(checks))
