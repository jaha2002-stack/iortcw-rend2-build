#!/usr/bin/env python3
from pathlib import Path
import json,sys

root=Path(sys.argv[1]); ev=Path(sys.argv[2]); ev.mkdir(parents=True,exist_ok=True)
init=(root/"tr_init.c").read_text()
local=(root/"tr_local.h").read_text()
world=(root/"tr_world.c").read_text()
base=(root/"tr_texture_restore.inc").read_text()
v1=(root/"tr_texture_ai_b2.inc").read_text()
v2=(root/"tr_texture_ai_b2_v2.inc").read_text()
checks={}
def ck(k,v):
    checks[k]=bool(v); assert v,k

ck("v2_include",'#include "tr_texture_ai_b2_v2.inc"' in world)
ck("v2_build_registered",'Cmd_AddCommand( "dw_tex_ai_build", R_DWTextureAIBuildV2_f )' in init)
ck("next_registered",'Cmd_AddCommand( "dw_tex_next", R_DWTextureNext_f )' in init)
ck("prev_registered",'Cmd_AddCommand( "dw_tex_prev", R_DWTexturePrev_f )' in init)
ck("ab_v2_registered",'Cmd_AddCommand( "dw_tex_ab", R_DWTextureABV2_f )' in init)
ck("save_v2_registered",'Cmd_AddCommand( "dw_tex_save", R_DWTextureSaveV2_f )' in init)
ck("info_v2_registered",'Cmd_AddCommand( "dw_tex_info", R_DWTextureInfoV2_f )' in init)
ck("old_builder_not_registered",'Cmd_AddCommand( "dw_tex_ai_build", R_DWTextureAIBuild_f )' not in init)
ck("candidate_count","#define DWTRV2_CANDIDATE_COUNT 3" in v2)
ck("faithful",'"FAITHFUL"' in v2 and "35, 10, 36" in v2)
ck("balanced",'"BALANCED"' in v2 and "55, 20, 56" in v2)
ck("strong",'"STRONG"' in v2 and "80, 35, 88" in v2)
ck("balanced_default","DWTRV2_Activate(1); /* RTCW default = BALANCED */" in v2)
ck("chroma_guard","chromaPercent" in v2 and "ac - bc" in v2)
ck("luma_guard","maxLumaDelta" in v2 and "DWTRV2_ClampI(ay - by" in v2)
ck("orientation_fix","DWTRV2_FlipRGB(flipped, rgb, width, height)" in v2)
ck("orientation_explained","RE_SaveJPG() already traverses source rows bottom->top" in v2)
ck("physical_pk3","CreateFileA(tmpPath" in v2 and "MoveFileExA(tmpPath, finalPath" in v2)
ck("atomic_tmp",'Com_sprintf(tmpPath, sizeof(tmpPath), "%s.tmp", finalPath)' in v2)
ck("pk3_not_engine_fs","FS_FOpenFileWrite" not in v2 and "ri.FS_WriteFile(pk3" not in v2)
ck("zip_signatures","0x04034b50" in v2 and "0x02014b50" in v2 and "0x06054b50" in v2)
ck("manifest_inside_pk3","manifestInternal" in v2 and "DWTRV2_WritePhysicalPK3" in v2)
ck("candidate_reset_hook","R_DWTextureV2ResetCandidates();" in base)
ck("v1_real_ai",'DWTR_AI_MODEL "realesrgan-x4plus"' in v1)
ck("runtime_no_network",all(x not in v2.lower() for x in ("http://","https://","winhttp","winsock","curl_easy","socket(")))
for sym in ("R_DWTextureAIBuildV2_f","R_DWTextureNext_f","R_DWTexturePrev_f","R_DWTextureSaveV2_f"):
    ck("prototype_"+sym,sym in local)

(ev/"DW_TEXTURE_AI_B2_V2_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n")
print("DW_TEXTURE_AI_B2_V2_STATIC_TESTS_PASS",len(checks))
