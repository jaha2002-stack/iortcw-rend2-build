#!/usr/bin/env python3
from pathlib import Path
import json,sys

root=Path(sys.argv[1]); ev=Path(sys.argv[2]); ev.mkdir(parents=True,exist_ok=True)
init=(root/"tr_init.c").read_text()
local=(root/"tr_local.h").read_text()
world=(root/"tr_world.c").read_text()
v24=(root/"tr_texture_ai_b2_v24.inc").read_text()
v23=(root/"tr_texture_ai_b2_v23.inc").read_text()
checks={}
def ck(k,v):
    checks[k]=bool(v); assert v,k

ck("v24_include",'#include "tr_texture_ai_b2_v24.inc"' in world)
ck("pick_v24_registered",'Cmd_AddCommand( "dw_tex_pick", R_DWTexturePickV24_f )' in init)
ck("old_v22_pick_not_registered",'Cmd_AddCommand( "dw_tex_pick", R_DWTexturePickV22_f )' not in init)
ck("info_v24_registered",'Cmd_AddCommand( "dw_tex_info", R_DWTextureInfoV24_f )' in init)
ck("prototypes","R_DWTexturePickV24_f" in local and "R_DWTextureInfoV24_f" in local)

ck("world_preserved","Pass 1: static WORLD BSP" in v24)
ck("brush_preserved","Pass 2: inline BSP entities" in v24)
ck("mesh_added","Pass 3: MD3/MDC vertex models" in v24)
ck("mod_mesh","model->type != MOD_MESH" in v24)
ck("animated_mesh_raycast","DWTRV24_RayMDVSurface" in v24)
ck("custom_shader","ent->e.customShader" in v24)
ck("custom_skin","ent->e.customSkin" in v24 and "R_GetSkinByHandle" in v24)
ck("scaled_brush_old_skip_absent","if (ent->e.nonNormalizedAxes)" not in v24)
ck("inverse_scaled_axes","DotProduct(ent->e.axis[k], ent->e.axis[k])" in v24)

ck("sky_excluded","SKY_EXCLUDED" in v24 and "shader->isSky" in v24)
ck("water_excluded","WATER_EXCLUDED" in v24 and "CONTENTS_WATER" in v24)
ck("other_liquids_excluded","CONTENTS_SLIME" in v24 and "CONTENTS_LAVA" in v24)
ck("portal_excluded","PORTAL_EXCLUDED" in v24)
ck("blocked_nearest_guard","blockedT + 0.01f < best" in v24)

# V2.3 AI/save path must remain the active implementation.
ck("v23_save_still_registered",'Cmd_AddCommand( "dw_tex_save", R_DWTextureSaveV23_f )' in init)
ck("v23_single_pack",'DWTRV23_PACK_NAME "zzzzzz_DW_TextureRestoration.pk3"' in v23)
ck("v24_does_not_define_save","R_DWTextureSaveV24_f" not in v24)
ck("v24_does_not_define_ai_build","R_DWTextureAIBuildV24_f" not in v24)
ck("variants_preserved",all(x in (root/"tr_texture_ai_b2_v2.inc").read_text() for x in ("FAITHFUL","BALANCED","STRONG")))

(ev/"DW_TEXTURE_AI_B2_V24_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n")
print("DW_TEXTURE_AI_B2_V24_STATIC_TESTS_PASS",len(checks))
