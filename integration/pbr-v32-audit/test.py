#!/usr/bin/env python3
from pathlib import Path
import argparse, json

ap=argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("--out")
args=ap.parse_args()

root=Path(args.source)/"SP/code/rend2"
init=(root/"tr_init.c").read_text()
local=(root/"tr_local.h").read_text()
shader=(root/"tr_shader.c").read_text()
frag=(root/"glsl/lightall_fp.glsl").read_text()

checks={
    "command_registered": 'Cmd_AddCommand( "r_pbrMaterialAudit", R_PbrMaterialAudit_f )' in init,
    "command_unregistered": 'Cmd_RemoveCommand( "r_pbrMaterialAudit" )' in init,
    "prototype_present": "R_PbrMaterialAudit_f" in local,
    "reads_loaded_shader": "R_FindShaderByName(name)" in shader,
    "reports_lightall_stage": "stage->glslShaderGroup == tr.lightallShader" in shader,
    "reports_diffuse": "TB_DIFFUSEMAP" in shader and "diffuse=%s" in shader,
    "reports_normalheight": "IMGTYPE_NORMALHEIGHT" in shader and "heightAlpha=%d" in shader,
    "reports_orm": "TB_SPECULARMAP" in shader and "packedORM=%d" in shader,
    "packed_orm_marker": "stage->specularScale[2] < 0.0f" in shader,
    "reports_lightmap": "TB_LIGHTMAP" in shader and "lightmap=%s" in shader,
    "reports_parallax_flag": "LIGHTDEF_USE_PARALLAXMAP" in shader and "parallax=%d" in shader,
    "reports_parallax_depth": "stage->normalScale[3]" in shader and "parallaxDepth=%.6f" in shader,
    "pom_v32_active_condition": all(x in shader for x in (
        "r_pbr->integer >= 3",
        "r_parallaxMapping->integer > 1",
        'pomActive ? "ACTIVE" : "INACTIVE"'
    )),
    "pom_config_report": all(x in shader for x in (
        "r_pomMinLayers->integer",
        "r_pomMaxLayers->integer",
        "r_pomRefineSteps->integer",
        "r_pomDepthScale->value"
    )),
    "v32_pom_unchanged": "DW_ParallaxOcclusionMap" in frag and "USE_PBR_PHYSICAL_RELIEF_V32" in frag,
}

failed=[k for k,v in checks.items() if not v]
if failed:
    raise SystemExit("PBR_V32_BINDING_AUDIT_TEST_FAIL: "+", ".join(failed))

print("DARKWOLF_PBR_V32_MATERIAL_BINDING_AUDIT_STATIC_PASS",len(checks))
if args.out:
    p=Path(args.out); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps({"checks":checks},indent=2)+"\n")
