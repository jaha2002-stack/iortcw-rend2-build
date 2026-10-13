#!/usr/bin/env python3
"""Repackage validated v4.4.6 binaries; preserve the exact existing production preset."""
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

dist, evidence, source = (Path(x).resolve() for x in sys.argv[1:4])
old = "DarkWolf-ioRTCW-Rend2-v4.4.6-Optimized-Clean-Candidate-Win64-SP"
name = "DarkWolf-ioRTCW-Rend2-v4.4.6-Fire-Direct-V2.2-Clean-RC-Win64-SP"
stage = dist / name
assert (dist / (old + ".zip")).is_file()
assert not stage.exists()
(dist / old).rename(stage)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
cfg = stage / "Main/PRODUCTION_HIGH_QUALITY.cfg"
original = Path(__file__).resolve().parents[1] / "optimized-v4-4-6/PRODUCTION_HIGH_QUALITY.cfg"
assert sha(cfg) == sha(original), "Production preset regression!"
binary = stage / "renderer_sp_rend2_x64.dll"
assert sha(binary) == sha(evidence / "renderer_sp_rend2_x64.dll"), "V22 compiler artifact mismatch!"
comp = json.loads((evidence / "binary-comparison.json").read_text())
assert all(v["optimized_sha256"] == v["baseline_rebuild_sha256"]
           for k, v in comp.items() if "renderer_sp_rend2_x64" not in k), "Unrelated binary changed"
assert comp["renderer_sp_rend2_x64.dll"]["optimized_sha256"] == sha(binary)
record_path = stage / "docs/BUILD_PROVENANCE.json"
record = json.loads(record_path.read_text())
record.update({
    "status": "CLEAN_BUILD_CANDIDATE_VISUAL_ACCEPTANCE_PENDING",
    "scope": "only direct dynamic fire-light BSP receiver occlusion with missing cubemap",
    "version": "DARKWOLF_V446_FIRE_DIRECT_V22",
    "builder_branch": "rend2-v446-fire-direct-occlusion-v2-20261013",
    "fire_patch_sha256": sha(evidence / "v22.patch"),
    "renderer_sha256": sha(binary),
    "protected_renderer_hashes": json.loads((evidence / "v22-preserved-hashes.json").read_text()),
    "production_preset_sha256": sha(cfg),
    "FIRE_VOLUMETRIC_MODIFIED_BY_V22": "NO",
    "ELECTRIC_LAMP_RENDERER_MODIFIED_BY_V22": "NO",
    "WINDOWS_GPU_TEST": "NOT_RUN",
    "ESCAPE1_COURTYARD_STOVE_REAL_SCREENSHOTS": "NOT_YET_VERIFIED",
    "VISUAL_PARITY_ACCEPTANCE": "PENDING",
    "SOURCE_URL": "https://github.com/jaha2002-stack/iortcw-rend2-build/tree/rend2-v446-fire-direct-occlusion-v2-20261013",
})
record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
shutil.copy2(evidence / "v22.patch", stage / "docs/DARKWOLF_FIRE_DIRECT_V22.patch")
shutil.copy2(evidence / "v22-preserved-hashes.json", stage / "docs/ProtectedSourceHashes.json")
(stage / "README_FIRE_DIRECT_V22_RU.txt").write_text(
    "DarkWolf ioRTCW Rend2 4.4.6 Fire Direct V2.2\n"
    "STATUS: Windows x64 Clean Build Candidate; VISUAL ACCEPTANCE PENDING.\n"
    "Production preset is identical to original clean optimized v4.4.6.\n"
    "No TestLab instrumentation in production binaries; original retail pak*.pk3 are NOT included.\n"
    "Purpose: keep ordinary dynamic fire lighting indoors and block BSP-occluded external receivers.\n"
    "Fire Volumetric and electrical lighting algorithms are unchanged.\n"
    "Required visual tests: escape1 courtyard guard room, furnace.md3 at -1226 602 -64,\n"
    "dynamic fire near -1340 692 -36; interior brightness, exterior wall leak, electric lamps.\n"
    "DO NOT CALL THIS A PRODUCTION ACCEPTANCE UNTIL REAL GAMEPLAY SCREENSHOTS PASS.\n",
    encoding="utf-8",
)
check = stage / "docs/SHA256SUMS.txt"
paths = sorted(p for p in stage.rglob("*") if p.is_file() and p != check)
check.write_text("".join(sha(p) + "  " + p.relative_to(stage).as_posix() + "\n" for p in paths))
archive = dist / (name + ".zip")
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in sorted(stage.rglob("*")):
        if p.is_file():
            z.write(p, name + "/" + p.relative_to(stage).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for p in paths + [check]:
        assert hashlib.sha256(z.read(name + "/" + p.relative_to(stage).as_posix())).hexdigest() == sha(p)
(dist / (name + ".zip.sha256")).write_text(sha(archive) + "  " + archive.name + "\n")
(dist / "FIRE_V22_BUILD_PROVENANCE.json").write_text(json.dumps(record, indent=2) + "\n")
(dist / (old + ".zip")).unlink()
(dist / (old + ".zip.sha256")).unlink()
assert (stage / "ioWolfSP.x64.exe").is_file()
assert (stage / "Main/cgame_sp_x64.dll").is_file()
assert (stage / "renderer_sp_rend2_x64.dll").is_file()
print("FIRE_V22_CLEAN_CANDIDATE_PACKAGE_PASS", sha(archive))
