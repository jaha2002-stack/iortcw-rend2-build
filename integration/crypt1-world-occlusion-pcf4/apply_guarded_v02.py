#!/usr/bin/env python3
"""Apply tested V01 PCF4 then conservative V02 occluder veto, and diagnostic SSGI guard."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from apply import apply
root=Path(sys.argv[1]);apply(root)
for rel in ("glsl/dlight_fp.glsl","glsl/lightall_fp.glsl"):
    f=root/"SP/code/rend2"/rel
    text=f.read_text()
    old="    return mix(mix(a00, a10, blend.x), mix(a01, a11, blend.x), blend.y);"
    new="""    // DARKWOLF_WORLD_OCCLUSION_PCF4_FAIL_CLOSED_V02
    float softened = mix(mix(a00, a10, blend.x), mix(a01, a11, blend.x), blend.y);
    float nearX = step(0.5, blend.x);
    float nearY = step(0.5, blend.y);
    float nearest = mix(mix(a00, a10, nearX), mix(a01, a11, nearX), nearY);
    return min(nearest, softened);"""
    assert text.count(old)==1,rel
    f.write_text(text.replace(old,new))
f=root/"SP/code/rend2/tr_backend.c"
text=f.read_text()
old="\t\tif (r_ssgi && r_ssgi->integer)"
new="\t\t// DARKWOLF_CRYPT1_LIGHTMAP_SSGI_ISOLATION_V1\n\t\tif (r_ssgi && r_ssgi->integer && !(r_lightmap && r_lightmap->integer))"
assert text.count(old)==1
f.write_text(text.replace(old,new))
print("GUARDED_V02_AND_SSGI_PATCH_PASS")
