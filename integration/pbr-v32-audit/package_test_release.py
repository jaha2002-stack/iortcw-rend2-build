#!/usr/bin/env python3
from pathlib import Path
import io, zipfile, hashlib, json, struct, sys

if len(sys.argv) != 4:
    raise SystemExit("usage: package_test_release.py <v32_outer_artifact.zip> <renderer_dll> <out_dir>")

outer_path=Path(sys.argv[1])
renderer_path=Path(sys.argv[2])
outdir=Path(sys.argv[3])
outdir.mkdir(parents=True,exist_ok=True)

H=lambda b: hashlib.sha256(b).hexdigest()
NL="\n"

with zipfile.ZipFile(outer_path) as outer:
    candidates=[n for n in outer.namelist()
                if n.endswith("DarkWolf_PBR32_Physical_Relief_POM_From_V31_Win64_TEST.zip")]
    assert len(candidates)==1,candidates
    inner_bytes=outer.read(candidates[0])

with zipfile.ZipFile(io.BytesIO(inner_bytes)) as z:
    assert z.testzip() is None
    entries={n:z.read(n) for n in z.namelist() if not n.endswith("/")}

roots={n.split("/",1)[0] for n in entries if "/" in n}
assert len(roots)==1,roots
oldroot=next(iter(roots))
root=oldroot+"/"

renderer_key=root+"renderer_sp_rend2_x64.dll"
old_renderer=entries[renderer_key]
EXPECTED_V32_RENDERER="01e0b325e7c4b98270c80e432d32f3b65b973abfbbf1ed5cf3c61429a9c0aa1e"
assert H(old_renderer)==EXPECTED_V32_RENDERER,(H(old_renderer),EXPECTED_V32_RENDERER)

new_renderer=renderer_path.read_bytes()
assert new_renderer[:2]==b"MZ"
pe=struct.unpack_from("<I",new_renderer,60)[0]
assert new_renderer[pe:pe+4]==b"PE\x00\x00"
entries[renderer_key]=new_renderer

readme=[
    "DarkWolf PBR V3.2 Physical Relief / POM + Material Binding Audit",
    "Direct base: GitHub Run #42614562240",
    "",
    "POM/GGX rendering code is unchanged from the accepted V3.2 build.",
    "This revision adds one diagnostic console command:",
    "",
    "  r_pbrMaterialAudit <shaderName>",
    "",
    "Example:",
    "  /r_pbrMaterialAudit textures/snow/s_cathedrale_c06",
    "",
    "The command reports the material after Rend2 stage collapse:",
    "  - Diffuse image",
    "  - Normal/NormalHeight image and whether Height alpha is present",
    "  - ORM/specular image and packed-ORM marker",
    "  - Lightmap image",
    "  - LIGHTDEF_USE_PARALLAXMAP state",
    "  - per-material parallaxDepth from normalScale.a",
    "  - V3.2 POM ACTIVE/INACTIVE",
    "  - current POM quality/safety cvars",
    "",
    "Use this command after the map has loaded and after the required",
    "r_pbr/r_parallaxMapping settings were applied before vid_restart.",
]
entries[root+"README_DARKWOLF_PBR32_MATERIAL_BINDING_AUDIT.txt"]=(NL.join(readme)+NL).encode("utf-8")

for k in list(entries):
    if k.endswith("/SHA256SUMS_PBR32_MATERIAL_AUDIT.txt"):
        del entries[k]

entries[root+"SHA256SUMS_PBR32_MATERIAL_AUDIT.txt"]="".join(
    H(v)+"  "+k[len(root):]+NL for k,v in sorted(entries.items())
).encode("ascii")

newroot="DarkWolf_PBR32_Physical_Relief_POM_Material_Audit_From_42614562240_Win64_TEST"
target=outdir/(newroot+".zip")
with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as out:
    for k,v in sorted(entries.items()):
        rel=k[len(root):]
        out.writestr(newroot+"/"+rel,v)

with zipfile.ZipFile(target) as check:
    assert check.testzip() is None

proof={
    "base_run":42614562240,
    "base_renderer_sha256":H(old_renderer),
    "new_renderer_sha256":H(new_renderer),
    "package_sha256":H(target.read_bytes()),
    "feature":"PBR V3.2 Material Binding Audit",
    "command":"r_pbrMaterialAudit <shaderName>",
    "pom_changed":False,
    "ggx_ibl_changed":False
}
(outdir/"PBR_V32_MATERIAL_AUDIT_RELEASE_PROOF.json").write_text(json.dumps(proof,indent=2)+NL)
Path(str(target)+".sha256").write_text(H(target.read_bytes())+"  "+target.name+NL)
print(json.dumps(proof,indent=2))
