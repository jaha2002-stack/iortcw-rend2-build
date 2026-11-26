#!/usr/bin/env python3
"""Bounded diagnostic color grade invariants, not a substitute for GPU runtime."""
from pathlib import Path
import hashlib
import math
import random
import sys
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
shader = (root / "SP/code/rend2/glsl/dwfinal_fp.glsl").read_text()
backend = (root / "SP/code/rend2/tr_backend.c").read_text()
glslc = (root / "SP/code/rend2/tr_glsl.c").read_text()
checks = {
    "SP/code/rend2/tr_backend.c": "7ca9c750f5490ba5327cb7a53df152d7368f09714249d8734a53abed113e9fc9",
    "SP/code/rend2/tr_glsl.c": "e1a85265122a8ed793615656ae417c41554e778d9584d442e62122d7572fa51e",
    "SP/code/rend2/glsl/dwfinal_fp.glsl": "c73a6366552bea1ec98501071e6325cd93b965475a3afbe21df4ebd53f104e3f",
}
for name, expected in checks.items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    assert actual == expected, (name, actual, expected)
assert "texture2D(u_LevelsMap" not in shader
assert "sampler2D u_LevelsMap" not in shader
assert shader.count("texture2D(") == 9
assert "VectorSet4(parms, cas, lut, (float)lutIndex, 0.0f);" in backend
assert "GL_BindToTMU(lut > 0.0f" not in backend
assert "DARKWOLF_LUT_V05_PROCEDURAL_ACTIVE" in glslc
assert 'Q_stricmp(name, "dwfinal")' in glslc
assert "return clamp(graded, v * 0.90, min(v * 1.10, vec3(1.0)));" in shader

def grade(rgb, mode):
    v = [max(0.0, min(1.0, float(x))) for x in rgb]
    if mode == 0:
        return v
    y = sum(a*b for a, b in zip(v, (0.2126, 0.7152, 0.0722)))
    shadow = max(0.0, min(1.0, (0.70-y)*2.0))
    hi = 1.0-shadow
    q = v[:]
    if mode == 1:
        q[0] *= 1.0+0.055*hi-0.012*shadow
        q[1] *= 1.0+0.008*shadow
        q[2] *= 1.0+0.045*shadow-0.045*hi
    else:
        q[0] *= 1.0-0.038*shadow+0.010*hi
        q[1] *= 1.0+0.006*shadow
        q[2] *= 1.0+0.052*shadow-0.016*hi
    new_y = sum(a*b for a, b in zip(q, (0.2126, 0.7152, 0.0722)))
    if y > 1e-6 and new_y > 1e-6:
        q = [x*y/new_y for x in q]
    return [max(x*0.90, min(min(x*1.10, 1.0), z)) for x, z in zip(v, q)]

rng = random.Random(4262)
samples = [(0,0,0), (1,1,1), (1,0,0), (0,1,0), (0,0,1)]
samples += [(r/15.0, g/15.0, b/15.0) for r in range(16) for g in range(16) for b in range(16)]
samples += [(rng.random(), rng.random(), rng.random()) for _ in range(25000)]
worst = 0.0
for rgb in samples:
    before = sum(a*b for a,b in zip(rgb,(0.2126,0.7152,0.0722)))
    for mode in range(3):
        q = grade(rgb, mode)
        assert all(math.isfinite(x) and 0.0 <= x <= 1.0 for x in q)
        if mode == 0:
            assert q == list(rgb)
        else:
            for original, result in zip(rgb, q):
                assert original*0.90-1e-9 <= result <= min(original*1.10, 1.0)+1e-9
                if original == 0.0: assert result == 0.0
            after = sum(a*b for a,b in zip(q,(0.2126,0.7152,0.0722)))
            worst = max(worst, abs(before-after))
            assert abs(before-after) < 0.035
print("LUT_V05_ANALYTIC_GPU_ATLAS_BYPASS_STATIC_PASS samples=%d worst_luminance_error=%.6f" %(len(samples),worst))
