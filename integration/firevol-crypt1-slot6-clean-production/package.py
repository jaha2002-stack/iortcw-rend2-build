#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, sys, zipfile

dist = Path(sys.argv[1])
base = dist / "DarkWolf_Clean_Production_FireVol_Final_From_41982135692_Win64.zip"
assert base.exists(), base

stage = dist / "crypt1_slot6_clean_production_stage"
if stage.exists():
    shutil.rmtree(stage)
stage.mkdir()

with zipfile.ZipFile(base) as z:
    z.extractall(stage)

roots = [p for p in stage.iterdir() if p.is_dir()]
assert len(roots) == 1, roots
old = roots[0]
name = "DarkWolf_Clean_Production_FireVol_Crypt1_Reanchor_From_42060324463_Win64"
root = stage / name
old.rename(root)

# Production archive must not carry the temporary Slot6 test/diagnostic wrapper.
main = root / "Main"
if main.exists():
    for pat in (
        "DW_CRYPT1_SLOT6_REANCHOR_TEST.cfg",
        "DW_CRYPT1_SLOT6_REANCHOR_RESTORE.cfg",
        "*SLOT_ISOLATION*.cfg",
    ):
        for p in main.glob(pat):
            p.unlink()

for pat in (
    "README_CRYPT1_SLOT6_REANCHOR_V1.txt",
    "CRYPT1_SLOT6_REANCHOR_V1_MANIFEST.json",
    "*SLOT_ISOLATION*",
):
    for p in root.glob(pat):
        if p.is_file():
            p.unlink()

readme = """DarkWolf CLEAN PRODUCTION - FireVol Final + Crypt1 Reanchor

Production lineage
------------------
User-confirmed Clean Production: GitHub Run #42060324463.
Visual PASS test of the targeted correction: GitHub Run #42192556922.

Accepted correction
-------------------
Crypt1 FireVol owner surface 9035 / pool 52 could bind to
textures/decals/burnm_01a because generic token "burn" was accepted as
semantic flame evidence for a positive native DLight owner.

The production correction excludes decals/burn* and decals/scorch* materials
from FireVol flame-anchor evidence. Real fire/flame/torch/blaze/ember/
flamethrower families remain accepted.

Production locks
----------------
- No global FireVol geometry-radius reduction.
- FireVol renderCap remains 8.
- Existing Crypt1, Chateau, IFLC, ELSS, shadow-cache, residency, continuity
  and anti-flash behavior from #42060324463 is preserved.
- Diagnostic Slot Isolation / dw_fv_solo is NOT included.
- No Crypt1 test cfg is required.
- Diagnostic overlays remain OFF by default.

Status
------
CLEAN PRODUCTION. The previously reported glow near the Crypt1 passage was
confirmed gone by the user with the #42192556922 test build.
"""
(root / "README_CLEAN_PRODUCTION.txt").write_text(readme)

manifest_path = root / "CLEAN_PRODUCTION_MANIFEST.json"
manifest = {}
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text())

manifest.update({
    "release": "DarkWolf Clean Production FireVol Final + Crypt1 Reanchor",
    "base_clean_production_run": 42060324463,
    "visual_pass_test_run": 42192556922,
    "crypt1_slot6_reanchor": {
        "status": "USER_VISUAL_PASS",
        "map": "crypt1",
        "pool": 52,
        "surface": 9035,
        "sourceClass": 0,
        "synthetic": 0,
        "root_cause": "burn/scorch decal admitted as semantic FireVol anchor for positive native DLight owner",
        "fix": "exclude decals/burn* and decals/scorch* from flame-anchor evidence"
    },
    "global_firevol_strength_changed": False,
    "geometry_radius_changed": False,
    "render_cap_changed": False,
    "iflc_changed": False,
    "elss_changed": False,
    "chateau_changed": False,
    "slot_isolation_diagnostic_included": False,
    "diagnostic_exec_required": False,
    "status": "CLEAN_PRODUCTION"
})
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

# Verify the delivered renderer contains the production classifier literals but
# does not contain the temporary Slot Isolation command/telemetry.
dlls = list(root.rglob("renderer_sp_rend2_x64.dll"))
assert len(dlls) == 1, dlls
data = dlls[0].read_bytes()
assert b"/decals/" in data
assert b"scorch" in data
assert b"dw_fv_solo" not in data
assert b"FIREVOL_SLOT_ISOLATION" not in data

# No temporary Crypt1 Slot6 test pack in the production tree.
for p in root.rglob("*"):
    if p.is_file():
        n = p.name.upper()
        assert "SLOT6_REANCHOR_TEST" not in n
        assert "SLOT6_REANCHOR_RESTORE" not in n
        assert "SLOT_ISOLATION" not in n

checksum = root / "SHA256SUMS.txt"
if checksum.exists():
    checksum.unlink()
rows = []
for p in sorted(root.rglob("*")):
    if p.is_file() and p.name != "SHA256SUMS.txt":
        rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}")
checksum.write_text("\n".join(rows) + "\n")

out = dist / (name + ".zip")
if out.exists():
    out.unlink()
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(root.rglob("*")):
        if p.is_file():
            z.write(p, arcname=f"{name}/{p.relative_to(root).as_posix()}")

(dist / "SHA256SUMS_CRYPT1_REANCHOR_CLEAN_PRODUCTION.txt").write_text(
    f"{hashlib.sha256(out.read_bytes()).hexdigest()}  {out.name}\n"
)
print(out)

# ci-trigger-after-base-workflow
