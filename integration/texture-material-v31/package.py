#!/usr/bin/env python3
"""V3.1 read-only model policy diagnostics, byte-pinned exact V3 parent.

Preserve every original V3 file except renderer DLL and checksum manifest;
add only a console report and optional text guidance, never alter V2 or V3.
"""
import argparse,hashlib,io,json,struct,zipfile
from pathlib import Path

OUT_NAME="DarkWolf_Texture_Material_V31_Model_Diagnostic_ExactV3_Win64"
PARENT_DLL_HASH="a54b037f8dc7685a86c2d389168e414793fe4b5e69361406cab736a81cd195f6"
V3_RUN=41202805738
SOURCE_RUN=41019985033
H=lambda b:hashlib.sha256(b).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--v3-artifact",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--source-proof",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.v3_artifact) as z:
        assert z.testzip() is None
        nested=[n for n in z.namelist() if n.startswith("dist/") and n.endswith(".zip") and "Fidelity_V3_Experimental" in n]
        assert len(nested)==1,("V3 parent artefact mismatch",nested)
        v3zip=z.read(nested[0])
        hashname=[n for n in z.namelist() if n.startswith("dist/") and n.endswith(".zip.sha256")]
        assert len(hashname)==1,hashname
        checksum=z.read(hashname[0]).decode().strip().split()[0]
        assert H(v3zip)==checksum,("V3 parent checksum drift",H(v3zip),checksum)
    with zipfile.ZipFile(io.BytesIO(v3zip)) as z:
        assert z.testzip() is None
        original={name:z.read(name) for name in z.namelist() if not name.endswith("/")}
    roots={n.split("/")[0] for n in original}
    assert len(roots)==1,roots
    prefix=next(iter(roots))+"/"
    dll=prefix+"renderer_sp_rend2_x64.dll"
    sums=prefix+"docs/SHA256SUMS.txt"
    assert dll in original and sums in original
    assert H(original[dll])==PARENT_DLL_HASH,(dll,H(original[dll]))
    assert any(n.endswith("/Main/DW_HDR16F_V1_QUALITY.cfg") for n in original)
    newdll=a.renderer.read_bytes()
    assert len(newdll)>2800000 and newdll[:2]==b"MZ"
    peoff=struct.unpack_from("<I",newdll,60)[0]
    assert newdll[peoff:peoff+4]==b"PE\0\0"
    assert b"r_dwModelTextureScope" in newdll, "V3 scope CVar missing"
    assert b"r_dwModelFidelityReport" in newdll, "V3.1 diagnostic command missing"
    for name in (b"r_dwTextureFidelity",b"r_dwMaterialFidelity",b"r_dwA2C",b"r_dwCas",b"r_dwLut",b"r_ssgi",b"r_bloom"):
        assert name in newdll,("required CVar missing",name)
    assert H(newdll)!=PARENT_DLL_HASH, "instrumented DLL must differ from V3"
    files=dict(original)
    files[dll]=newdll
    proof=json.loads(a.source_proof.read_text())
    assert len(proof["changed_files"])==3
    assert proof["render_algorithms_modified"] is False
    assert proof["cvar_defaults_modified"] is False
    assert proof["diagnostic_command"].startswith("r_dwModelFidelityReport")
    manifest={
        "release":OUT_NAME,
        "status":"EXPERIMENTAL_V31_DIAGNOSTIC_GPU_NOT_YET_VALIDATED",
        "immutable_base_production_run":SOURCE_RUN,
        "frozen_v2_run":41200040113,
        "immutable_parent_v3_run":V3_RUN,
        "parent_v3_renderer_sha256":PARENT_DLL_HASH,
        "new_diagnostic_renderer_sha256":H(newdll),
        "render_algorithms_modified":False,
        "renderer_cvar_defaults_modified":False,
        "additional_command":"r_dwModelFidelityReport [optional substring|all]",
        "V3_opt_in_scope_default":"0 (unchanged)",
        "original_v3_files_identical_except_renderer_and_sha_manifest":True,
        "source_changes_only":["SP/code/rend2/tr_image.c","SP/code/rend2/tr_local.h",
                               "SP/code/rend2/tr_init.c"],
        "other_effects_source_modified":False,
        "new_gpu_tests_user_required":True,
        "visual_acceptance":"NOT_APPLICABLE_DIAGNOSTIC_ONLY"
    }
    files[prefix+"docs/DW_V31_DIAGNOSTIC_SOURCE_PROOF.json"]=json.dumps(proof,indent=2).encode()
    files[prefix+"docs/DW_V31_DIAGNOSTIC_RELEASE_AUDIT.json"]=json.dumps(manifest,indent=2).encode()
    files[prefix+"README_DW_V31_MODEL_DIAGNOSTIC_RU.txt"]=(
        "DarkWolf V3.1 Model Fidelity Diagnostic -- NOT a new Clean Production.\n"
        "Exact parent V3 Actions #41202805738; V2 Clean and base #41019985033 untouched.\n"
        "Only renderer diagnostic tracing and report command were added.\n"
        "All original V3 files/configs byte-identical except renderer DLL and SHA manifest.\n"
        "\n"
        "HOW TO COLLECT A/B POLICY REPORTS ON ONE MAP AND CAMERA:\n"
        "  /exec DW_V3_SCOPE_0_V2_PARITY.cfg\n"
        "  After vid_restart and map loading: /r_dwModelFidelityReport powerups\n"
        "  /condump dw_v31_scope0.txt\n"
        "  /exec DW_V3_SCOPE_1_EXTENDED_MODELS.cfg\n"
        "  After vid_restart and map loading: /r_dwModelFidelityReport powerups\n"
        "  /condump dw_v31_scope1.txt\n"
        "Upload BOTH txt files; optional analyze_reports.py compares exact GPU formats.\n"
        "Read policy=FLAG_ADDED as an actual V3 flag intervention, NOT proof of visual improvement.\n"
        "RGB, POT and already uncompressed textures typically show no useful difference.\n"
        "No cvar changes needed beyond the accepted V3 scope configurations.\n"
        "No new filter or mip behavior is introduced by diagnostic V3.1.\n"
    ).encode()
    # Every V3 parent binary/profile remains byte-identical except renderer DLL + SHA index.
    for key,data in original.items():
        if key not in (dll,sums):
            assert files[key]==data,("baseline changed",key)
    files[sums]="".join(
       H(data)+"  "+k[len(prefix):]+"\n" for k,data in sorted(files.items()) if k!=sums
    ).encode()
    out=a.out/(OUT_NAME+".zip")
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,1,12,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            z.writestr(info,data)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for key,val in original.items():
            if key not in (dll,sums):assert z.read(key)==val,("file drift",key)
        assert z.read(dll)==newdll
        for row in z.read(sums).decode().splitlines():
            digest,rel=row.split("  ",1)
            assert H(z.read(prefix+rel))==digest,rel
    final=H(out.read_bytes())
    (a.out/(OUT_NAME+".zip.sha256")).write_text(final+"  "+out.name+"\n")
    manifest["final_zip_sha256"]=final
    manifest["preserved_original_v3_files"]=len(original)-2
    manifest["total_files"]=len(files)
    (a.out/"DW_V31_DIAGNOSTIC_FINAL_AUDIT.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("DW_V31_DIAGNOSTIC_ZIP_AND_EXACT_V3_INHERITANCE_PASS",out,final,flush=True)

if __name__=="__main__":
    main()
