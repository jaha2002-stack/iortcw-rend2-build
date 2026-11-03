#!/usr/bin/env python3
"""Package only the renderer and user instructions; preserve existing game modules."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

ap = argparse.ArgumentParser()
ap.add_argument("source", type=Path)
ap.add_argument("evidence", type=Path)
ap.add_argument("dist", type=Path)
a = ap.parse_args()
matches = list((a.source / "SP/build").rglob("renderer_sp_rend2_x64.dll"))
assert len(matches) == 1, matches
a.dist.mkdir(parents=True, exist_ok=True)
name = "DarkWolf_IFLC_V1_FROM_41408153237_Win64_TEST"
stage = a.dist / name
stage.mkdir(exist_ok=True)
shutil.copy2(matches[0], stage / matches[0].name)
kit = Path(__file__).resolve().parent
for file in ("README_RU.md", "DW_IFLC_V1_ENABLE.cfg", "DW_IFLC_V1_DISABLE.cfg"):
    shutil.copy2(kit / file, stage / file)
shutil.copy2(a.evidence / "IFLC_SOURCE_PROOF.json", stage / "IFLC_SOURCE_PROOF.json")
status = {"status": "TEST_CANDIDATE", "base_run": 41408153237,
          "builder_commit": os.environ.get("GITHUB_SHA"),
          "build_run": os.environ.get("GITHUB_RUN_ID"),
          "renderer_sha256": hashlib.sha256(matches[0].read_bytes()).hexdigest(),
          "visual_status": "See separate runtime evidence; compile success is not visual acceptance"}
(stage / "BUILD_STATUS.json").write_text(json.dumps(status, indent=2) + "\n")
archive = a.dist / (name + ".zip")
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(stage.rglob("*")):
        if p.is_file():
            z.write(p, p.relative_to(stage))
(a.dist / "SHA256SUMS.txt").write_text(
    hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n" +
    status["renderer_sha256"] + "  renderer_sp_rend2_x64.dll\n")
print("IFLC_WIN64_TEST_PACKAGE_READY", archive, flush=True)
