#!/usr/bin/env python3
"""Fix jitter for public production r_volumetricLocalMode 5 lamp rendering."""
from pathlib import Path
import hashlib, json, sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path("source")
evidence=Path(sys.argv[2]) if len(sys.argv)>2 else Path("evidence")
shader=root/"SP/code/rend2/glsl/volumetriclocal_fp.glsl"
backend=root/"SP/code/rend2/tr_backend.c"
text=shader.read_text(encoding="utf-8")
bt=backend.read_text(encoding="utf-8")
assert "mode = Com_Clamp(0, 5, r_volumetricLocalMode ? r_volumetricLocalMode->integer : 0);" in bt
assert "else if (mode == 5)" in bt
assert "RB_LocalVolumetricRender(srcFbo, srcBox, 3, &backEnd.refdef.dlights[index]," in bt
old="float jitter = (stableVolumetricJitter(gl_FragCoord.xy) - 0.5) * jitterAmount;"
new="""// DW_LAMP_WAVE_CLEAN_MODE5: public r_volumetricLocalMode 5 dispatches lamps as shader mode 3.
    // Fire shader modes 5..8 and spotlight mode 4 retain their original jitter.
    float jitter = (mode == 3) ? 0.0 : ((stableVolumetricJitter(gl_FragCoord.xy) - 0.5) * jitterAmount);"""
assert "if (mode >= 5 && mode <= 8)" in text
assert text.count(old)==1, text.count(old)
protected=[root/"SP/code/rend2/glsl/volumetricsun_fp.glsl",root/"SP/code/rend2/glsl/volumetriclocal_upscale_fp.glsl"]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.name:sha(p) for p in protected}
shader.write_text(text.replace(old,new),encoding="utf-8",newline="\n")
after={p.name:sha(p) for p in protected}
assert before==after
evidence.mkdir(parents=True,exist_ok=True)
(evidence/"DW_LAMP_WAVE_CLEAN_MODE5_PROOF.json").write_text(json.dumps({
"status":"STATIC_TEST_CANDIDATE","public_cvar":"r_volumetricLocalMode","public_production_mode":5,
"renderer_dispatch":"RB_LocalVolumetricRender(..., 3, lamp, ...)","shader_mode_patched":3,
"change":"zero ray-step jitter for production lamp shader mode only",
"fire_shader_modes_5_to_8_modified":False,"spotlight_shader_mode_4_modified":False,
"sun_shader_modified":False,"protected_files_sha256_before_after":before,
"protected_files_unchanged":before==after},indent=2)+"\n")
print("DW_LAMP_WAVE_CLEAN_MODE5_APPLY_PASS")
