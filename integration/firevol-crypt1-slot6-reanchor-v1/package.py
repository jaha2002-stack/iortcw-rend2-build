#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,sys,zipfile

dist=Path(sys.argv[1])
base=dist/"DarkWolf_Clean_Production_FireVol_Final_From_41982135692_Win64.zip"
assert base.exists(), base

stage=dist/"crypt1_slot6_reanchor_v1_stage"
if stage.exists(): shutil.rmtree(stage)
stage.mkdir()

with zipfile.ZipFile(base) as z:
    z.extractall(stage)

roots=[p for p in stage.iterdir() if p.is_dir()]
assert len(roots)==1, roots
old=roots[0]
name="DarkWolf_Crypt1_FireVol_Slot6_Reanchor_V1_From_42060324463_Win64"
root=stage/name
old.rename(root)

main=root/"Main"
main.mkdir(exist_ok=True)

(main/"DW_CRYPT1_SLOT6_REANCHOR_TEST.cfg").write_text(
'''// Crypt1 FireVol Slot6 Reanchor V1 TEST
// Base: user-confirmed Clean Production GitHub Run #42060324463
set developer 1
set logfile 2
set r_volumetricFire 1
set r_volumetricFireStrength 1
set r_dwFireVolContinuityDiag 1
set r_dwFireVolFixtureDiag 1
dw_fv_solo -1
echo ============================================================
echo CRYPT1 SLOT6 REANCHOR V1 TEST READY
echo Normal view first: the ghost glow should be gone.
echo Optional owner isolation remains available: /dw_fv_solo 0..7
echo ============================================================
''')

(main/"DW_CRYPT1_SLOT6_REANCHOR_RESTORE.cfg").write_text(
'''// Return diagnostic controls to normal Clean Production behavior.
dw_fv_solo -1
set r_dwFireVolContinuityDiag 0
set r_dwFireVolFixtureDiag 0
set developer 0
echo CRYPT1 SLOT6 REANCHOR DIAGNOSTICS RESTORED
''')

readme='''DarkWolf Crypt1 FireVol Slot6 Reanchor V1 TEST
=================================================

Base
----
User-confirmed Clean Production GitHub Run #42060324463.

Observed culprit from Slot Isolation
------------------------------------
selected slot 6
pool 52
runtime surface 9035
sourceClass 0 (real/native-backed)
synthetic 0
origin -1376,640,-384
geometryRadius ~118..123
shadowSlot 2
dlightIndex 24

Root cause
----------
Retail Crypt1 BSP inspection shows surface 9035 is textures/decals/burnm_01a,
a tiny burn decal rather than a physical flame. Production semantic-fire discovery
accepted generic token "burn". Synthetic/fallback paths already rejected generic
burn/scorch decals, but positive-native DLight owners could still bind to the
nearest semanticFire anchor.

V1 fix
------
Burn/scorch materials under decals/ are excluded from flame-anchor evidence.
Real fire/flame/torch/ember shader families are unchanged. Native FireVol owners
must therefore re-anchor to actual flame-family evidence instead of burn decals.

No global radius, strength, render-cap, IFLC, ELSS, Chateau, shadow-cache,
residency or FireVol energy settings are changed.

Test
----
1. Replace the Win64 files with this TEST build.
2. Start Crypt1 and go to the exact previously glowing passage.
3. /exec DW_CRYPT1_SLOT6_REANCHOR_TEST.cfg
4. Check normal view first. Do NOT change r_volumetricFireStrength from 1.
5. If needed, /dw_fv_solo 0..7 remains available for proof.
6. /condump crypt1_slot6_reanchor_v1.txt
7. /exec DW_CRYPT1_SLOT6_REANCHOR_RESTORE.cfg

This is a TEST release, not a new production base until visual PASS.
'''
(root/"README_CRYPT1_SLOT6_REANCHOR_V1.txt").write_text(readme)

manifest={
    "release":"DarkWolf Crypt1 FireVol Slot6 Reanchor V1 TEST",
    "base_clean_production_run":42060324463,
    "target":{"map":"crypt1","slot":6,"pool":52,"surface":9035,
              "origin":[-1376.0,640.0,-384.0],"sourceClass":0,"synthetic":0,
              "shadowSlot":2,"dlightIndex":24},
    "root_cause":"burn/scorch decal admitted as semanticFire anchor for positive-native DLight owner",
    "fix":"exclude decals/burn* and decals/scorch* from flame-anchor evidence, allowing physical flame re-anchor",
    "global_firevol_strength_changed":False,
    "geometry_radius_changed":False,
    "render_cap_changed":False,
    "iflc_changed":False,
    "elss_changed":False,
    "chateau_changed":False,
    "slot_isolation_diagnostic_included":True,
    "production_candidate":False
}
(root/"CRYPT1_SLOT6_REANCHOR_V1_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")

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

(dist/"SHA256SUMS_CRYPT1_SLOT6_REANCHOR_V1.txt").write_text(
    f"{hashlib.sha256(out.read_bytes()).hexdigest()}  {out.name}\n")
print(out)
