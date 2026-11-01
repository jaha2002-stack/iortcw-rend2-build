#!/usr/bin/env python3
"""Pack point-shadow test DLL atop immutable user-accepted #41019985033 archive."""
import hashlib,io,json,sys,zipfile
from pathlib import Path

NAME="DarkWolf_PointShadow_V31_OneShot_Caster_Attribution_TEST_ONLY_41019985033_Win64"
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
    for mark in (b"r_dwPointCasterScope",b"r_dwPointReceiverPath",b"r_dwPointNearWorldClip",b"r_dwPointOriginAxis",b"r_dwPointOriginShift",b"_dwSunHalfRGBA16F", b"r_dwPointV3Mode", b"r_dwPointV3TargetTolerance", b"r_dwPointV3InspectSurface", b"r_dwPointV31AutoAudit"):
        assert mark in newdll,("missing marker",mark)
    patch=json.loads(Path(proof).read_text())
    assert patch["accepted_baseline_run"]==41019985033
    assert patch["diagnostic_matches_only_selected_capture"] and patch["no_change_to_GL_shaders"] and patch["no_change_to_capture_origin_depth_or_casting"] and patch["other_effects_and_production_untouched"]
    files=dict(original)
    files["renderer_sp_rend2_x64.dll"]=newdll
    readme="""DARKWOLF POINT SHADOW V3.1 ONE-SHOT BSP AUTO AUDIT - TEST ONLY
Accepted clean production #41019985033 is immutable. V3.1 extends V3.
For this exact Boss1 scene one command:
/exec DW_PS_V31_BOSS1_AUTO.cfg
This automatically resets previous V1/V2/V3 modifications to baseline,
selects source capture=(-2764,-219,-24) from user GPU A/B/C test,
records candidate geometry from world surface IDs 3637..7273, and
writes dw_ps_v31_boss1_auto.json to active game writable filesystem
(e.g. Main or user homepath). No condump or manual binary search.
Look for DW_PS_V31_AUTOREPORT_OK in the game console.
The report includes the selected source, range, depth-candidate list,
spatial bounds, shader material, distance and approximate apparent size.
It does NOT identify the GPU depth-winning caster/pixel; the entries
are candidates, not confirmed shadow owners. No visual fix is applied.
Do not ship V1/V2/V3/V31 diagnostics in Clean Production.
Once done: /exec DW_PS_V3_A_BASELINE.cfg and restore original renderer.
"""
    files["README_POINT_SHADOW_V31_AUTO.txt"]=readme.encode("utf-8")
    files["Main/DW_PS_V31_BOSS1_AUTO.cfg"]=Path(
        "integration/point-shadow-v31-oneshot-audit/DW_PS_V31_BOSS1_AUTO.cfg").read_bytes()
    manifest={"type":"V31_ONE_SHOT_DIAGNOSTIC_ONLY","accepted_release_run":41019985033,"accepted_artifact_id":12960988233,
       "accepted_release_zip_sha256":sha(payload),"accepted_renderer_sha256":BASE_SHA,
       "diagnostic_renderer_sha256":sha(newdll),"new_cvars":{"r_dwPointV31AutoAudit":"0=no effect;1=one-shot JSON (non-archived)","r_dwPointV3Mode":"0=all unchanged;1/2=V3 diagnostic filtering","r_dwPointV3SourceXYZ":"selected capture coordinates, V3 LATCH","r_dwPointV3SurfaceFirstLast":"BSP surface ID interval, V3 LATCH"},
       "preset_cfgs":["Main/DW_PS_V31_BOSS1_AUTO.cfg"],
       "original_files_preserved_except_renderer_and_sha":len(original)-2,
       "accepted_default_caster_receiver_coverage":"preserved in 0/0",
       "change_to_sun_hdr16f":False,"change_to_fire_world_mask":False,
       "change_to_glsl":"V2 debug shadowfill retained unchanged, V3.1 does not alter any shader","gpu_visual_validation":"PENDING","patch_proof":patch}
    files["docs/DW_POINT_SHADOW_V31_ONESHOT_MANIFEST.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
    files["docs/SHA256SUMS.txt"]="".join(f"{sha(files[n])}  {n}\n" for n in sorted(files) if n!="docs/SHA256SUMS.txt").encode()
    assert len(files)==60
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
        assert z.testzip() is None and len(z.namelist())==60
        for line in z.read(NAME+"/docs/SHA256SUMS.txt").decode().splitlines():
            h,n=line.split("  ",1)
            assert sha(z.read(NAME+"/"+n))==h,n
    h=sha(out.read_bytes())
    (outdir/(out.name+".sha256")).write_text(h+"  "+out.name+"\n")
    print("DW_PS_V31_ONESHOT_RELEASE_PASS",h)
if __name__=="__main__":
    assert len(sys.argv)==5
    package(*map(Path,sys.argv[1:]))
