#!/usr/bin/env python3
"""Produce exact #40640998083 Win64 with test-only CGame and Rend2 DLLs, nothing else."""
import argparse,hashlib,io,json,struct,zipfile,re
from pathlib import Path
H=lambda b:hashlib.sha256(b).hexdigest()
BASE_SHA="d43a166c3f7c0b9ecb92767401c1617aecfea0337c137e28ae175b3d4db900b1"
RENDER_SHA="1d27de162dff6328c1504781edd973fa286289101a0557a1012252d618804c47"
CGAME_SHA="52908cfeca0cf3d589ad8a84f083e100a4e2aa02757ee687d264946281947bcf"
ROOT="DarkWolf_Sun3_FireE_Crypt1_Shadow_Fidelity_Clean_Production_Win64"
NAME="DarkWolf_Xlabs_Tesla_Escape1_Fire_Origin_Trace_Test_V2_Win64"
MARK="DARKWOLF_XLABS_ESCAPE1_DIAGNOSTIC_V2_20261028"
ap=argparse.ArgumentParser()
for p in ("base-zip","renderer","cgame","proof","qa","out"):
    ap.add_argument("--"+p,required=True,type=Path)
a=ap.parse_args()
original=a.base_zip.read_bytes()
assert H(original)==BASE_SHA,("BASE_NOT_ACCEPTED_40640998083",H(original))
with zipfile.ZipFile(io.BytesIO(original)) as z:
    assert z.testzip() is None
    previous={k.filename:z.read(k) for k in z.infolist() if not k.is_dir()}
assert len(previous)==40
assert {k.split("/")[0] for k in previous}=={ROOT}
assert all(k.startswith(ROOT+"/") and ".." not in Path(k).parts for k in previous)
files={k.split("/",1)[1]:blob for k,blob in previous.items()}
assert H(files["renderer_sp_rend2_x64.dll"])==RENDER_SHA
assert H(files["Main/cgame_sp_x64.dll"])==CGAME_SHA
proof=json.loads(a.proof.read_text())
qa=json.loads(a.qa.read_text())
assert proof["marker"]==MARK and proof["frozen_binary_run"]==40640998083
assert qa["status"]=="PASS" and all(qa["checks"].values())
assert sorted(proof["changed_source_files"])==sorted([
 "SP/code/cgame/cg_main.c","SP/code/cgame/cg_local.h",
 "SP/code/cgame/cg_ents.c","SP/code/rend2/tr_main.c"])
for rel,source in (("renderer_sp_rend2_x64.dll",a.renderer),("Main/cgame_sp_x64.dll",a.cgame)):
    obj=source.read_bytes()
    assert H(obj)!=H(files[rel]) and len(obj)>150000
    off=struct.unpack_from("<I",obj,0x3c)[0]
    assert obj[:2]==b"MZ" and obj[off:off+4]==b"PE\0\0"
    assert struct.unpack_from("<H",obj,off+4)[0]==0x8664
    files[rel]=obj
configs=[
 ("0_XLABS_REFERENCE",2,0,0),
 ("1_XLABS_SHIFT64",2,1,0),
 ("2_XLABS_SHIFT96",2,2,0),
 ("3_XLABS_GATE1_REFERENCE",1,0,0),
 ("4_XLABS_SOURCE_AUDIT",2,0,1),
 ("5_ESCAPE1_SOURCE_AUDIT",2,0,1)]
for name,gate,shift,audit in configs:
    cfg=(
      "// DarkWolf Xlabs Escape1 TEST V2. Do NOT reuse as a production preset.\n"
      "exec DW_CRYPT1_SHADOW_FIDELITY_PRODUCTION.cfg\n"
      f'set r_dlightWorldContainment "{gate}"\n'
      f'set cg_dwTeslaNativeShiftTest "{shift}"\n'
      'set cg_xlabsTeslaDoorLight "1"\n'
      'set cg_xlabsTeslaDoorShadows "1"\n'
      'set cg_xlabsTeslaDoorIntensity "0.95"\n'
      'set cg_xlabsTeslaDoorRadius "300"\n'
      'set r_volumetricFire "1"\n'
      f'set r_dwWorldGateAuditOnce "{audit}"\n'
      'set cg_drawFPS "1"\n'
    )
    files["Main/DW_TEST_V2_"+name+".cfg"]=cfg.encode("ascii")
