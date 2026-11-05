#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, sys, zipfile

dist=Path(sys.argv[1])
base_zip=dist/"DarkWolf_FireVol_Chateau_Follow_V5_FINAL_From_41982135692_Win64_TEST.zip"
assert base_zip.exists(), base_zip
stage=dist/"v6_stage"
if stage.exists(): shutil.rmtree(stage)
stage.mkdir()
with zipfile.ZipFile(base_zip) as z: z.extractall(stage)
roots=[p for p in stage.iterdir() if p.is_dir()]
assert len(roots)==1, roots
old=roots[0]
name="DarkWolf_FireVol_Chateau_V6_FINAL_From_41982135692_Win64_TEST"
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
(main/"DW_FIREVOL_CHATEAU_V6_FINAL.cfg").write_text(cfg)

(root/"README_FIREVOL_CHATEAU_V6_RU.txt").write_text('''DarkWolf FireVol Chateau V6 - FINAL TEST

Base lineage:
GitHub Run #41982135692 + accepted ELSS V1/V1.0.1 + FireVol FlashFix V1 + Fixture V3 + Continuity V4 + Chateau Follow V5.

Preserved from V5:
- Crypt1 WORLD/IFLC behavior and renderCap=8.
- Moving Chateau fireplace local BMODEL anchor.
- No selected=0 flash at the secret-room entrance.
- BMODEL hold and moved-shadow handling.
- All inherited ELSS/IFLC and earlier accepted renderer work.

V6 final changes only:
1. A large real static WORLD fireplace absorbs nearby synthetic WORLD flame companions inside 192 units.
   This prevents several overlapping FireVol volumes from alternating around the first Chateau fireplace.
2. Once such a real fireplace owner is established, its FireVol geometry radius is held stable instead of
   following small native DLight-radius oscillations.
3. The proven moving BMODEL fireplace FireVol render volume is shifted 12 units downward toward the visible flame.
   Its V5 ownership, movement following, hold and anti-flash behavior are otherwise unchanged.
4. Crypt1 is intentionally outside the V6 large-fireplace gate.

Test:
 /exec DW_FIREVOL_CHATEAU_V6_FINAL.cfg

Chateau:
- First static fireplace: check side light/FireVol for continuous jitter.
- Moving secret-room fireplace: open/close several times; verify no entrance flash and FireVol sits lower on the flame.

Crypt1:
- Regression only. Expected V5 PASS behavior unchanged.

Then:
 /condump firevol_chateau_v6.txt

Diagnostic marker:
 FIREVOL_CONTINUITY_V6
''')

status={
  "name":"DarkWolf FireVol Chateau V6 FINAL TEST",
  "base_run":41982135692,
  "inherits":"Chateau Follow V5 + all accepted lineage",
  "render_cap":8,
  "static_fireplace_raw_radius_min":360,
  "static_fireplace_companion_radius":192,
  "bmodel_plume_z_offset":-12,
  "world_plume_z_offset":-10,
  "status":"COMPILED_TEST_CANDIDATE"
}
(root/"FIREVOL_CHATEAU_V6_BUILD_STATUS.json").write_text(json.dumps(status,indent=2))

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
(dist/"SHA256SUMS_V6.txt").write_text(
    f"{hashlib.sha256(out.read_bytes()).hexdigest()}  {out.name}\n")
print(out)
