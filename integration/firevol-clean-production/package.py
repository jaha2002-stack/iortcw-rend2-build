#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, sys, zipfile

dist=Path(sys.argv[1])
base=dist/"DarkWolf_FireVol_Chateau_V6_FINAL_From_41982135692_Win64_TEST.zip"
assert base.exists(), base

stage=dist/"clean_production_stage"
if stage.exists(): shutil.rmtree(stage)
stage.mkdir()
with zipfile.ZipFile(base) as z:
    z.extractall(stage)

roots=[p for p in stage.iterdir() if p.is_dir()]
assert len(roots)==1, roots
old=roots[0]
name="DarkWolf_Clean_Production_FireVol_Final_From_41982135692_Win64"
root=stage/name
old.rename(root)

# Remove experiment/diagnostic execution packs from the delivered production tree.
main=root/"Main"
if main.exists():
    for p in list(main.glob("DW_FIREVOL_*.cfg")):
        p.unlink()

for pattern in ("README_FIREVOL_*.txt","FIREVOL_*_BUILD_STATUS.json"):
    for p in list(root.glob(pattern)):
        p.unlink()

readme='''DarkWolf CLEAN PRODUCTION - FireVol Final

Production lineage:
GitHub Run #41982135692
+ accepted ELSS V1 / V1.0.1
+ accepted IFLC tooling and profiles
+ FireVol Flash Fix V1
+ FireVol Fixture Owner V3
+ FireVol Continuity V4
+ Chateau Follow V5
+ Chateau V6 stable static-fireplace consolidation
+ final fireplace visual alignment.

Production locks:
- Crypt1 FireVol/IFLC behavior is preserved from the user-approved V5/V6 result.
- FireVol renderCap remains 8.
- First Chateau fireplace keeps V6 one-owner consolidation and stable radius.
- First Chateau fireplace uses a dedicated -4 unit plume alignment.
- Moving/secret Chateau fireplace keeps V5/V6 BMODEL follow, hold and anti-flash logic.
- Moving/secret fireplace uses a dedicated -6 unit plume alignment.
- Normal WORLD torches retain the accepted -10 unit alignment.
- Diagnostic overlays are OFF by default and no diagnostic exec cfg is required.
- Existing accepted ELSS/IFLC and other inherited renderer tools are preserved.

This archive is intended to be installed directly as the clean production build.
'''
(root/"README_CLEAN_PRODUCTION.txt").write_text(readme)

manifest={
    "release":"DarkWolf Clean Production FireVol Final",
    "base_run":41982135692,
    "production_parent_run":42049041759,
    "render_cap":8,
    "world_torch_plume_z_offset":-10,
    "static_fireplace_plume_z_offset":-4,
    "moving_bmodel_fireplace_plume_z_offset":-6,
    "crypt1_status":"USER_ACCEPTED_PASS_PRESERVED",
    "chateau_static_fireplace":"V6_STABLE_OWNER_PRESERVED",
    "chateau_moving_fireplace":"V5_V6_FOLLOW_AND_ANTI_FLASH_PRESERVED",
    "diagnostic_exec_required":False,
    "status":"CLEAN_PRODUCTION"
}
(root/"CLEAN_PRODUCTION_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")

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

(dist/"SHA256SUMS_CLEAN_PRODUCTION.txt").write_text(
    f"{hashlib.sha256(out.read_bytes()).hexdigest()}  {out.name}\n")
print(out)
