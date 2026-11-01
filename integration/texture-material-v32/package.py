#!/usr/bin/env python3
"""Byte-pinned packaging of V3.2 from exact V3.1 #41283547717.

Only renderer DLL + SHA index replaced; every inherited V3.1 file, including
the five quality presets, games, shaders and launchers, is byte-for-byte retained.
"""
import argparse,hashlib,io,json,struct,zipfile
from pathlib import Path

NAME="DarkWolf_Texture_Material_V32_Model_Sampling_Experimental_Win64"
PARENT_SHA="c3656b2dd8de566ac07a93628f94024755fa42ce2649eeb195ac890a4fd7b722"
H=lambda b:hashlib.sha256(b).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--v31-artifact",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--source-proof",type=Path,required=True)
    p.add_argument("--native-proof",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.v31_artifact) as outer:
        assert outer.testzip() is None
        nested=[x for x in outer.namelist()
             if x.startswith("dist/") and x.endswith(".zip") and "V31_Model_Diagnostic_ExactV3" in x]
        assert len(nested)==1,("exact V3.1 artifact not found",nested)
        raw=outer.read(nested[0])
        checks=[x for x in outer.namelist() if x.endswith(".zip.sha256")]
        assert len(checks)==1,checks
        assert H(raw)==outer.read(checks[0]).decode().split()[0], "parent ZIP SHA mismatch"
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        parent={x:z.read(x) for x in z.namelist() if not x.endswith("/")}
    roots={x.split("/")[0] for x in parent}
    assert len(roots)==1,roots
    root=next(iter(roots))+"/"
    renderer_name=root+"renderer_sp_rend2_x64.dll"
    hashes=root+"docs/SHA256SUMS.txt"
    assert H(parent[renderer_name])==PARENT_SHA,H(parent[renderer_name])
    assert hashes in parent
    new=a.renderer.read_bytes()
    assert new[:2]==b"MZ" and len(new)>2800000
    pe=struct.unpack_from("<I",new,60)[0]
    assert new[pe:pe+4]==b"PE\0\0"
    for name in (b"r_dwTextureFidelity",b"r_dwModelTextureScope",b"r_dwModelFidelityReport",
                 b"r_dwModelMipBias",b"r_dwA2C",b"r_dwCas",b"r_dwLut",
                 b"r_ssgi",b"r_bloom"):
        assert name in new,("missing accepted CVar",name)
    assert H(new)!=PARENT_SHA
    source=json.loads(a.source_proof.read_text())
    native=json.loads(a.native_proof.read_text())
    paths=set(source["changed_source_files"])
    assert paths=={"SP/code/rend2/tr_init.c","SP/code/rend2/tr_local.h","SP/code/rend2/tr_image.c"},paths
    assert native["pass"] and native["config_default_zero"]
    assert source["new_cvar"]["r_dwModelMipBias"]["default"]=="0"
    assert source["no_global_texture_filter_change"] and source["anisotropy_unchanged"]
    files=dict(parent);files[renderer_name]=new

    files[root+"Main/DW_V32_MODEL_LOD_0_PARITY.cfg"]=(
      "// Exact V3.1 image sampling (control), scoped model classes only\n"
      "seta r_dwTextureFidelity \"1\"\n"
      "seta r_dwModelTextureScope \"1\"\n"
      "seta r_dwModelMipBias \"0\"\n"
      "vid_restart\n").encode()
    files[root+"Main/DW_V32_MODEL_LOD_NEG025_TEST.cfg"]=(
      "// Model 2D color mip samples ONLY: bias -0.25. World and FX untouched\n"
      "seta r_dwTextureFidelity \"1\"\n"
      "seta r_dwModelTextureScope \"1\"\n"
      "seta r_dwModelMipBias \"-0.25\"\n"
      "vid_restart\n").encode()
    files[root+"README_DW_V32_EXPERIMENTAL_RU.txt"]=(
      "DARKWOLF Texture and Material V3.2 -- experimental model sampling only.\n"
      "Parent: EXACT V3.1 GitHub Actions #41283547717 derived from V2 Clean #41200040113\n"
      "and original Clean Production #41019985033. No accepted base modified.\n"
      "\n"
      "DEFAULT: r_dwModelMipBias 0. No extra GL texture param call at 0.\n"
      "Opt-in values: -0.25 test, minimum -0.50; negative bias can shimmer.\n"
      "Does not change geometry, textures, mip generation, global filtering,\n"
      "16x anisotropy, A2C/CAS/LUT, HDR, bloom, volumetrics, SSGI or shadows.\n"
      "Restricted to allowlisted 2D color model textures with mipmaps:\n"
      "models/players, models/weapons, models/weapons2; extended V3 paths\n"
      "only when r_dwModelTextureScope 1. Mapobjects, BSP, UI, sky excluded.\n"
      "\n"
      "A/B TEST ON IDENTICAL CAMERA, MAP, SCENE:\n"
      "1. /exec DW_V32_MODEL_LOD_0_PARITY.cfg\n"
      "2. /r_dwModelFidelityReport powerups\n"
      "3. /condump DW_V32_LOD0.txt\n"
      "4. Screenshot close & mid-distance, inspect moving shimmering.\n"
      "5. /exec DW_V32_MODEL_LOD_NEG025_TEST.cfg\n"
      "6. /r_dwModelFidelityReport powerups\n"
      "7. /condump DW_V32_LOD_NEG025.txt\n"
      "8. Repeat screenshots and movement. Revert to 0 if alias/shimmer.\n"
      "GL bias request does not invent texture detail; never install as\n"
      "Clean Production before the user accepts real Windows GPU images.\n"
    ).encode()
    files[root+"docs/DW_V32_SOURCE_PROOF.json"]=json.dumps(source,indent=2).encode()
    files[root+"docs/DW_V32_NATIVE_TEST.json"]=json.dumps(native,indent=2).encode()
    manifest={
      "release":NAME,"status":"EXPERIMENTAL_NOT_USER_GPU_ACCEPTED",
      "parent_release":"DarkWolf Texture Material V3.1 Diagnostic Actions 41283547717",
      "source_clean_run":41019985033,"frozen_v2_clean_run":41200040113,
      "parent_sha256":PARENT_SHA,"new_renderer_sha256":H(new),
      "only_changed_source_files":sorted(paths),
      "preserved_parent_files_except_renderer_and_sha":len(parent)-2,
      "unchanged_games_profiles_shaders":True,
      "global_texture_filter_modified":False,
      "LOD_bias_default":"0",
      "A2C_CAS_LUT_HDR_Bloom_CSM_SSGI_Volumetric_modified":False,
      "new_configuration_files":["Main/DW_V32_MODEL_LOD_0_PARITY.cfg",
                                 "Main/DW_V32_MODEL_LOD_NEG025_TEST.cfg"],
      "runtime_gpu_image_acceptance":"PENDING"}
    files[root+"docs/DW_V32_RELEASE_AUDIT.json"]=json.dumps(manifest,indent=2).encode()
    for name,data in parent.items():
        if name not in (renderer_name,hashes):
            assert files[name]==data,("unintended base change",name)
    files[hashes]="".join(H(data)+"  "+k[len(root):]+"\n"
             for k,data in sorted(files.items()) if k!=hashes).encode()
    out=a.out/(NAME+".zip")
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,1,16,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            z.writestr(info,data)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for name,data in parent.items():
            if name not in (renderer_name,hashes):
                assert z.read(name)==data,name
        assert z.read(renderer_name)==new
        for line in z.read(hashes).decode().splitlines():
            digest,local=line.split("  ",1)
            assert H(z.read(root+local))==digest,local
    digest=H(out.read_bytes())
    (a.out/(NAME+".zip.sha256")).write_text(digest+"  "+out.name+"\n")
    manifest["final_zip_sha256"]=digest
    manifest["files_total"]=len(files)
    manifest["unchanged_parent_files_verified"]=len(parent)-2
    (a.out/"DW_V32_RELEASE_AUDIT.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("DW_V32_BYTE_EXACT_PARENT_PRESERVATION_AND_ZIP_PASS",digest,flush=True)

if __name__=="__main__":main()
