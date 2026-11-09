#!/usr/bin/env python3
from pathlib import Path
import io, zipfile, hashlib, json, struct, sys

if len(sys.argv) != 4:
    raise SystemExit("usage: package_v42_test_release.py <base_outer_zip> <renderer_dll> <out_dir>")

base_outer=Path(sys.argv[1])
renderer=Path(sys.argv[2])
outdir=Path(sys.argv[3])
outdir.mkdir(parents=True,exist_ok=True)
H=lambda b:hashlib.sha256(b).hexdigest()
NL=chr(10)

outer=zipfile.ZipFile(base_outer)
inners=[n for n in outer.namelist() if n.lower().endswith(".zip")]
assert len(inners)==1, inners
z=zipfile.ZipFile(io.BytesIO(outer.read(inners[0])))
assert z.testzip() is None
entries={n:z.read(n) for n in z.namelist() if not n.endswith("/")}
roots={n.split("/",1)[0] for n in entries if "/" in n}
assert len(roots)==1, roots
oldroot=next(iter(roots))
root=oldroot+"/"

renderer_key=root+"renderer_sp_rend2_x64.dll"
old=entries[renderer_key]
EXPECTED_BASE="0b2ff0b28bbf69ff0df73417866eb330eb204c10b5be5fb0835b98f26797cc2d"
assert H(old)==EXPECTED_BASE,(H(old),EXPECTED_BASE)

new=renderer.read_bytes()
assert new[:2]==b"MZ"
pe=struct.unpack_from("<I",new,60)[0]
assert new[pe:pe+4]==b"PE\x00\x00"
entries[renderer_key]=new

cfgs={
    "DW_PBR_LEGACY_OFF.cfg":[
        'seta r_pbr "0"',
        "vid_restart",
    ],
    "DW_PBR_LEGACY_V1.cfg":[
        'seta r_pbr "1"',
        'seta r_normalMapping "1"',
        'seta r_specularMapping "1"',
        'seta r_cubeMapping "1"',
        "vid_restart",
    ],
    "DW_PBR2_CORE_ORM.cfg":[
        'seta r_pbr "2"',
        'seta r_normalMapping "1"',
        'seta r_specularMapping "1"',
        'seta r_cubeMapping "1"',
        "vid_restart",
    ],
    "DW_PBR3_BSP_RELIGHT_V42.cfg":[
        'seta r_pbr "3"',
        'seta r_normalMapping "1"',
        'seta r_specularMapping "1"',
        'seta r_cubeMapping "1"',
        "vid_restart",
    ],
}
for name,lines in cfgs.items():
    entries[root+"Main/"+name]=(NL.join(lines)+NL).encode("ascii")

readme=[
    "DarkWolf PBR V3 + BSP Relight V4.2 - Win64 TEST",
    "Exact base: Clean Production GitHub Run #42217883095",
    "Base commit: 0ef4fc401daff30c230ccb8226a8029fb0a3519f",
    "",
    "This package consolidates:",
    "  - all PBR V2/V3 renderer work from the earlier #42403630529 TEST release",
    "  - packed ORM support: R=AO, G=Roughness, B=Metallic",
    "  - exact sRGB/linear transfer for PBR2+",
    "  - GGX direct-light BRDF path",
    "  - conservative PBR3 environment BRDF / roughness LOD",
    "  - BSP Relight V4 directional baked-light reprojection",
    "  - BSP directional recovery V4.1",
    "  - BSP normal-aware diffuse IBL correction V4.2",
    "",
    "Modes:",
    "  r_pbr 0 = unchanged non-PBR baseline",
    "  r_pbr 1 = inherited Rend2 PBR compatibility",
    "  r_pbr 2 = modern PBR2 core + ORM",
    "  r_pbr 3 = PBR2 core + PBR3 IBL + BSP Relight V4.2",
    "",
    "Production default remains r_pbr 0.",
    "No TestLab auto-start, camera patch, developer overlay, or temporary test material is included.",
    "Existing Clean Production features from #42217883095 are preserved.",
    "",
    "Note: true offline GGX cubemap prefilter + full BRDF integration LUT remain a later PBR3 stage.",
]
entries[root+"README_DARKWOLF_PBR3_BSP_RELIGHT_V42_TEST.txt"]=(NL.join(readme)+NL).encode("utf-8")

for k in list(entries):
    if k.endswith("/SHA256SUMS.txt") or k.endswith("/SHA256SUMS_PBR_V2_V3.txt"):
        del entries[k]

entries[root+"SHA256SUMS_PBR3_V42.txt"]="".join(
    H(v)+"  "+k[len(root):]+NL for k,v in sorted(entries.items())
).encode("ascii")

newroot="DarkWolf_PBR3_BSP_Relight_V42_From_42217883095_Win64_TEST"
target=outdir/(newroot+".zip")
with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as out:
    for k,v in sorted(entries.items()):
        rel=k[len(root):]
        out.writestr(newroot+"/"+rel,v)
with zipfile.ZipFile(target) as check:
    assert check.testzip() is None

proof={
    "base_run":42217883095,
    "base_commit":"0ef4fc401daff30c230ccb8226a8029fb0a3519f",
    "base_renderer_sha256":H(old),
    "new_renderer_sha256":H(new),
    "package_sha256":H(target.read_bytes()),
    "renderer_mode":"PBR V3 + BSP Relight V4.2",
    "r_pbr_default":0,
    "orm":"R=AO G=Roughness B=Metallic",
    "testlab_runtime_patches_included":False,
    "cubemap_capture_changed":False,
    "true_ggx_prefilter_and_brdf_lut":"deferred"
}
(outdir/"PBR3_V42_RELEASE_PROOF.json").write_text(json.dumps(proof,indent=2)+NL)
Path(str(target)+".sha256").write_text(H(target.read_bytes())+"  "+target.name+NL)
print(json.dumps(proof,indent=2))
