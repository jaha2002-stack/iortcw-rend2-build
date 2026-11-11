#!/usr/bin/env python3
from pathlib import Path
import json,sys

root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve(); ev.mkdir(parents=True,exist_ok=True)
v24=(root/"tr_texture_ai_b2_v24.inc").read_text()
init=(root/"tr_init.c").read_text()
v23=(root/"tr_texture_ai_b2_v23.inc").read_text()
checks={}
def ck(k,v):
    checks[k]=bool(v); assert v,k

ck("v241_marker","DARKWOLF_TEXTURE_AI_B2_V241" in v24)
ck("brush_total_surface_bound","surfIndex >= tr.world->numsurfaces" in v24)
ck("wrong_world_only_bound_removed","surfIndex >= tr.world->numWorldSurfaces" not in v24)
ck("third_person_excluded","RF_THIRD_PERSON | RF_FIRST_PERSON | RF_DEPTHHACK" in v24)
ck("players_prefix_excluded",'"models/players/"' in v24)
ck("weapons2_prefix_excluded",'"models/weapons2/"' in v24)
ck("weapons_prefix_excluded",'"models/weapons/"' in v24)
ck("mesh_support_preserved","model->type != MOD_MESH" in v24)
ck("scaled_brush_support_preserved","DotProduct(ent->e.axis[k], ent->e.axis[k])" in v24)
ck("sky_excluded","SKY_EXCLUDED" in v24)
ck("water_excluded","WATER_EXCLUDED" in v24)
ck("v23_save_preserved",'Cmd_AddCommand( "dw_tex_save", R_DWTextureSaveV23_f )' in init)
ck("v23_cumulative_pack_preserved",'DWTRV23_PACK_NAME "zzzzzz_DW_TextureRestoration.pk3"' in v23)
ck("v241_console_marker","DWTR AI B2 V2.4.1:" in v24)

(ev/"DW_TEXTURE_AI_B2_V241_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n")
print("DW_TEXTURE_AI_B2_V241_STATIC_TESTS_PASS",len(checks))
