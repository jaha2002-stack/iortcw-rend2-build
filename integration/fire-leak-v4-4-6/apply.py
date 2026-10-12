#!/usr/bin/env python3
"""Strict v4.4.6 fire/light occlusion safety patch. Only two C paths and one GLSL function."""
import hashlib
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "optimized-v4-4-6"
lock = json.loads((root / "baseline_source_manifest.json").read_text())
engine = Path(sys.argv[1]).resolve()
evidence = Path(sys.argv[2]).resolve()
evidence.mkdir(parents=True, exist_ok=True)
shade_path = "SP/code/rend2/tr_shade.c"
vol_path = "SP/code/rend2/glsl/volumetriclocal_fp.glsl"
shade_original = (engine / shade_path).read_bytes()
assert hashlib.sha256(shade_original).hexdigest() == lock["baseline_source_files"][shade_path], "Unverified tr_shade.c; refuse patch"
shader_original = (engine / vol_path).read_bytes()
assert b"DARKWOLF_V446_OPT04_LOCALVOL_LOOP_INVARIANTS" in shader_original, "Optimized shader missing"
shade = shade_original.decode("utf-8")
shader = shader_original.decode("utf-8")

# The two exact receiver routes are ProjectDlightTexture and ForwardDlight.
# Do not disable explosions, muzzle light, Tesla or the fire sprite itself.
pattern = re.compile(
    r"(?P<block>^[ \t]*shadowSlot = \(int\)backEnd\.refdef\.dlightShadowSlot\[l\];\n"
    r"[ \t]*useShadow = r_dlightMode->integer >= 2\n"
    r"[ \t]*&& \(backEnd\.refdef\.dlightShadowMask & \(1u << l\)\)\n"
    r"[ \t]*&& shadowSlot >= 0 && shadowSlot < MAX_DLIGHT_SHADOWS\n"
    r"[ \t]*&& tr\.shadowCubemaps\[shadowSlot\] != NULL;)",
    flags=re.MULTILINE,
)
guard = (
    "\n\t\t// DARKWOLF_V446_FIRE_LEAK_DIRECT_FAIL_CLOSED_RC1: no persistent unshadowed light.\n"
    "\t\tif (r_dlightMode->integer >= 2 && !useShadow &&\n"
    "\t\t\t(dl->shadowSourceClass == DWSHADOW_SOURCE_PERSISTENT_FIRE ||\n"
    "\t\t\t dl->shadowSourceClass == DWSHADOW_SOURCE_PERSISTENT_PHYSICAL))\n"
    "\t\t\tcontinue;"
)
shade_fixed, count = pattern.subn(lambda m: m.group("block") + guard, shade)
assert count == 2, f"Expected 2 point-light receiver guards, got {count}"
shader_old = "    if (u_DlightShadowParams.x < 0.5)\n        return 1.0;"
shader_new = ("    // DARKWOLF_V446_FIRE_LEAK_VOLUME_FAIL_CLOSED_RC1: modes 3/6/7 require real occlusion.\n"
              "    if (u_DlightShadowParams.x < 0.5)\n        return 0.0;")
assert shader.count(shader_old) == 1, f"Expected single shadow-aware volumetric fallback, got {shader.count(shader_old)}"
shader_fixed = shader.replace(shader_old, shader_new, 1)
assert shade_fixed.count("DARKWOLF_V446_FIRE_LEAK_DIRECT_FAIL_CLOSED_RC1") == 2
assert shader_fixed.count("DARKWOLF_V446_FIRE_LEAK_VOLUME_FAIL_CLOSED_RC1") == 1

# Both anchors and baseline identity were checked before either source was touched.
(engine / shade_path).write_text(shade_fixed)
(engine / vol_path).write_text(shader_fixed)
report = {
    "status": "SOURCE_PATCH_PASS",
    "version": "DARKWOLF_V446_FIRE_LEAK_ROOTFIX_RC1",
    "guards": {"ProjectDlightTexture": 1, "ForwardDlight": 1, "volumetric_shader": 1},
    "in_scope": [shade_path, vol_path],
    "preimage_sha256": {shade_path: hashlib.sha256(shade_original).hexdigest(),
                        vol_path: hashlib.sha256(shader_original).hexdigest()},
    "postimage_sha256": {shade_path: hashlib.sha256(shade_fixed.encode()).hexdigest(),
                         vol_path: hashlib.sha256(shader_fixed.encode()).hexdigest()},
    "not_changed": ["dlight source class", "fire sprite", "muzzle/Tesla/explosion shadow policy",
                    "BSP/PVS", "sun CSM", "shadow budget"]
}
(evidence / "rootfix-source.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
