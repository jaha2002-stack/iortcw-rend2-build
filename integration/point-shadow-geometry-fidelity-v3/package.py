#!/usr/bin/env python3
"""Pack point-shadow test DLL atop immutable user-accepted #41019985033 archive."""
import hashlib,io,json,sys,zipfile
from pathlib import Path

NAME="DarkWolf_PointShadow_Geometry_Fidelity_V3_TEST_ONLY_From_41019985033_Win64"
BASE_ROOT="DarkWolf_Volumetric_Sun_HDR16F_Precision_V1_Clean_Production_Win64"
BASE_SHA="d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45"
def sha(data):return hashlib.sha256(data).hexdigest()

def package(artifact,renderer,proof,outdir):
    with zipfile.ZipFile(artifact) as o:
        assert o.testzip() is None
        names=[n for n in o.namelist() if n.startswith("dist/") and n.endswith(".zip")]
        assert len(names)==1,names
        payload=o.read(names[0])
        assert sha(payload)=="e61a38fec90fbdece43364232c0064e40825eb86db7c035df9a46cddcf2cc869"
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        assert z.testzip() is None
        original={n[len(BASE_ROOT)+1:]:z.read(n) for n in z.namelist() if n.startswith(BASE_ROOT+"/") and not n.endswith("/")}
    assert len(original)==57,len(original)
    assert sha(original["renderer_sp_rend2_x64.dll"])==BASE_SHA
    newdll=Path(renderer).read_bytes()
    assert len(newdll)>500000 and newdll[:2]==b"MZ"
    assert sha(newdll)!=BASE_SHA
    for mark in (b"r_dwPointCasterScope",b"r_dwPointReceiverPath",b"r_dwPointNearWorldClip",b"r_dwPointOriginAxis",b"r_dwPointOriginShift",b"_dwSunHalfRGBA16F", b"r_dwPointV3Mode", b"r_dwPointV3TargetTolerance", b"r_dwPointV3InspectSurface"):
        assert mark in newdll,("missing marker",mark)
    patch=json.loads(Path(proof).read_text())
    assert patch["accepted_baseline_run"]==41019985033
    assert patch["v3_default_has_no_draw_or_light_changes"] and patch["stage11_asset_coverage_preserved_at_defaults"] and patch["fire_worldmask_sun_hdr16f_and_glsl_not_changed_in_v3"]
    files=dict(original)
    files["renderer_sp_rend2_x64.dll"]=newdll
    readme="""DARKWOLF POINT SHADOW GEOMETRY FIDELITY V3 (TEST ONLY)
Original Clean Production remains #41019985033. Test separate install.
Default mode 0 and tolerance 0: all ordinary shadow geometry unchanged.
1. /exec DW_PS_V3_A_BASELINE.cfg
2. /r_dwPointV3ListLight -2  : print current dlight indices and origins
   every ~120 frames. Set -1 to stop logging.
3. Pick source capture coordinates from DW_PS_V3_SOURCE line.
   Set r_dwPointV3SourceX, r_dwPointV3SourceY, r_dwPointV3SourceZ,
   r_dwPointV3TargetTolerance 0.25; /vid_restart.
4. r_dwPointV3Mode 1 includes only BSP world surface IDs in
   [r_dwPointV3SurfaceFirst, r_dwPointV3SurfaceLast] for selected light.
   Mode 2 excludes selected BSP interval; all entity casters remain.
   Mode 0 restores all casters. /vid_restart for range and mode.
5. r_dwPointV3InspectSurface N logs shader, AABB, centroid and depth
   capture proximity. Draw-list presence does NOT prove depth ownership.
   Source dlight index is NOT a verified FixtureId or shadow slot.
6. All modes of V1/V2 clip, shift, scope must remain at 0.
Filtered modes deliberately hide shadow casters: TEST ONLY.
Save same-camera screenshots on spotlight, Factory arch, Crypt1 flame.
Restore original #41019985033 renderer DLL after testing.
NO V3 shadow shape or softness fix has been accepted.
"""
    files["README_POINT_SHADOW_DIAGNOSTIC_V3.txt"]=readme.encode("utf-8")
    modes=[("A_BASELINE",0),("B_INCLUDE_BSP_INTERVAL",1),("C_EXCLUDE_BSP_INTERVAL",2)]
    for mode_name,mode in modes:
        config=f"""// V3 TEST ONLY {mode_name}
set r_dwPointCasterScope "0"
set r_dwPointReceiverPath "0"
set r_dwPointNearWorldClip "0"
set r_dwPointOriginAxis "0"
set r_dwPointOriginShift "0"
set r_dwPointV3Mode "{mode}"
set r_dwPointV3SourceX "0"
set r_dwPointV3SourceY "0"
set r_dwPointV3SourceZ "0"
set r_dwPointV3TargetTolerance "0"
set r_dwPointV3SurfaceFirst "0"
set r_dwPointV3SurfaceLast "500000"
set r_dwPointV3InspectSurface "-1"
set r_dwPointV3ListLight "-1"
vid_restart
"""
        files[f"Main/DW_PS_V3_{mode_name}.cfg"]=config.encode("utf-8")
    manifest={"type":"DIAGNOSTIC_ONLY","accepted_release_run":41019985033,"accepted_artifact_id":12960988233,
       "accepted_release_zip_sha256":sha(payload),"accepted_renderer_sha256":BASE_SHA,
       "diagnostic_renderer_sha256":sha(newdll),"new_cvars":{"r_dwPointCasterScope":"V1 0=all;1=BSP;2=entities","r_dwPointReceiverPath":"V1 0=all;1=legacy bypass","r_dwPointNearWorldClip":"0..32 units per-fragment point BSP clip; LATCH","r_dwPointOriginAxis":"0 off,1 X,2 Y,3 Z; LATCH","r_dwPointOriginShift":"signed -16..16 units, capture origin and receiver sampling; LATCH"},
       "preset_cfgs":[f"Main/DW_PS_V3_{x[0]}.cfg" for x in modes],
       "original_files_preserved_except_renderer_and_sha":len(original)-2,
       "accepted_default_caster_receiver_coverage":"preserved in 0/0",
       "change_to_sun_hdr16f":False,"change_to_fire_world_mask":False,
       "change_to_glsl":"V2 debug shadowfill only, V3 shader unchanged","gpu_visual_validation":"PENDING","patch_proof":patch}
    files["docs/DW_POINT_SHADOW_GEOMETRY_FIDELITY_V3_MANIFEST.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
    files["docs/SHA256SUMS.txt"]="".join(f"{sha(files[n])}  {n}\n" for n in sorted(files) if n!="docs/SHA256SUMS.txt").encode()
    assert len(files)==62
    assert all(files[n]==original[n] for n in original if n not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt"))
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    out=outdir/(NAME+".zip")
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for n in sorted(files):
            info=zipfile.ZipInfo(NAME+"/"+n,(2026,10,30,12,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,files[n],compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None and len(z.namelist())==62
        for line in z.read(NAME+"/docs/SHA256SUMS.txt").decode().splitlines():
            h,n=line.split("  ",1)
            assert sha(z.read(NAME+"/"+n))==h,n
    h=sha(out.read_bytes())
    (outdir/(out.name+".sha256")).write_text(h+"  "+out.name+"\n")
    print("DW_POINT_SHADOW_GEOMETRY_FIDELITY_V3_DIAG_RELEASE_PASS",h)
if __name__=="__main__":
    assert len(sys.argv)==5
    package(*map(Path,sys.argv[1:]))
