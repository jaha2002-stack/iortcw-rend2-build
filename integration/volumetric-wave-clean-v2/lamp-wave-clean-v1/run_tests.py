#!/usr/bin/env python3
"""Static tests for public local volumetric mode 5 lamp jitter isolation."""
from pathlib import Path
import json,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path("source")
evidence=Path(sys.argv[2]) if len(sys.argv)>2 else Path("evidence")
local=(root/"SP/code/rend2/glsl/volumetriclocal_fp.glsl").read_text(encoding="utf-8")
backend=(root/"SP/code/rend2/tr_backend.c").read_text(encoding="utf-8")
assert "mode = Com_Clamp(0, 5, r_volumetricLocalMode ? r_volumetricLocalMode->integer : 0);" in backend
assert "else if (mode == 5)" in backend
assert "RB_LocalVolumetricRender(srcFbo, srcBox, 3, &backEnd.refdef.dlights[index]," in backend
assert local.count("float jitter = (mode == 3) ? 0.0 : ((stableVolumetricJitter(gl_FragCoord.xy) - 0.5) * jitterAmount);")==1
assert "if (mode >= 5 && mode <= 8)" in local and "fireShapeMask(worldPos" in local
proof=json.loads((evidence/"DW_LAMP_WAVE_CLEAN_MODE5_PROOF.json").read_text())
assert proof["public_production_mode"]==5 and proof["shader_mode_patched"]==3
assert proof["fire_shader_modes_5_to_8_modified"] is False
assert proof["sun_shader_modified"] is False and proof["protected_files_unchanged"] is True
print("DW_LAMP_WAVE_CLEAN_MODE5_STATIC_TESTS_PASS")

# Trigger dedicated Win64 Mode 5 full-system package rebuild with PK3 archives excluded.
