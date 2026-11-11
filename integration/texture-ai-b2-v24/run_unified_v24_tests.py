#!/usr/bin/env python3
from pathlib import Path
import json,re,sys

if len(sys.argv) != 3:
    raise SystemExit("usage: run_tests.py <source-root> <evidence-dir>")

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve()
ev.mkdir(parents=True,exist_ok=True)
rend=src/"SP/code/rend2"
qcommon=src/"SP/code/qcommon"

def read(rel):
    p=rend/rel
    assert p.exists(), p
    return p.read_text(errors="ignore")

local=read("tr_local.h")
scene=read("tr_scene.c")
main=read("tr_main.c")
backend=read("tr_backend.c")
init=read("tr_init.c")
world=read("tr_world.c")
shader=read("tr_shader.c")
glsl=read("tr_glsl.c")
frag=read("glsl/lightall_fp.glsl")
epo=read("tr_electric_physical_owner.inc")
epoa=read("tr_electric_owner_audit.inc")
edra=read("tr_escape1_dlight_residency_audit.inc")
edr12=read("tr_escape1_physical_dlight_owner_v12.inc")
v23=read("tr_texture_ai_b2_v23.inc")
v24=read("tr_texture_ai_b2_v24.inc")
files=(qcommon/"files.c").read_text(errors="ignore")

checks={}

# Electric Physical Owner V1 + Escape1 Owner Residency V1.2
checks["epo_v1_marker"]="DARKWOLF_ELECTRIC_PHYSICAL_OWNER_V1" in epo
checks["epo_owner_field"]="int physicalElectricOwnerId;" in local
checks["epo_default_on"]='r_dwElectricPhysicalOwner", "1"' in epo
checks["epo_diag_default_off"]='r_dwElectricPhysicalOwnerDiag", "0"' in epo
checks["epoa_default_off"]='r_dwElectricOwnerAudit", "0"' in epoa
checks["edra_default_off"]='r_dwEscape1DlightResidencyAudit", "0"' in edra
checks["edr12_marker"]="DARKWOLF_ESCAPE1_PHYSICAL_DLIGHT_OWNER_RESIDENCY_V12" in edr12
checks["edr12_default_on"]='r_dwEscape1PhysicalDlightOwnerResidency", "1"' in edr12
checks["edr12_diag_default_off"]='r_dwEscape1PhysicalDlightOwnerDiag", "0"' in edr12
checks["edr12_reserve_9"]="EDR12_DEFAULT_EXTERNAL_NATIVE_RESERVE 9" in edr12
checks["v11_withdrawn"]="DARKWOLF_ESCAPE1_DLIGHT_RESIDENCY_FIX_V1_1" not in (scene+edr12+local)
checks["direct_energy_not_written"]=not re.search(r'->(?:radius|color|candidate\.intensity)\s*=(?!=)',edr12)
checks["epo_direct_energy_not_written"]=all(x not in epo for x in (
    '->radius =','->color[0] =','->color[1] =','->color[2] =',
    'RE_AddLightToScene(','R_StaticPromoteSyntheticAdd('))
checks["feature_incs_do_not_define_max_dlights"]="#define MAX_DLIGHTS" not in (epo+epoa+edra+edr12)

# The engine hard limit must remain 32.
all_code="\n".join(p.read_text(errors="ignore") for p in (src/"SP/code").rglob("*") if p.is_file() and p.suffix.lower() in (".c",".h",".inc"))
checks["max_dlights_is_32"]=bool(re.search(r'#\s*define\s+MAX_DLIGHTS\s+32\b',all_code))

# Texture AI B2 V2.3
checks["texture_v23_marker"]="DARKWOLF_TEXTURE_AI_B2_V23" in v23
checks["texture_save_registered"]='Cmd_AddCommand( "dw_tex_save", R_DWTextureSaveV23_f )' in init
checks["texture_next_prev"]='Cmd_AddCommand( "dw_tex_next"' in init and 'Cmd_AddCommand( "dw_tex_prev"' in init
checks["texture_universal_picker_v24"]="R_DWTexturePickV24_f" in init
checks["texture_v24_marker"]="DARKWOLF_TEXTURE_AI_B2_V24" in v24
checks["texture_v24_brush"]="MOD_BRUSH" in v24
checks["texture_v24_mesh"]="MOD_MESH" in v24
checks["texture_v24_sky_excluded"]="SKY_EXCLUDED" in v24
checks["texture_v24_water_excluded"]="WATER_EXCLUDED" in v24
checks["texture_cumulative_pack"]='DWTRV23_PACK_NAME "zzzzzz_DW_TextureRestoration.pk3"' in v23
checks["texture_pending_promotion"]="FS_DWTRV23_PromotePendingPack" in files
checks["texture_pending_before_scan"]=files.index("FS_DWTRV23_PromotePendingPack( path, dir );") < files.index('Sys_ListFiles( pakfile, ".pk3"')

# PBR V3.2 + Material Binding Audit
checks["pbr_v31_true_ggx"]="USE_PBR2_IBL_V31" in frag and "u_BRDFLut" in frag
checks["pbr_v32_pom"]="DW_ParallaxOcclusionMap" in frag and "USE_PBR_PHYSICAL_RELIEF_V32" in frag
checks["pbr_v32_only_for_pbr3"]="r_pbr->integer >= 3" in glsl
checks["pbr_material_audit_command"]='Cmd_AddCommand( "r_pbrMaterialAudit", R_PbrMaterialAudit_f )' in init
checks["pbr_audit_normalheight"]="IMGTYPE_NORMALHEIGHT" in shader and "heightAlpha=%d" in shader
checks["pbr_audit_packed_orm"]="packedORM=%d" in shader
checks["pbr_audit_pom_active"]='pomActive ? "ACTIVE" : "INACTIVE"' in shader
checks["pbr_pom_defaults_present"]=all(x in init for x in (
    "r_pomMinLayers","r_pomMaxLayers","r_pomRefineSteps","r_pomMaxOffset",
    "r_pomDepthScale","r_pomGrazingFadeStart","r_pomGrazingFadeEnd","r_pomShadowStrength"))

# Coexistence on overlap files.
checks["tr_local_has_all_three"]=all(x in local for x in (
    "physicalElectricOwnerId","R_DWTextureSaveV23_f","R_DWTexturePickV24_f","r_pomMinLayers","R_PbrMaterialAudit_f"))
checks["tr_init_has_texture_and_pbr"]=all(x in init for x in (
    "R_DWTextureSaveV23_f","R_DWTexturePickV24_f","r_pbrMaterialAudit","r_pomMinLayers"))
checks["tr_backend_has_owner_and_ggx"]="physicalElectricOwnerId" in backend and ("PBR V3.1" in backend or "R_PBR31" in backend or "pbr31" in backend.lower())

failed={k:v for k,v in checks.items() if not v}
(ev/"UNIFIED_SOURCE_INVARIANTS.json").write_text(json.dumps({"checks":checks,"failed":list(failed)},indent=2)+"\n")
if failed:
    raise SystemExit("UNIFIED_SOURCE_INVARIANTS_FAIL: "+", ".join(failed))
print("UNIFIED_SOURCE_INVARIANTS_PASS",len(checks))
