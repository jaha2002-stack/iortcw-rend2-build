#!/usr/bin/env python3
from pathlib import Path
import argparse, json, re

ap=argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("--stage",type=int,choices=(1,2,3),required=True)
ap.add_argument("--out")
args=ap.parse_args()
root=Path(args.source)/"SP/code/rend2"
stage=args.stage

def txt(rel): return (root/rel).read_text()

glsl=txt("tr_glsl.c")
frag=txt("glsl/lightall_fp.glsl")
shader=txt("tr_shader.c")
image=txt("tr_image.c")
local=txt("tr_local.h")
init=txt("tr_init.c")
backend=txt("tr_backend.c")

checks={
 "pbr_default_off": 'r_pbr = ri.Cvar_Get("r_pbr", "0"' in init,
 "use_pbr_legacy_preserved": 'if (r_pbr->integer)\n\t\tQ_strcat(dest, size, "#define USE_PBR\\n");' in glsl,
 "pbr2_define": 'if (r_pbr->integer >= 2)' in glsl and '#define USE_PBR2' in glsl,
 "pbr3_ibl_define": 'if (r_pbr->integer >= 3)' in glsl and '#define USE_PBR2_IBL_V3' in glsl,
 "srgb_exact": all(x in frag for x in ("DW_SRGBToLinear","DW_LinearToSRGB","2.4","0.04045","0.0031308")),
 "ggx": all(x in frag for x in ("DW_DistributionGGX","DW_VisibilitySmithGGXCorrelated","DW_FresnelSchlick","DW_CalcSpecularGGX")),
 "legacy_square_fallback": 'diffuse.rgb *= diffuse.rgb;' in frag,
 "legacy_sqrt_fallback": 'gl_FragColor.rgb = sqrt(gl_FragColor.rgb);' in frag,
 "material_ao_indirect_only": 'ambientColor * diffuse.rgb * materialAO' in frag,
 "missing_material_map_dielectric": 'u_EnableTextures.z < 0.5' in frag and 'metal = 0.0;' in frag and 'roughness = 0.78;' in frag,
 "ibl_v3": 'DW_EnvironmentBRDFApprox' in frag and 'roughness * roughness' in frag,
 "firevol_marker_preserved": 'FIREVOL_CLEAN_PRODUCTION' in backend,
 "crypt1_marker_preserved": 'DARKWOLF_FIREVOL_CRYPT1_SLOT6_REANCHOR_PRODUCTION' in backend,
}
if stage >= 2:
    checks.update({
      "pbrdata_flag": "IMGFLAG_PBRDATA" in local,
      "orm_parser": 'ormMap' in shader and 'specularScale, 1.0f, 1.0f, -1.0f' in shader,
      "orm_autodiscovery": '"_orm"' in shader and 'r_pbr->integer >= 2' in shader,
      "legacy_spec_fallback": '"_s"' in shader,
      "orm_no_sampler_growth": "TB_SPECULARMAP" in shader and "TB_SPECULARMAP" in local,
      "linear_data_mips": "DW_MipMapsPBRData" in image and image.count("IMGFLAG_PBRDATA") >= 2,
      "orm_shader_decode": "R=AO, G=roughness, B=metallic" in frag,
    })

# Non-regression: PBR patch must not rewrite cubemap generation/export.
checks["ordinary_cubemap_mipmap_still_present"]='qglGenerateTextureMipmapEXT(cubemap->image->texnum, GL_TEXTURE_CUBE_MAP)' in backend
checks["shadow_budget_not_touched"]="r_dlightShadowMaxLights" not in frag and "r_dlightShadowMaxLights" not in shader

failed=[k for k,v in checks.items() if not v]
if failed:
    raise SystemExit("PBR_TEST_FAIL: "+", ".join(failed))
print(f"DARKWOLF_PBR_STAGE_{stage}_STATIC_PASS {len(checks)}")
if args.out:
    p=Path(args.out); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(checks,indent=2)+"\n")
