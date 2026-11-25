#!/usr/bin/env python3
"""Isolated, lamp-only fixed-phase experiment for Rend2 local volumetrics."""
from pathlib import Path
import hashlib, json, sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source")
shader = root / "SP/code/rend2/glsl/volumetriclocal_fp.glsl"
evidence = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("evidence")
text = shader.read_text(encoding="utf-8")
old = "float jitter = (stableVolumetricJitter(gl_FragCoord.xy) - 0.5) * jitterAmount;"
new = "// DW_LAMP_WAVE_CLEAN_V1: fixed sample phase for shadowed electric lamps only.\n    // Fire (modes 5..8), spotlight (4), and diagnostic modes retain the original jitter.\n    float jitter = (mode == 3) ? 0.0 : ((stableVolumetricJitter(gl_FragCoord.xy) - 0.5) * jitterAmount);"
if text.count(old) != 1:
    raise SystemExit(f"Expected exactly one original jitter expression, found {text.count(old)}")
# Snapshot the three explicitly protected files before changing the local shader.
protected = [
    root / "SP/code/rend2/glsl/volumetricsun_fp.glsl",
    root / "SP/code/rend2/glsl/volumetriclocal_upscale_fp.glsl",
    root / "SP/code/rend2/tr_backend.c",
]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
before = {p.name: sha(p) for p in protected}
shader.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
after = {p.name: sha(p) for p in protected}
assert before == after, (before, after)
evidence.mkdir(parents=True, exist_ok=True)
(evidence / "DW_LAMP_WAVE_CLEAN_V1_PROOF.json").write_text(json.dumps({
    "status": "STATIC_TEST_CANDIDATE",
    "changed_file": str(shader),
    "change": "mode 3 uses zero per-pixel raymarch jitter; all other modes keep original expression",
    "protected_files_sha256_before_after": before,
    "protected_files_unchanged": before == after,
    "sun_shader_modified": False,
    "fire_modes_5_to_8_modified": False,
    "backend_modified": False,
    "upscale_shader_modified": False
}, indent=2) + "\n", encoding="utf-8")
print("DW_LAMP_WAVE_CLEAN_V1_APPLY_PASS")
