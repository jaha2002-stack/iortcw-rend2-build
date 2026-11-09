#!/usr/bin/env python3
from pathlib import Path
import json,sys
root=Path(sys.argv[1]); ev=Path(sys.argv[2]); ev.mkdir(parents=True,exist_ok=True)
init=(root/"tr_init.c").read_text()
local=(root/"tr_local.h").read_text()
world=(root/"tr_world.c").read_text()
v2=(root/"tr_texture_ai_b2_v2.inc").read_text()
v22=(root/"tr_texture_ai_b2_v22.inc").read_text()
checks={}
def ck(k,v):
    checks[k]=bool(v); assert v,k

ck("v22_include",'#include "tr_texture_ai_b2_v22.inc"' in world)
ck("pick_v22_registered",'Cmd_AddCommand( "dw_tex_pick", R_DWTexturePickV22_f )' in init)
ck("old_pick_not_registered",'Cmd_AddCommand( "dw_tex_pick", R_DWTexturePick_f )' not in init)
ck("info_v22_registered",'Cmd_AddCommand( "dw_tex_info", R_DWTextureInfoV22_f )' in init)
ck("stable_6z_prefix",'"zzzzzz_dwtr_%08x.pk3"' in v2)
ck("3z_prefix_removed",'"zzz_dwtr_%08x.pk3"' not in v2)
ck("cleanup_called","R_DWTextureV22CleanupLegacyPaks(home, game, hash, pk3Physical);" in v2)
ck("cleanup_range","zcount = 2; zcount <= 10" in v22)
ck("cleanup_same_hash",'%08x.pk3' in v22 and "hash" in v22)
ck("cleanup_after_success",v2.index("R_DWTextureV22CleanupLegacyPaks") > v2.index("DWTRV2_WritePhysicalPK3"))
ck("world_pick","Pass 1: static WORLD BSP" in v22)
ck("brush_pick","Pass 2: RT_MODEL / MOD_BRUSH entities" in v22)
ck("mod_brush","model->type != MOD_BRUSH" in v22)
ck("bmodel_surfaces","bmodel->firstSurface + s" in v22)
ck("entity_ray_transform","DWTRV22_WorldRayToEntity" in v22)
ck("brush_log","PICK source=BRUSH" in v22)
ck("world_log","PICK source=WORLD" in v22)
ck("nearest_shared_best","float t = best;" in v22)
ck("scaled_guard","ent->e.nonNormalizedAxes" in v22)
ck("prototypes","R_DWTexturePickV22_f" in local and "R_DWTextureV22CleanupLegacyPaks" in local)

(ev/"DW_TEXTURE_AI_B2_V22_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n")
print("DW_TEXTURE_AI_B2_V22_STATIC_TESTS_PASS",len(checks))
