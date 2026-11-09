#!/usr/bin/env python3
from pathlib import Path
import io, zipfile, hashlib, json, struct, sys

if len(sys.argv) != 4:
    raise SystemExit("usage: package_test_release.py <v42_artifact_outer_zip> <renderer_dll> <out_dir>")

base_outer=Path(sys.argv[1])
renderer=Path(sys.argv[2])
outdir=Path(sys.argv[3])
outdir.mkdir(parents=True,exist_ok=True)

H=lambda b: hashlib.sha256(b).hexdigest()
NL=chr(10)

with zipfile.ZipFile(base_outer) as outer:
    inner_candidates=[n for n in outer.namelist()
        if n.endswith("DarkWolf_PBR3_BSP_Relight_V42_From_42217883095_Win64_TEST.zip")]
    assert len(inner_candidates)==1, inner_candidates
    inner_bytes=outer.read(inner_candidates[0])

with zipfile.ZipFile(io.BytesIO(inner_bytes)) as z:
    assert z.testzip() is None
    entries={n:z.read(n) for n in z.namelist() if not n.endswith("/")}

roots={n.split("/",1)[0] for n in entries if "/" in n}
assert len(roots)==1, roots
oldroot=next(iter(roots))
root=oldroot+"/"
renderer_key=root+"renderer_sp_rend2_x64.dll"
old_renderer=entries[renderer_key]

EXPECTED_V42_RENDERER="83ce31c639b2ba980b71568919f6a3432e0369f5f58061f7620ac660b85c63a9"
assert H(old_renderer)==EXPECTED_V42_RENDERER, (H(old_renderer),EXPECTED_V42_RENDERER)

new_renderer=renderer.read_bytes()
assert new_renderer[:2]==b"MZ"
pe=struct.unpack_from("<I",new_renderer,60)[0]
assert new_renderer[pe:pe+4]==b"PE\x00\x00"
entries[renderer_key]=new_renderer

cfg=[
    'seta r_pbr "3"',
    'seta r_normalMapping "1"',
    'seta r_specularMapping "1"',
    'seta r_cubeMapping "1"',
    "vid_restart",
]
entries[root+"Main/DW_PBR31_TRUE_GGX_IBL.cfg"]=(NL.join(cfg)+NL).encode("ascii")

readme=[
    "DarkWolf PBR V3.1 True GGX IBL - Win64 TEST",
    "Direct base package: GitHub Run #42594561766",
    "Base renderer: PBR V3 + BSP Relight V4.2",
    "",
    "V3.1 additions:",
    "  - separate linear RGBA16F prefiltered environment cubemap per probe",
    "  - true GGX half-vector importance-sampled environment convolution",
    "  - 256 deterministic samples per non-zero roughness mip",
    "  - raw environment LOD0 samples converted sRGB->linear before accumulation",
    "  - no gamma-space legacy mip averaging in the GGX integral",
    "  - 256x256 RGBA16F BRDF integration LUT (RG used)",
    "  - 512-sample split-sum DFG integration",
    "  - correlated Smith GGX visibility matching the direct-light GGX model",
    "  - roughness-to-prefiltered-mip selection at runtime",
    "  - automatic analytical V3 fallback if FBO/float textures/8 TMUs are unavailable",
    "",
    "Preserved:",
    "  - r_pbr 0 / 1 / 2 behavior",
    "  - PBR V2 core + packed ORM (R=AO, G=Roughness, B=Metallic)",
    "  - BSP Relight V4 + directional recovery V4.1 + diffuse IBL correction V4.2",
    "  - all Clean Production features inherited by #42594561766",
    "",
    "Recommended test:",
    "  /exec DW_PBR31_TRUE_GGX_IBL.cfg",
    "",
    "The GGX cubemap/LUT are generated at map-load time on supported GPUs.",
]
entries[root+"README_DARKWOLF_PBR31_TRUE_GGX_IBL_TEST.txt"]=(NL.join(readme)+NL).encode("utf-8")

for k in list(entries):
    if k.endswith("/SHA256SUMS_PBR31_TRUE_GGX_IBL.txt"):
        del entries[k]

entries[root+"SHA256SUMS_PBR31_TRUE_GGX_IBL.txt"]="".join(
    H(v)+"  "+k[len(root):]+NL for k,v in sorted(entries.items())
).encode("ascii")

newroot="DarkWolf_PBR31_True_GGX_IBL_From_42594561766_Win64_TEST"
target=outdir/(newroot+".zip")
with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as out:
    for k,v in sorted(entries.items()):
        rel=k[len(root):]
        out.writestr(newroot+"/"+rel,v)

with zipfile.ZipFile(target) as check:
    assert check.testzip() is None

proof={
    "direct_base_run":42594561766,
    "direct_base_sha":"957c425b3c3a8f521c72d5dd2bca9dba9b825938",
    "old_v42_renderer_sha256":H(old_renderer),
    "new_v31_renderer_sha256":H(new_renderer),
    "package_sha256":H(target.read_bytes()),
    "feature":"PBR V3.1 true GGX prefiltered environment + full BRDF integration LUT",
    "prefilter_samples_per_nonzero_mip":256,
    "brdf_lut":"256x256 RGBA16F",
    "brdf_samples":512,
    "visibility_model":"correlated Smith GGX",
    "source_convolution_space":"sRGB samples converted to linear before accumulation",
    "legacy_modes_preserved":[0,1,2],
    "fallback":"analytical PBR V3 when V3.1 capabilities are unavailable"
}
(outdir/"PBR_V31_RELEASE_PROOF.json").write_text(json.dumps(proof,indent=2)+NL)
Path(str(target)+".sha256").write_text(H(target.read_bytes())+"  "+target.name+NL)
print(json.dumps(proof,indent=2))
