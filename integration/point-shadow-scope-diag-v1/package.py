#!/usr/bin/env python3
"""Pack point-shadow test DLL atop immutable user-accepted #41019985033 archive."""
import hashlib,io,json,sys,zipfile
from pathlib import Path

NAME="DarkWolf_PointShadow_CasterReceiver_Diagnostic_V1_From_41019985033_Win64"
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
    for mark in (b"r_dwPointCasterScope",b"r_dwPointReceiverPath",b"_dwSunHalfRGBA16F"):
        assert mark in newdll,("missing marker",mark)
    patch=json.loads(Path(proof).read_text())
    assert patch["accepted_baseline_run"]==41019985033
    assert patch["sun_hdr16f_untouched"] and patch["stage11_all_casters_receivers_at_defaults"]
    files=dict(original)
    files["renderer_sp_rend2_x64.dll"]=newdll
    readme="""DARKWOLF POINT SHADOW TEST ONLY - based on accepted #41019985033.
Do NOT replace the accepted Clean Production or merge diagnostic CVar modes.
At 0/0 all Stage11 Caster/Receiver assets are enabled, exactly as before.
Test in a separate install with existing original map PK3s and identical CFG.
Remove any external GLSL or old diagnostic PK3.

At each SAME CAMERA on Factory ladder, Crypt1 hanging fire, and spotlight:
A. /r_dwPointCasterScope 0 ; /r_dwPointReceiverPath 0 ; /vid_restart
B. /r_dwPointCasterScope 1 ; /vid_restart   (only static world BSP casts)
C. /r_dwPointCasterScope 2 ; /vid_restart   (only scene entity/model casts)
D. /r_dwPointCasterScope 0 ; /vid_restart ; /r_dwPointReceiverPath 1
   (all casters, no legacy ProjectDlightTexture cubemap shadows)

Scope 0/1/2 is LATCHED: vid_restart is mandatory; inspect active value
with /r_dwPointCasterScope. Receiver Path 0/1 is runtime adjustable.
Do not turn off r_dlightShadowStrength or worldContainment during these tests.
For diagnostics only, settings 1/2 intentionally hide a subset of casters.
That is NOT a proposed rendering change; final full coverage is mandatory.

Reset: /r_dwPointCasterScope 0 ; /r_dwPointReceiverPath 0 ; /vid_restart
After testing restore original renderer_sp_rend2_x64.dll from #41019985033.
Sun HDR16F, Local/Fire, CSM, Sky, SSGI and all lighting remain unchanged.
"""
    files["README_POINT_SHADOW_DIAGNOSTIC_V1.txt"]=readme.encode("utf-8")
    manifest={"type":"DIAGNOSTIC_ONLY","accepted_release_run":41019985033,"accepted_artifact_id":12960988233,
       "accepted_release_zip_sha256":sha(payload),"accepted_renderer_sha256":BASE_SHA,
       "diagnostic_renderer_sha256":sha(newdll),"new_cvars":{"r_dwPointCasterScope":"0=all;1=static world BSP only;2=entity/model incl bmodel only;latched","r_dwPointReceiverPath":"0=all;1=legacy no point shadow;runtime"},
       "original_files_preserved_except_renderer_and_sha":len(original)-2,
       "accepted_default_caster_receiver_coverage":"preserved in 0/0",
       "change_to_sun_hdr16f":False,"change_to_fire_world_mask":False,
       "change_to_glsl":False,"gpu_visual_validation":"PENDING","patch_proof":patch}
    files["docs/DW_POINT_SHADOW_SCOPE_DIAG_V1_MANIFEST.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
    files["docs/SHA256SUMS.txt"]="".join(f"{sha(files[n])}  {n}\n" for n in sorted(files) if n!="docs/SHA256SUMS.txt").encode()
    assert len(files)==59
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
        assert z.testzip() is None and len(z.namelist())==59
        for line in z.read(NAME+"/docs/SHA256SUMS.txt").decode().splitlines():
            h,n=line.split("  ",1)
            assert sha(z.read(NAME+"/"+n))==h,n
    h=sha(out.read_bytes())
    (outdir/(out.name+".sha256")).write_text(h+"  "+out.name+"\n")
    print("DW_POINT_SHADOW_SCOPE_RECEIVER_V1_DIAG_RELEASE_PASS",h)
if __name__=="__main__":
    assert len(sys.argv)==5
    package(*map(Path,sys.argv[1:]))
