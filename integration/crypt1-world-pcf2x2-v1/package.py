#!/usr/bin/env python3
"""Repackage byte-identical #40628480022 with ONLY depth-filtered Rend2 renderer."""
import argparse,hashlib,io,json,re,zipfile
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("--base-zip",type=Path,required=True)
p.add_argument("--renderer",type=Path,required=True)
p.add_argument("--proof",type=Path,required=True)
p.add_argument("--tests",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args()
H=lambda b:hashlib.sha256(b).hexdigest()
BASE_RUN=40628480022
BASE_ARCHIVE_SHA="2e4cc61e5371103098063a02c53acc56925403abae25800fb65fe6b6bb9786d7"
BASE_RENDERER_SHA="1cff1833dcbe36c636649a405849cf72c0bc9739add42b87927851960af3f66d"
MARK="DARKWOLF_CRYPT1_ARCHITECTURAL_WORLD_VISIBILITY_PCF2X2_V1_20261028"
base=a.base_zip.read_bytes()
assert H(base)==BASE_ARCHIVE_SHA,("WRONG_USER_TESTED_BASE_ARCHIVE",H(base))
dll=a.renderer.read_bytes()
assert dll[:2]==b"MZ" and len(dll)>2000000
assert H(dll)!=BASE_RENDERER_SHA
proof=json.loads(a.proof.read_text())
tests=json.loads(a.tests.read_text())
assert proof["marker"]==MARK
assert proof["accepted_binary_base_run"]==BASE_RUN
assert proof["new_cvars"]==[] and proof["telemetry"] is False
assert sorted(proof["changed_source_files"])==sorted([
  "SP/code/rend2/glsl/dlight_fp.glsl",
  "SP/code/rend2/glsl/lightall_fp.glsl"])
assert proof["old_world_function_sha256"]=="2e518538bb8fb3db37377e539b8642e4c18bd1327e1b1ef1bf1cabdb909348d8"
assert tests["GLSL_versions"]==[120,130]
assert tests["four_sample_weights_sum_one"] is True
assert tests["full_walls_remain_zero"] is True
assert len(tests["numeric_cases"])==10
with zipfile.ZipFile(io.BytesIO(base)) as z:
    assert z.testzip() is None
    original={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
assert len(original)==35,("BASE_FILE_COUNT_CHANGED",len(original))
root="DarkWolf_Sun3_FireE_Crypt1_Shadow_Priority_Clean_Production_Win64"
assert {k.split("/")[0] for k in original}=={root}
assert all(k.startswith(root+"/") and ".." not in Path(k).parts for k in original)
renderer="renderer_sp_rend2_x64.dll"
assert H(original[root+"/"+renderer])==BASE_RENDERER_SHA
for required in ("ioWolfSP.x64.exe","renderer_sp_opengl1_x64.dll",
  "Main/cgame_sp_x64.dll","Main/qagame_sp_x64.dll",
  "Main/ui_sp_x64.dll","Main/DW_SUN3_FIRE_E_PRODUCTION.cfg"):
    assert root+"/"+required in original
entries={name.split("/",1)[1]:blob for name,blob in original.items()}
entries[renderer]=dll
assert not any(re.search(r"(^|/)pak[0-9]*\.pk3$",k,re.I) for k in entries)
readme="""DARKWOLF Crypt1 Architectural World Gate PCF2x2 - CLEAN WIN64 TEST CANDIDATE
==========================================================================
Accepted runtime origin: Sun3 + FireE #40512393634, then shadow priority #40628480022.
This build changes exactly TWO GLSL source files and only the Rend2 DLL in runtime.

GPU A/B, use the same SAVE/angle/resolution/exposure:
1. Old #40628480022, console: r_dlightWorldContainment 2
   Expected: user-observed dirty, stepped shadows in Crypt1.
2. This new DLL, console: r_dlightWorldContainment 2
   Determine whether the fence shadows are now clean and soft (do not assume).
3. This new DLL, console: r_dlightWorldContainment 0
   Clean reference without the architectural gate. This may leak light through walls.
4. Escape1 guard stove OUTSIDE the wall and both sides of near-thin partitions:
   confirm no new light leakage when r_dlightWorldContainment 2.
5. Check SWF three lamps, Sun3/Fire E, Sky, SSGI and FPS.
6. For a consistent 5-10s FPS check: same camera and scene each mode.

Implementation: 256 world-only cubemap stays nearest-neighbor packed RGB depth.
Each receiver compares depth at four neighboring cubemap texels, with identical
existing 0.35 world-unit bias and receiver-plane correction, and bilinearly
mixes the four comparisons. Entirely blocked area still returns 0, entirely
visible area remains 1. No new CVars, no telemetry, no geometry/budget change.
The independent 2048 primary DLight PCF stays unchanged.

This is NOT yet an accepted production fix until GPU A/B confirms visual
quality and no architectural light leak. Keep previous #40628480022 for rollback.
Licensed game pak files are NOT bundled.
"""
entries["README_CRYPT1_WORLD_GATE_PCF2X2_RU.txt"]=readme.encode()
manifest={
 "status":"CLEAN_PRODUCTION_CANDIDATE_GPU_VISUAL_PENDING",
 "origin_user_tested_base_run":BASE_RUN,
 "base_archive_sha256":BASE_ARCHIVE_SHA,
 "base_renderer_sha256":BASE_RENDERER_SHA,
 "new_renderer_sha256":H(dll),
 "source":proof,
 "test_results":tests,
 "changed_existing_files":[renderer,"docs/SHA256SUMS.txt"],
 "unchanged_existing_files":len(original)-2,
 "added_files":["README_CRYPT1_WORLD_GATE_PCF2X2_RU.txt",
                "docs/CRYPT1_WORLD_GATE_PCF2X2_MANIFEST.json"],
 "no_new_cvars":True,"no_telemetry":True,
 "preserved":["Sun3 dual shadow visibility","FireE 40 steps 5x5 9tap",
              "Local","Sky Single-Sample","SSGI","Tesla","CSM",
              "3 persistent and 2 dynamic shadow slots",
              "point-shadow main 2048 PCF/strength/bias",
              "256 world-only texture and packed RGB depth format",
              "physical lamp fixture groups","Bloom2","CAS/LUT/A2C"],
 "regression_guard":"Wall leakage and GPU FPS still must be checked by the user",
 "user_acceptance":"PENDING"
}
entries["docs/CRYPT1_WORLD_GATE_PCF2X2_MANIFEST.json"]=(
    json.dumps(manifest,indent=2,ensure_ascii=False)+"\n").encode()
entries["docs/SHA256SUMS.txt"]=("".join(
    H(v)+"  "+k+"\n" for k,v in sorted(entries.items()) if k!="docs/SHA256SUMS.txt")).encode("ascii")
assert len(entries)==len(original)+2
a.out.mkdir(parents=True,exist_ok=True)
name="DarkWolf_Sun3_FireE_Crypt1_WorldGate_PCF2x2_Clean_Candidate_Win64"
out=a.out/(name+".zip")
with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
    for rel,b in sorted(entries.items()):
        item=zipfile.ZipInfo(name+"/"+rel,date_time=(2026,10,28,0,0,0))
        item.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(item,b)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    got={name.split("/",1)[1]:z.read(name) for name in z.namelist() if not name.endswith("/")}
    assert len(got)==len(entries)
    assert H(got[renderer])==H(dll)
    for k,v in original.items():
        rel=k.split("/",1)[1]
        if rel not in (renderer,"docs/SHA256SUMS.txt"):
            assert got[rel]==v,("BASE_FILE_CHANGED",rel)
    assert not any("DW_VOL_DIAG" in k or "DW_SUN_V3_0" in k for k in got)
sha=H(out.read_bytes())
(a.out/(name+".sha256")).write_text(sha+"  "+out.name+"\n")
manifest["candidate_zip_sha256"]=sha
(a.out/"CRYPT1_WORLD_GATE_PCF2X2_RELEASE_AUDIT.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("DW_CRYPT1_WORLD_GATE_PCF2X2_CLEAN_RUNTIME_PACKAGE_PASS",
      str(out),"sha256="+sha,"byte_identical_existing="+str(len(original)-2),
      "renderer_sha256="+H(dll))
