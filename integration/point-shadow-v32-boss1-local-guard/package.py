#!/usr/bin/env python3
"""Pack point-shadow test DLL atop immutable user-accepted #41019985033 archive."""
import hashlib,io,json,sys,zipfile
from pathlib import Path

NAME="DarkWolf_PointShadow_V32_Boss1_SourceLocalFixtureGuard_TEST_ONLY_41019985033_Win64"
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
    for mark in (b"r_dwPointCasterScope",b"r_dwPointReceiverPath",b"r_dwPointNearWorldClip",b"r_dwPointOriginAxis",b"r_dwPointOriginShift",b"_dwSunHalfRGBA16F", b"r_dwPointV3Mode", b"r_dwPointV3TargetTolerance", b"r_dwPointV3InspectSurface", b"r_dwPointV31AutoAudit", b"r_dwPointV32FixtureGuard", b"DW_PS_V32_GUARD_APPLIED"):
        assert mark in newdll,("missing marker",mark)
    patch=json.loads(Path(proof).read_text())
    assert patch["base"]==41019985033
    assert patch["guard_default"]==0 and patch["worldSurface"]==7232 and patch["otherPointLightsCasterUnmodified"] and patch["visibleSceneGeometryUnmodified"] and patch["sunFireTeslaVolumetricUnmodified"]
    files=dict(original)
    files["renderer_sp_rend2_x64.dll"]=newdll
    files["README_POINT_SHADOW_V32_SOURCE_LOCAL_GUARD.txt"]=Path(
        "integration/point-shadow-v32-boss1-local-guard/README_GPU_TEST_RU.md").read_bytes()
    for cfg_name in ("DW_PS_V32_BOSS1_AUTOTEST.cfg","DW_PS_V32_BOSS1_RESET.cfg"):
        files["Main/"+cfg_name]=Path("integration/point-shadow-v32-boss1-local-guard/"+cfg_name).read_bytes()
    manifest={"type":"V32_SOURCE_LOCAL_FIXTURE_GUARD_EXPERIMENT_ONLY","accepted_release_run":41019985033,"accepted_artifact_id":12960988233,
       "accepted_release_zip_sha256":sha(payload),"accepted_renderer_sha256":BASE_SHA,
       "diagnostic_renderer_sha256":sha(newdll),"new_cvars":{"r_dwPointV32FixtureGuard":"0=OFF default,1=only boss1 surface7232 for capture(-2764,-219,-24), CVAR_LATCH; no global material removal"},
       "preset_cfgs":["Main/DW_PS_V32_BOSS1_AUTOTEST.cfg","Main/DW_PS_V32_BOSS1_RESET.cfg"],
       "original_files_preserved_except_renderer_and_sha":len(original)-2,
       "accepted_default_caster_receiver_coverage":"preserved in 0/0",
       "change_to_sun_hdr16f":False,"change_to_fire_world_mask":False,
       "change_to_glsl":"V2 diagnostic base unchanged; V3.2 modifies no shader","gpu_visual_validation":"PENDING","patch_proof":patch}
    files["docs/DW_POINT_SHADOW_V32_BOSS1_LOCAL_GUARD_MANIFEST.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
    files["docs/SHA256SUMS.txt"]="".join(f"{sha(files[n])}  {n}\n" for n in sorted(files) if n!="docs/SHA256SUMS.txt").encode()
    assert len(files)==61
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
        assert z.testzip() is None and len(z.namelist())==61
        for line in z.read(NAME+"/docs/SHA256SUMS.txt").decode().splitlines():
            h,n=line.split("  ",1)
            assert sha(z.read(NAME+"/"+n))==h,n
    h=sha(out.read_bytes())
    (outdir/(out.name+".sha256")).write_text(h+"  "+out.name+"\n")
    print("DW_PS_V32_SOURCE_LOCAL_FIXTURE_RELEASE_PASS",h)
if __name__=="__main__":
    assert len(sys.argv)==5
    package(*map(Path,sys.argv[1:]))
