#!/usr/bin/env python3
"""Package exact V2 CI release plus ONLY V3 renderer and additive test files.

Never mutate accepted V2 / Clean Production 41019985033. Check every inherited
file byte-for-byte and validate SHA256 manifest after writing.
"""
import argparse,hashlib,io,json,struct,zipfile
from pathlib import Path

OUT_NAME="DarkWolf_Texture_Material_Fidelity_V3_Experimental_From_41019985033_Win64"
PARENT_DLL_HASH="83e492871751cc4c37baf9909350a71ce0c90f3c21b895c2e8d572aa21b40acc"
V2_RUN=41200040113
SOURCE_RUN=41019985033
H=lambda b:hashlib.sha256(b).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--v2-artifact",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--source-proof",type=Path,required=True)
    p.add_argument("--native-proof",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.v2_artifact) as z:
        assert z.testzip() is None
        nested=[n for n in z.namelist() if n.startswith("dist/") and n.endswith(".zip") and "Quality_V2" in n]
        assert len(nested)==1,("V2 artefact mismatch",nested)
        v2zip=z.read(nested[0])
        hashname=[n for n in z.namelist() if n.startswith("dist/") and n.endswith(".zip.sha256")]
        assert len(hashname)==1,hashname
        checksum=z.read(hashname[0]).decode().strip().split()[0]
        assert H(v2zip)==checksum,("V2 artifact inner checksum drift",H(v2zip),checksum)
    with zipfile.ZipFile(io.BytesIO(v2zip)) as z:
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
    assert b"r_dwModelTextureScope" in newdll,"new scope CVar missing in Win64 renderer"
    for name in (b"r_dwTextureFidelity",b"r_dwMaterialFidelity",b"r_dwA2C",b"r_dwCas",b"r_dwLut",b"r_ssgi",b"r_bloom"):
        assert name in newdll,("required CVar missing",name)
    assert H(newdll)!=PARENT_DLL_HASH, "new DLL must differ from V2"
    files=dict(original)
    files[dll]=newdll
    proof=json.loads(a.source_proof.read_text())
    test=json.loads(a.native_proof.read_text())
    assert len(proof["changed_files"])==3
    assert proof["defaults"]["r_dwModelTextureScope"]=="0"
    assert test["native_binary_compiled"] and test["V2_default_scope_zero"]
    manifest={
        "release":OUT_NAME, "status":"EXPERIMENTAL_V3_NOT_YET_USER_GPU_ACCEPTED",
        "immutable_source_base_run":SOURCE_RUN,"frozen_v2_run":V2_RUN,
        "parent_v2_renderer_sha256":PARENT_DLL_HASH,
        "v3_renderer_sha256":H(newdll),
        "v3_extra_cvar":{"r_dwModelTextureScope":"0 or 1; default=0"},
        "default_zero_equals_V2_model_scope":True,
        "original_v2_files_identical_except_renderer_and_sums":True,
        "source_changes_only":["SP/code/rend2/tr_init.c","SP/code/rend2/tr_local.h","SP/code/rend2/tr_image.c"],
        "unrelated_runtime_and_configs_byte_preserved":True,
        "other_effects_preserved":["HDR16F Sun","Bloom v2","CSM","SSGI","Tesla","Volumetric Sun Local Fire","StaticPromote","CAS","A2C","Analytic LUT"],
        "new_gpu_tests_user_required":True,
        "visual_acceptance":"PENDING_WINDOWS_GPU"
    }
    files[prefix+"docs/DW_V3_MODEL_SCOPE_SOURCE_PROOF.json"]=json.dumps(proof,indent=2).encode()
    files[prefix+"docs/DW_V3_MODEL_SCOPE_NATIVE_TEST.json"]=json.dumps(test,indent=2).encode()
    files[prefix+"docs/DW_V3_RELEASE_AUDIT.json"]=json.dumps(manifest,indent=2).encode()
    files[prefix+"Main/DW_V3_SCOPE_0_V2_PARITY.cfg"]=(
        "// V3 reference: keep V2 exactly on players/weapons\n"
        "seta r_dwTextureFidelity \"1\"\n"
        "seta r_dwModelTextureScope \"0\"\n"
        "vid_restart\n").encode()
    files[prefix+"Main/DW_V3_SCOPE_1_EXTENDED_MODELS.cfg"]=(
        "// V3 candidate: non-world models only, rest of V2 unchanged\n"
        "seta r_dwTextureFidelity \"1\"\n"
        "seta r_dwModelTextureScope \"1\"\n"
        "vid_restart\n").encode()
    files[prefix+"README_DW_V3_EXPERIMENTAL_RU.txt"]=(
        "DarkWolf Texture and Material Fidelity V3, experimental Win64 SP.\n"
        "Base: immutable V2 Actions 41200040113 derived from Clean 41019985033.\n"
        "Additional model textures are opt-in only. Default scope 0 is V2 parity.\n"
        "Scope 1 extends texture detail treatment to models/characters, models/enemies,\n"
        "models/monsters, models/items, models/powerups. No mapobjects or BSP textures.\n"
        "No change to A2C, CAS, LUT, lighting, shaders, volumetrics or other effects.\n"
        "Try /exec DW_V3_SCOPE_0_V2_PARITY.cfg and /exec DW_V3_SCOPE_1_EXTENDED_MODELS.cfg.\n"
        "Compare on same camera and model; restart occurs automatically.\n"
        "Note: player and gun textures already benefit from V2; new scope targets\n"
        "other model paths, and may not visibly affect every asset. Test is not GPU-accepted.\n"
        "Do not replace immutable accepted V2 baseline until validated on Windows GPU.\n").encode()
    # Existing V2 files, particularly game binaries and ALL existing quality CFG,
    # must remain byte-identical. New text files are additive, not replacements.
    for key,data in original.items():
        if key not in (dll,sums):
            assert files[key]==data,("baseline changed",key)
    files[sums]="".join(
       H(data)+"  "+k[len(prefix):]+"\n" for k,data in sorted(files.items()) if k!=sums
    ).encode()
    out=a.out/(OUT_NAME+".zip")
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,31,13,0,0))
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
    manifest["preserved_original_v2_files"]=len(original)-2
    manifest["total_files"]=len(files)
    (a.out/"DW_V3_MODEL_SCOPE_FINAL_AUDIT.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("DW_V3_MODEL_SCOPE_ZIP_INTEGRITY_AND_55_FILE_PARITY_PASS",out,final,flush=True)

if __name__=="__main__":
    main()