readme="""DARKWOLF: Xlabs Stationary Tesla / Escape1 Stove World Gate - TEST V2
==================================================================
Base: exact user-accepted #40640998083, including Crypt1 PCF2x2 shadows.
TEMPORARY experiment, not a clean production build. Changes: game CGame
DLL (only Xlabs native Tesla lighting test) and Rend2 DLL (one-shot audit).
No changes to Crypt1 shaders, Sun3, Fire E, Local, CSM, Sky, shadow budgets,
Tesla bolt animation, existing shadow sampling or other gameplay binaries.

Xlabs SAME SAVE / VIEW, keep generator bolts ACTIVE:
  exec DW_TEST_V2_0_XLABS_REFERENCE.cfg
  exec DW_TEST_V2_1_XLABS_SHIFT64.cfg
  exec DW_TEST_V2_2_XLABS_SHIFT96.cfg
  exec DW_TEST_V2_3_XLABS_GATE1_REFERENCE.cfg
All other settings identical. Modes 1/2 shift the NATIVE Tesla point-light
origin farther along the existing bolt-to-target vector *only on Xlabs*.
Mode 0 is exact original; mode 3 is known bright reference with Tesla gate
disabled and Fire gate still on. Compare blue illumination, shadows, wall
leaks, flicker and 10s FPS. DO NOT assume shift is acceptable for release;
it changes the light origin and can create new leaks or changed attenuation.

SOURCE AUDIT, no video/telemetry capture:
  In Xlabs: exec DW_TEST_V2_4_XLABS_SOURCE_AUDIT.cfg
  In Escape1 OUTSIDE stove wall: exec DW_TEST_V2_5_ESCAPE1_SOURCE_AUDIT.cfg
The renderer prints WG_AUDIT_V2_BEGIN/LIGHT/END exactly once (maximum 32
lines) and immediately resets r_dwWorldGateAuditOnce to zero.
After the print, type: condump worldgate_escape1_v2.log
Send that console dump and 4 Xlabs comparison screenshots.
For each light the dump lists position, color, radius, camera distance,
worldOcclusion 0/1, world cache slot, native 0/1, FireVol 0/1, class.
This distinguishes an unclassified stove source from a bad world mask.
If no BEGIN block appears, run the audit command again with console open.

RESET: exec DW_TEST_V2_0_XLABS_REFERENCE.cfg
Do not transfer test-only Cvars to production. Preserve original #40640998083
in a separate folder for independent rollback and A/B.
Licensed RTCW pak files are not distributed.
"""
files["README_XLABS_ESCAPE1_V2.txt"]=readme.encode("ascii")
manifest={
 "type":"TEMPORARY_DIAGNOSTIC_NOT_PRODUCTION",
 "base_run":40640998083,"base_sha256":BASE_SHA,
 "prior_renderer_sha256":RENDER_SHA,"prior_cgame_sha256":CGAME_SHA,
 "new_renderer_sha256":H(files["renderer_sp_rend2_x64.dll"]),
 "new_cgame_sha256":H(files["Main/cgame_sp_x64.dll"]),
 "user_accepted_crypt1_shadow_shaders_unchanged":True,
 "changes_to_engine_source":proof["changed_source_files"],
 "temporary_test_cvars":proof["temporary_test_cvars"],
 "unmodified_existing_files":len(previous)-3,
 "replaced":["renderer_sp_rend2_x64.dll","Main/cgame_sp_x64.dll","docs/SHA256SUMS.txt"],
 "qa":qa,"profiles":[n for n,_,_,_ in configs],
 "gpu_quality_performance_not_yet_accepted":True}
files["docs/XLABS_ESCAPE1_V2_TEST_MANIFEST.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
files["docs/SHA256SUMS.txt"]="".join(H(v)+"  "+k+"\n" for k,v in sorted(files.items())
                                       if k!="docs/SHA256SUMS.txt").encode("ascii")
assert len(files)==len(previous)+len(configs)+2
assert not any(re.search(r"(^|/)pak[0-9]*\.pk3$",k,re.I) for k in files)
a.out.mkdir(parents=True,exist_ok=True)
release=a.out/(NAME+".zip")
with zipfile.ZipFile(release,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
    for name,blob in sorted(files.items()):
        ent=zipfile.ZipInfo(NAME+"/"+name,date_time=(2026,10,28,0,0,0))
        ent.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(ent,blob)
with zipfile.ZipFile(release) as z:
    assert z.testzip() is None
    check={name.split("/",1)[1]:z.read(name) for name in z.namelist() if not name.endswith("/")}
    assert len(check)==len(files)
    for path,old in previous.items():
        rel=path.split("/",1)[1]
        if rel not in ("renderer_sp_rend2_x64.dll","Main/cgame_sp_x64.dll","docs/SHA256SUMS.txt"):
            assert check[rel]==old,("UNEXPECTED_BASE_REGRESSION",rel)
    for line in check["docs/SHA256SUMS.txt"].decode("ascii").splitlines():
        h,name=line.split("  ",1)
        assert H(check[name])==h,("INTERNAL_HASH_FAIL",name)
audit=dict(manifest)
audit.update(zip_file=release.name,zip_sha256=H(release.read_bytes()),
             file_count=len(check),all_internal_checksums_valid=True)
(a.out/"XLABS_ESCAPE1_TEST_V2_AUDIT.json").write_text(json.dumps(audit,indent=2)+"\n")
(a.out/(NAME+".zip.sha256")).write_text(audit["zip_sha256"]+"  "+NAME+".zip\n")
print("DW_XLABS_ESCAPE1_V2_PACKAGE_EXACT_BASE_PASS",str(release),audit["zip_sha256"])
