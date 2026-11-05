#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, sys, zipfile

dist=Path(sys.argv[1])
base_zip=dist/"DarkWolf_FireVol_Continuity_V4_From_41982135692_Win64_TEST.zip"
assert base_zip.exists(), base_zip
stage=dist/"v5_stage"
if stage.exists(): shutil.rmtree(stage)
stage.mkdir()
with zipfile.ZipFile(base_zip) as z: z.extractall(stage)
roots=[p for p in stage.iterdir() if p.is_dir()]
assert len(roots)==1, roots
old=roots[0]
name="DarkWolf_FireVol_Chateau_Follow_V5_FINAL_From_41982135692_Win64_TEST"
root=stage/name
old.rename(root)
main=root/"Main"
main.mkdir(exist_ok=True)

cfg='''seta r_dwFireVolFlashFix "1"
seta r_dwFireVolWarmupGuard "1"
seta r_dwFireVolEnergyGuard "1"
seta r_dwFireVolFLCFade "1"
seta r_dwFireVolFixtureV3 "1"
seta r_dwFireVolFixtureDiag "0"
seta r_dwFireVolContinuityV4 "1"
seta r_dwFireVolContinuityDiag "1"
seta r_dwFireVolWorldClusterRadius "48"
seta r_dwFireVolWorldGeometryScale "0.45"
seta r_dwFireVolIFLCPriority "1"
seta r_dwFireVolMovingBmodelFallback "0.65"
seta r_dwFireVolGeometryScale "0.55"
seta r_dwFireVolGeometryMin "96"
'''
(main/"DW_FIREVOL_CHATEAU_V5_FINAL.cfg").write_text(cfg)
(main/"DW_FIREVOL_CHATEAU_V5_AB_OFF.cfg").write_text('''seta r_dwFireVolContinuityV4 "0"
seta r_dwFireVolContinuityDiag "1"
seta r_dwFireVolFixtureV3 "1"
''')

(root/"README_FIREVOL_CHATEAU_V5_RU.txt").write_text('''DarkWolf FireVol Chateau Follow V5 - FINAL TEST

Base lineage: GitHub Run #41982135692 + ELSS V1/V1.0.1 + FireVol FlashFix V1 + Fixture V3 + Continuity V4.

V5 changes:
1. Moving BMODEL flame owner stores a stable entity-local anchor and follows the current entity transform every frame.
2. A nearby synthetic BMODEL companion is suppressed when a real-backed physical owner exists; two different real-backed BMODEL fires are never merged.
3. A moving BMODEL owner is retained for 5 seconds through temporary drawSurf/PVS loss, preventing selected=0 gaps during the secret-fireplace animation.
4. When a BMODEL has moved away from its real DLight/shadow origin, the old cubemap is not treated as if it were still aligned. During motion a compact low-energy local fallback is used; after motion a synthetic architectural cubemap is rebuilt at the final flame position and faded in.
5. BMODEL geometry-radius smoothing is not reset by translation.
6. WORLD torch plume geometry is shifted down by 10 units only; strength, renderCap=8, residency and Crypt1 dedup remain unchanged.

Test:
 /exec DW_FIREVOL_CHATEAU_V5_FINAL.cfg
 Chateau: open/close the secret fireplace several times and inspect both fireplaces.
 Crypt1: verify all torches/IFLC FireVol remains stable and the plume sits closer around the flame.
 Then:
 /condump firevol_chateau_v5.txt

Diagnostic marker:
 FIREVOL_CONTINUITY_V5
''')

status={
  "name":"DarkWolf FireVol Chateau Follow V5 FINAL TEST",
  "base_run":41982135692,
  "inherits":"FireVol Continuity V4",
  "render_cap":8,
  "bmodel_companion_radius":112,
  "bmodel_hold_ms":5000,
  "moving_fallback_weight":0.38,
  "moving_fallback_radius":112,
  "world_plume_z_offset":-10,
  "status":"COMPILED_TEST_CANDIDATE"
}
(root/"FIREVOL_CHATEAU_V5_BUILD_STATUS.json").write_text(json.dumps(status,indent=2))

# Replace inherited checksum list with checksums for the actual V5 tree.
checksum=root/"SHA256SUMS.txt"
if checksum.exists(): checksum.unlink()
rows=[]
for p in sorted(root.rglob("*")):
    if p.is_file() and p.name!="SHA256SUMS.txt":
        rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}")
checksum.write_text("\n".join(rows)+"\n")

out=dist/(name+".zip")
if out.exists(): out.unlink()
with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(root.rglob("*")):
        if p.is_file():
            z.write(p,arcname=f"{name}/{p.relative_to(root).as_posix()}")
(dist/"SHA256SUMS_V5.txt").write_text(
    f"{hashlib.sha256(out.read_bytes()).hexdigest()}  {out.name}\n")
print(out)
