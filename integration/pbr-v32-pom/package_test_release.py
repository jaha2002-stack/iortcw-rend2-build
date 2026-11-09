#!/usr/bin/env python3
from pathlib import Path
import io,zipfile,hashlib,json,struct,sys

if len(sys.argv)!=4:
    raise SystemExit("usage: package_test_release.py <v31_outer_artifact.zip> <renderer_dll> <out_dir>")

outer_path=Path(sys.argv[1]); renderer_path=Path(sys.argv[2]); outdir=Path(sys.argv[3])
outdir.mkdir(parents=True,exist_ok=True)
H=lambda b:hashlib.sha256(b).hexdigest()
NL="\n"

with zipfile.ZipFile(outer_path) as outer:
    inner=[n for n in outer.namelist() if n.endswith("DarkWolf_PBR31_True_GGX_IBL_From_42594561766_Win64_TEST.zip")]
    assert len(inner)==1,inner
    data=outer.read(inner[0])

with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert z.testzip() is None
    entries={n:z.read(n) for n in z.namelist() if not n.endswith("/")}

roots={n.split("/",1)[0] for n in entries if "/" in n}
assert len(roots)==1,roots
oldroot=next(iter(roots)); root=oldroot+"/"
renderer_key=root+"renderer_sp_rend2_x64.dll"
old=entries[renderer_key]
EXPECTED="6b152ad44b04f91cb7f2975453ef2f2ce7cf760321cbf9fc056103554557811d"
assert H(old)==EXPECTED,(H(old),EXPECTED)

new=renderer_path.read_bytes()
assert new[:2]==b"MZ"
pe=struct.unpack_from("<I",new,60)[0]
assert new[pe:pe+4]==b"PE\x00\x00"
entries[renderer_key]=new

cfg=[
'seta r_pbr "3"',
'seta r_normalMapping "1"',
'seta r_specularMapping "1"',
'seta r_cubeMapping "1"',
'seta r_parallaxMapping "2"',
'seta r_parallaxMapShadows "1"',
'seta r_pomMinLayers "20"',
'seta r_pomMaxLayers "56"',
'seta r_pomRefineSteps "5"',
'seta r_pomMaxOffset "0.080"',
'seta r_pomDepthScale "1.0"',
'seta r_pomShadowStrength "0.65"',
'vid_restart',
]
entries[root+"Main/DW_PBR32_PHYSICAL_RELIEF_POM.cfg"]=(NL.join(cfg)+NL).encode("ascii")

readme=[
"DarkWolf PBR V3.2 Physical Relief / POM - Win64 TEST",
"Direct base: PBR V3.1 True GGX IBL final TEST",
"",
"V3.2 adds:",
"  - adaptive Parallax Occlusion Mapping for r_pbr 3 + r_parallaxMapping 2",
"  - 20..56 view-angle layers (configurable)",
"  - 5 binary refinement steps plus final secant interpolation",
"  - safe UV displacement clamp",
"  - individual per-material parallaxDepth from normalParallaxMap MTR stage",
"  - optional heightfield self-shadow via r_parallaxMapShadows 1",
"",
"Preserved:",
"  - all V3.1 true GGX prefiltered cubemap + 256x256 BRDF LUT work",
"  - BSP Relight V4/V4.1/V4.2",
"  - r_parallaxMapping 1 legacy path",
"  - r_pbr 0/1/2 behavior",
"",
"Recommended material:",
"  PBR Studio V2.05 -> PhysicalReliefPOM -> Parallax ON -> paired .shader/.mtr export.",
"",
"Run:",
"  /exec DW_PBR32_PHYSICAL_RELIEF_POM.cfg",
]
entries[root+"README_DARKWOLF_PBR32_PHYSICAL_RELIEF_POM_TEST.txt"]=(NL.join(readme)+NL).encode("utf-8")

for k in list(entries):
    if k.endswith("/SHA256SUMS_PBR32_PHYSICAL_RELIEF.txt"):
        del entries[k]
entries[root+"SHA256SUMS_PBR32_PHYSICAL_RELIEF.txt"]="".join(
    H(v)+"  "+k[len(root):]+NL for k,v in sorted(entries.items())
).encode("ascii")

newroot="DarkWolf_PBR32_Physical_Relief_POM_From_V31_Win64_TEST"
target=outdir/(newroot+".zip")
with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as out:
    for k,v in sorted(entries.items()):
        out.writestr(newroot+"/"+k[len(root):],v)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None

proof={
 "base":"DarkWolf PBR V3.1 True GGX IBL",
 "old_renderer_sha256":H(old),
 "new_renderer_sha256":H(new),
 "package_sha256":H(target.read_bytes()),
 "feature":"PBR V3.2 Physical Relief / adaptive POM",
 "defaults":{"minLayers":20,"maxLayers":56,"refine":5,"maxOffset":0.08,"depthScale":1.0,"shadowStrength":0.65},
 "activation":"r_pbr 3 + r_parallaxMapping 2 + parallax-capable material"
}
(outdir/"PBR_V32_RELEASE_PROOF.json").write_text(json.dumps(proof,indent=2)+NL)
Path(str(target)+".sha256").write_text(H(target.read_bytes())+"  "+target.name+NL)
print(json.dumps(proof,indent=2))
