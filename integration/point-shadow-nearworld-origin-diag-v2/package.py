#!/usr/bin/env python3
"""Pack point-shadow test DLL atop immutable user-accepted #41019985033 archive."""
import hashlib,io,json,sys,zipfile
from pathlib import Path

NAME="DarkWolf_PointShadow_NearWorld_Origin_Diagnostic_V2_From_41019985033_Win64"
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
    for mark in (b"r_dwPointCasterScope",b"r_dwPointReceiverPath",b"r_dwPointNearWorldClip",b"r_dwPointOriginAxis",b"r_dwPointOriginShift",b"_dwSunHalfRGBA16F"):
        assert mark in newdll,("missing marker",mark)
    patch=json.loads(Path(proof).read_text())
    assert patch["accepted_baseline_run"]==41019985033
    assert patch["sun_hdr16f_unchanged"] and patch["stage11_coverage_unchanged_at_defaults"] and patch["fire_world_mask_unchanged"]
    files=dict(original)
    files["renderer_sp_rend2_x64.dll"]=newdll
    readme="""DARKWOLF POINT SHADOW DIAGNOSTIC V2 (TEST ONLY).
Immutable accepted Clean Production baseline: #41019985033.
This package replaces ONLY the renderer DLL; all original game binaries/CFG remain.
Sky HDR16F, Stage11 full asset coverage, SSGI, CSM and Local/Fire preserved.
The legacy V1 CasterScope/ReceiverPath probes remain available.
NO CASTER OR RECEIVER IS REMOVED in the default mode.

INSTALL: back up renderer_sp_rend2_x64.dll; use this DLL in a SEPARATE COPY.
Remove previous diagnostic DLLs and external GLSL/PK3 overrides.

IDENTICAL CAMERA test (Factory ladder, spotlight, Crypt1 hanging fire):
/exec DW_PS_V2_A_ORIGINAL.cfg    - all assets, no diagnostic clip/shift
/exec DW_PS_V2_B_CLIP_8.cfg      - world/BSP fragment clipping near light: 8 units
/exec DW_PS_V2_C_CLIP_16.cfg     - 16 units
/exec DW_PS_V2_D_CLIP_24.cfg     - 24 units
/exec DW_PS_V2_E_Z_PLUS_4.cfg   - no clip, capture origin shifted +4 world Z
/exec DW_PS_V2_F_Z_MINUS_4.cfg  - no clip, shifted -4 world Z
/exec DW_PS_V2_G_X_PLUS_4.cfg   - no clip, shifted +4 world X
/exec DW_PS_V2_H_Y_PLUS_4.cfg   - no clip, shifted +4 world Y

Each CFG resets the other diagnostic controls to 0 and performs vid_restart.
Cvars are unarchived and LATCHED (vid_restart required):
  r_dwPointNearWorldClip 0..32
  r_dwPointOriginAxis 0=off,1=X,2=Y,3=Z
  r_dwPointOriginShift -16..16 world units
  r_dwPointCasterScope 0=all (V1), r_dwPointReceiverPath 0=all (V1)

BSP CLIP is per-fragment in shadowfill_fp, not a removal of whole assets:
some VERY CLOSE world shadow fragments are TEMPORARILY discarded.
This can cause light leaks through nearby walls. Diagnostic ONLY.
Origin offset moves shadow capture AND cubemap sampling origin, but
does not move direct-light origin or change brightness.
It may affect volumetric sampling; use for localization only.
If major wall leaks, unstable shadows or GPU errors appear, return to A.

Log shadow shape + leakage + FPS for each scene (same saved frame/exposure).
Do NOT conclude an asset is incorrectly classified just because its shadow
disappears during BSP near clip. The final production goal is full Stage11
caster/receiver coverage, improved physically plausible shadow shape.

RESET: /exec DW_PS_V2_A_ORIGINAL.cfg
Then restore the ORIGINAL clean renderer_sp_rend2_x64.dll #41019985033.
Do NOT merge V2 diagnostic mode into the Clean Production.
"""
    files["README_POINT_SHADOW_DIAGNOSTIC_V2.txt"]=readme.encode("utf-8")
    modes=[
        ("A_ORIGINAL",0,0,0),
        ("B_CLIP_8",8,0,0),
        ("C_CLIP_16",16,0,0),
        ("D_CLIP_24",24,0,0),
        ("E_Z_PLUS_4",0,3,4),
        ("F_Z_MINUS_4",0,3,-4),
        ("G_X_PLUS_4",0,1,4),
        ("H_Y_PLUS_4",0,2,4),
    ]
    for mode,clip,axis,shift in modes:
        config=f"""// DarkWolf Point Shadow Diagnostic V2: {mode}; TEST ONLY
set r_dwPointCasterScope "0"
set r_dwPointReceiverPath "0"
set r_dwPointNearWorldClip "{clip}"
set r_dwPointOriginAxis "{axis}"
set r_dwPointOriginShift "{shift}"
set r_dlightShadowStrength "0.88"
set r_dlightWorldContainment "2"
set r_dlightShadowSoftness "1.70"
set r_externalGLSL "0"
vid_restart
"""
        files[f"Main/DW_PS_V2_{mode}.cfg"]=config.encode("utf-8")
    manifest={"type":"DIAGNOSTIC_ONLY","accepted_release_run":41019985033,"accepted_artifact_id":12960988233,
       "accepted_release_zip_sha256":sha(payload),"accepted_renderer_sha256":BASE_SHA,
       "diagnostic_renderer_sha256":sha(newdll),"new_cvars":{"r_dwPointCasterScope":"V1 0=all;1=BSP;2=entities","r_dwPointReceiverPath":"V1 0=all;1=legacy bypass","r_dwPointNearWorldClip":"0..32 units per-fragment point BSP clip; LATCH","r_dwPointOriginAxis":"0 off,1 X,2 Y,3 Z; LATCH","r_dwPointOriginShift":"signed -16..16 units, capture origin and receiver sampling; LATCH"},
       "preset_cfgs":[f"Main/DW_PS_V2_{x[0]}.cfg" for x in modes],
       "original_files_preserved_except_renderer_and_sha":len(original)-2,
       "accepted_default_caster_receiver_coverage":"preserved in 0/0",
       "change_to_sun_hdr16f":False,"change_to_fire_world_mask":False,
       "change_to_glsl":"shadowfill_fp only, baked into DLL","gpu_visual_validation":"PENDING","patch_proof":patch}
    files["docs/DW_POINT_SHADOW_NEARWORLD_ORIGIN_V2_MANIFEST.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
    files["docs/SHA256SUMS.txt"]="".join(f"{sha(files[n])}  {n}\n" for n in sorted(files) if n!="docs/SHA256SUMS.txt").encode()
    assert len(files)==67
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
        assert z.testzip() is None and len(z.namelist())==67
        for line in z.read(NAME+"/docs/SHA256SUMS.txt").decode().splitlines():
            h,n=line.split("  ",1)
            assert sha(z.read(NAME+"/"+n))==h,n
    h=sha(out.read_bytes())
    (outdir/(out.name+".sha256")).write_text(h+"  "+out.name+"\n")
    print("DW_POINT_SHADOW_NEARWORLD_ORIGIN_V2_DIAG_RELEASE_PASS",h)
if __name__=="__main__":
    assert len(sys.argv)==5
    package(*map(Path,sys.argv[1:]))
