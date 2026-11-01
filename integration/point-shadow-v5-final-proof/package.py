#!/usr/bin/env python3
"""Pack point-shadow test DLL atop immutable user-accepted #41019985033 archive."""
import hashlib,io,json,sys,zipfile
from pathlib import Path

NAME="DarkWolf_PointShadow_V5_CrossMap_SourceLocal_PROOF_FINAL_ATTEMPT_41019985033_Win64"
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
    for mark in (b"r_dwPointCasterScope",b"r_dwPointReceiverPath",b"r_dwPointNearWorldClip",b"r_dwPointOriginAxis",b"r_dwPointOriginShift",b"_dwSunHalfRGBA16F", b"r_dwPointV3Mode", b"r_dwPointV3TargetTolerance", b"r_dwPointV3InspectSurface", b"r_dwPointV31AutoAudit", b"r_dwPointV32FixtureGuard", b"DW_PS_V32_GUARD_APPLIED", b"r_dwPointV4Scan", b"r_dwPointV4Mode", b"DW_PS_V4_SOURCE_LOCAL_SKIP", b"DW_PS_V4_REPORT_OK", b"r_dwPointV5ProofMode", b"r_dwPointV5ProofAudit", b"DW_PS_V5_SOURCE_LOCAL_SKIP", b"DW_PS_V5_PROOF_REPORT_OK"):
        assert mark in newdll,("missing marker",mark)
    patch=json.loads(Path(proof).read_text())
    assert patch["accepted_base_run"]==41019985033
    assert patch["safe_default_mode"]==0 and patch["safe_default_audit"]==0
    assert patch["no_global_material_suppression"] and patch["no_hardcoded_bsp_ids_or_material_names"]
    assert patch["strict_one_source_current_map_only"] and patch["fire_tesla_sun_and_other_light_casters_preserved"]
    assert patch["stage11_full_casters_and_receivers_preserved_at_defaults"]
    files=dict(original)
    files["renderer_sp_rend2_x64.dll"]=newdll
    files["README_POINT_SHADOW_V5_LAST_PROOF.txt"]=Path(
        "integration/point-shadow-v5-final-proof/README_GPU_TEST_RU.md").read_bytes()
    for cfg_name in ("DW_PS_V5_PROOF_AUTOTEST.cfg","DW_PS_V5_RESET.cfg"):
        files["Main/"+cfg_name]=Path("integration/point-shadow-v5-final-proof/"+cfg_name).read_bytes()
    for collector_name in ("COLLECT_DW_PS_V5.cmd","COLLECT_DW_PS_V5.ps1"):
        files[collector_name]=Path("integration/point-shadow-v5-final-proof/"+collector_name).read_bytes()
    manifest={"type":"V5_SECOND_AND_FINAL_CROSSMAP_PROOF_NOT_PRODUCTION",
       "accepted_release_run":41019985033,"accepted_artifact_id":12960988233,
       "accepted_release_zip_sha256":sha(payload),"accepted_renderer_sha256":BASE_SHA,
       "experimental_renderer_sha256":sha(newdll),
       "new_cvars":{"r_dwPointV5ProofMode":"0=OFF default; 1=conservative source-local repair hypothesis; 2=source cage/ladder control; 3=union control",
                    "r_dwPointV5ProofAudit":"0=OFF; 1=proof JSON/logging only in test",
                    "r_dwPointV4Scan":"1 enabled by test CFG for source selection; no global material exclusion"},
       "preset_cfgs":["Main/DW_PS_V5_PROOF_AUTOTEST.cfg","Main/DW_PS_V5_RESET.cfg"],
       "original_files_preserved_except_renderer_and_sha":len(original)-2,
       "default_caster_receiver_coverage":"preserved",
       "change_to_sun_hdr16f":False,"change_to_fire_world_mask":False,
       "change_to_glsl":False,"gpu_visual_validation":"PENDING second/last proof",
       "production_status":"NOT ACCEPTED; Clean only after all map proof PASS",
       "patch_proof":patch}
    files["docs/DW_POINT_SHADOW_V5_FINAL_PROOF_MANIFEST.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
    files["docs/SHA256SUMS.txt"]="".join(f"{sha(files[n])}  {n}\n" for n in sorted(files) if n!="docs/SHA256SUMS.txt").encode()
    assert len(files)==63
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
        assert z.testzip() is None and len(z.namelist())==63
        for line in z.read(NAME+"/docs/SHA256SUMS.txt").decode().splitlines():
            h,n=line.split("  ",1)
            assert sha(z.read(NAME+"/"+n))==h,n
    h=sha(out.read_bytes())
    (outdir/(out.name+".sha256")).write_text(h+"  "+out.name+"\n")
    print("DW_PS_V5_SECOND_FINAL_PROOF_RELEASE_PASS",h)
if __name__=="__main__":
    assert len(sys.argv)==5
    package(*map(Path,sys.argv[1:]))
