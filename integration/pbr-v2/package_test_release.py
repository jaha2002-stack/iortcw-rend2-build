#!/usr/bin/env python3
from pathlib import Path
import io, zipfile, hashlib, json, struct, sys

if len(sys.argv) != 4:
    raise SystemExit("usage: package_test_release.py <base_outer_zip> <build_artifact_dir> <out_dir>")

base_outer=Path(sys.argv[1])
build=Path(sys.argv[2])
outdir=Path(sys.argv[3])
outdir.mkdir(parents=True,exist_ok=True)
H=lambda b:hashlib.sha256(b).hexdigest()
NL=chr(10)

outer=zipfile.ZipFile(base_outer)
inners=[n for n in outer.namelist() if n.lower().endswith(".zip")]
assert len(inners)==1,inners
z=zipfile.ZipFile(io.BytesIO(outer.read(inners[0])))
assert z.testzip() is None
entries={n:z.read(n) for n in z.namelist() if not n.endswith("/")}
roots={n.split("/",1)[0] for n in entries if "/" in n}
assert len(roots)==1,roots
oldroot=next(iter(roots))
renderer_key=oldroot+"/renderer_sp_rend2_x64.dll"
old=entries[renderer_key]
EXPECTED_BASE="0b2ff0b28bbf69ff0df73417866eb330eb204c10b5be5fb0835b98f26797cc2d"
assert H(old)==EXPECTED_BASE,(H(old),EXPECTED_BASE)

new=(build/"build-binaries/renderer_sp_rend2_x64.dll").read_bytes()
assert new[:2]==b"MZ"
pe=struct.unpack_from("<I",new,60)[0]
assert new[pe:pe+4]==b"PE\x00\x00"
entries[renderer_key]=new
root=oldroot+"/"

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
    "DW_PBR2_CORE.cfg":[
        'seta r_pbr "2"',
        'seta r_normalMapping "1"',
        'seta r_specularMapping "1"',
        'seta r_cubeMapping "1"',
        "vid_restart",
    ],
    "DW_PBR2_MODERN_ORM.cfg":[
        'seta r_pbr "2"',
        'seta r_normalMapping "1"',
        'seta r_specularMapping "1"',
        'seta r_cubeMapping "1"',
        "vid_restart",
    ],
    "DW_PBR2_V3_IBL.cfg":[
        'seta r_pbr "3"',
        'seta r_normalMapping "1"',
        'seta r_specularMapping "1"',
        'seta r_cubeMapping "1"',
        "vid_restart",
    ],
}
for name,lines in cfgs.items():
    entries[root+"Main/"+name]=(NL.join(lines)+NL).encode("ascii")

readme_lines=[
    "DarkWolf PBR V2 V1-V3 - Win64 TEST",
    "Base: Clean Production #42217883095",
    "Validated build: #42402994791",
    "",
    "r_pbr 0 = unchanged legacy non-PBR",
    "r_pbr 1 = unchanged inherited Rend2 PBR",
    "r_pbr 2 = PBR2 GGX core + exact transfer + ORM",
    "r_pbr 3 = PBR2 + conservative V3 environment BRDF / roughness LOD",
    "",
    "Modern maps:",
    "  BaseColor = original diffuse/base",
    "  _n   = Normal",
    "  _nh  = Normal+Height",
    "  _orm = R AO, G Roughness, B Metallic",
    "Legacy _s remains a fallback.",
    "",
    "Production default remains r_pbr 0.",
    "Cubemap capture/export is unchanged in V3.",
    "True GGX cubemap prefilter is deferred to V3.1 after visual acceptance.",
]
entries[root+"README_DARKWOLF_PBR_V2_V3_TEST.txt"]=(NL.join(readme_lines)+NL).encode("utf-8")

handoff=Path("docs/DARKWOLF_PBR_V2_ARCHITECTURE_HANDOFF_2026-11-07.md")
entries[root+"docs/"+handoff.name]=handoff.read_bytes()
for src in (build/"evidence").glob("PBR_V*_*.json"):
    entries[root+"docs/"+src.name]=src.read_bytes()

for k in list(entries):
    if k.endswith("/SHA256SUMS.txt"):
        del entries[k]

entries[root+"SHA256SUMS_PBR_V2_V3.txt"]="".join(
    H(v)+"  "+k[len(root):]+NL for k,v in sorted(entries.items())
).encode("ascii")

newroot="DarkWolf_PBR_V2_V3_From_42217883095_Win64_TEST"
target=outdir/(newroot+".zip")
with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as out:
    for k,v in sorted(entries.items()):
        rel=k.split("/",1)[1] if "/" in k else k
        out.writestr(newroot+"/"+rel,v)
with zipfile.ZipFile(target) as check:
    assert check.testzip() is None

proof={
    "base_run":42217883095,
    "validated_build_run":42402994791,
    "old_renderer_sha256":H(old),
    "new_renderer_sha256":H(new),
    "package_sha256":H(target.read_bytes()),
    "r_pbr_default":0,
    "orm":"R=AO G=Roughness B=Metallic",
    "cubemap_capture_changed":False,
}
(outdir/"PBR_V2_V3_RELEASE_PROOF.json").write_text(json.dumps(proof,indent=2)+NL)
Path(str(target)+".sha256").write_text(H(target.read_bytes())+"  "+target.name+NL)
print(json.dumps(proof,indent=2))
