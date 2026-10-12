#!/usr/bin/env python3
"""Post-rootfix source delta, mode, and provenance gate. Original v4.4.6 gate runs first."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

source, baseline, evidence = (Path(p).resolve() for p in sys.argv[1:])
expected = sorted([
    "SP/code/rend2/glsl/ssgi_fp.glsl",
    "SP/code/rend2/glsl/volumetriclocal_fp.glsl",
    "SP/code/rend2/glsl/volumetricsun_fp.glsl",
    "SP/code/rend2/tr_main.c",
    "SP/code/rend2/tr_scene.c",
    "SP/code/rend2/tr_shade.c",
])
got = sorted(x.strip() for x in subprocess.check_output(
    ["git", "-C", str(source), "diff", "--name-only"], text=True).splitlines() if x.strip())
assert got == expected, f"Unexpected source delta: {got!r}"
shade = (source / "SP/code/rend2/tr_shade.c").read_text()
vol = (source / "SP/code/rend2/glsl/volumetriclocal_fp.glsl").read_text()
assert shade.count("DARKWOLF_V446_FIRE_LEAK_DIRECT_FAIL_CLOSED_RC1") == 2
assert shade.count("DWSHADOW_SOURCE_PERSISTENT_FIRE ||") >= 2
assert vol.count("DARKWOLF_V446_FIRE_LEAK_VOLUME_FAIL_CLOSED_RC1") == 1
assert "if (u_DlightShadowParams.x < 0.5)\n        return 0.0;" in vol
assert "DARKWOLF_V446_OPT06_FIRE_GAUSSIAN_SQRT_ELIMINATION" in vol
manifest = json.loads((evidence / "rootfix-source.json").read_text())
for path, digest in manifest["postimage_sha256"].items():
    assert hashlib.sha256((source / path).read_bytes()).hexdigest() == digest, path
base_diff = json.loads((evidence / "source-policy.json").read_text())
assert base_diff["status"] == "PASS", "Original v4.4.6 provenance gate not passed"
print("DARKWOLF_V446_FIRE_LEAK_ROOTFIX_SOURCE_POLICY_PASS", len(got), "files")
