#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, sys, zipfile

dist=Path(sys.argv[1])
base=dist/"DarkWolf_Clean_Production_FireVol_Final_From_41982135692_Win64.zip"
assert base.exists(), base

stage=dist/"firevol_slot_isolation_v1_stage"
if stage.exists(): shutil.rmtree(stage)
stage.mkdir()

with zipfile.ZipFile(base) as z:
    z.extractall(stage)

roots=[p for p in stage.iterdir() if p.is_dir()]
assert len(roots)==1, roots
old=roots[0]
name="DarkWolf_FireVol_Slot_Isolation_V1_From_42060324463_Win64"
root=stage/name
old.rename(root)

main=root/"Main"
main.mkdir(exist_ok=True)

(main/"DW_FIREVOL_SLOT_ISOLATION_START.cfg").write_text(
'''// FireVol Slot Isolation V1 - exact diagnostic derivative of Clean Production #42060324463
set developer 1
set logfile 2
set r_volumetricFire 1
set r_volumetricFireStrength 1
set r_dwFireVolContinuityDiag 1
set r_dwFireVolFixtureDiag 1
dw_fv_solo -1
echo ============================================================
echo FIREVOL SLOT ISOLATION V1 READY
echo Use: /dw_fv_solo 0 ... /dw_fv_solo 7
echo Restore all FireVol with: /dw_fv_solo -1
echo ============================================================
''')

(main/"DW_FIREVOL_SLOT_ISOLATION_RESTORE.cfg").write_text(
'''// Restore exact Clean Production render behavior
dw_fv_solo -1
set r_dwFireVolContinuityDiag 0
set r_dwFireVolFixtureDiag 0
set developer 0
echo FIREVOL SLOT ISOLATION RESTORED TO PRODUCTION ALL
''')

readme='''DarkWolf FireVol Slot Isolation V1
Diagnostic derivative of user-confirmed Clean Production GitHub Run #42060324463.

Purpose
-------
Identify exactly which of the already-selected FireVol slots 0..7 produces a visible glow.

Important behavior lock
-----------------------
dw_fv_solo -1 = normal Clean Production behavior.
The tool does NOT change FireVol selection, residency, owner de-duplication,
shadow-cache construction, IFLC priority, ELSS, or saved IFLC/ELSS profiles.
It only suppresses final rendering of non-selected slots.

Usage
-----
1. Stand at the exact problem location without moving the camera.
2. /exec DW_FIREVOL_SLOT_ISOLATION_START.cfg
3. Test:
   /dw_fv_solo 0
   /dw_fv_solo 1
   ...
   /dw_fv_solo 7
4. Note/screenshot the slot where the unwanted glow appears.
5. /condump crypt1_firevol_slot_isolation.txt
6. /exec DW_FIREVOL_SLOT_ISOLATION_RESTORE.cfg

For every active solo slot the console prints:
FIREVOL_SLOT_ISOLATION map=... solo=... selected=... rendered=...
pool=... surface=... primitive=... entity=... sourceClass=...
synthetic=... iflcPriority=... origin=x,y,z geometryRadius=...
shadowSlot=... dlightIndex=...

Do not use this diagnostic build as a new production base.
'''
(root/"README_FIREVOL_SLOT_ISOLATION_V1.txt").write_text(readme)

manifest={
    "release":"DarkWolf FireVol Slot Isolation V1",
    "base_clean_production_run":42060324463,
    "diagnostic_only":True,
    "default_solo":-1,
    "valid_solo_slots":[0,1,2,3,4,5,6,7],
    "selection_modified":False,
    "residency_modified":False,
    "shadow_cache_modified":False,
    "iflc_profiles_modified":False,
    "elss_profiles_modified":False,
}
(root/"FIREVOL_SLOT_ISOLATION_V1_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")

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

(dist/"SHA256SUMS_FIREVOL_SLOT_ISOLATION_V1.txt").write_text(
    f"{hashlib.sha256(out.read_bytes()).hexdigest()}  {out.name}\n")
print(out)
