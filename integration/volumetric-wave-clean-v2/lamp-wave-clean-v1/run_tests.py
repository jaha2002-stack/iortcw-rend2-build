#!/usr/bin/env python3
"""Static isolation tests for the lamp-only volumetric sample-phase experiment."""
from pathlib import Path
import hashlib, json, sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source")
evidence = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("evidence")
local = (root / "SP/code/rend2/glsl/volumetriclocal_fp.glsl").read_text(encoding="utf-8")
sun = root / "SP/code/rend2/glsl/volumetricsun_fp.glsl"
upscale = root / "SP/code/rend2/glsl/volumetriclocal_upscale_fp.glsl"
backend = root / "SP/code/rend2/tr_backend.c"
assert local.count("float jitter = (mode == 3) ? 0.0 : ((stableVolumetricJitter(gl_FragCoord.xy) - 0.5) * jitterAmount);") == 1
assert "if (mode >= 5 && mode <= 8)" in local
assert "fireShapeMask(worldPos" in local
assert "if (mode == 3 || mode == 6 || mode == 7)" in local
assert "mode == 3" in local
proof = json.loads((evidence / "DW_LAMP_WAVE_CLEAN_V1_PROOF.json").read_text(encoding="utf-8"))
assert proof["protected_files_unchanged"] is True
assert proof["sun_shader_modified"] is False
assert proof["fire_modes_5_to_8_modified"] is False
assert proof["backend_modified"] is False
assert proof["upscale_shader_modified"] is False
assert all(p.exists() for p in (sun, upscale, backend))
# Guard against accidental insertion of the experiment into fire/spotlight branches.
assert "mode == 3) ? 0.0" in local
assert "mode == 4) ? 0.0" not in local
print("DW_LAMP_WAVE_CLEAN_V1_STATIC_TESTS_PASS")
