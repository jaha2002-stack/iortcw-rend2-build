#!/usr/bin/env python3
from pathlib import Path
import json,sys
root=Path(sys.argv[1]); ev=Path(sys.argv[2]); ev.mkdir(parents=True,exist_ok=True)
init=(root/"tr_init.c").read_text()
local=(root/"tr_local.h").read_text()
world=(root/"tr_world.c").read_text()
ai=(root/"tr_texture_ai_b2.inc").read_text()
base=(root/"tr_texture_restore.inc").read_text()
checks={}
def ck(k,v):
    checks[k]=bool(v); assert v,k
ck("b2_include",'#include "tr_texture_ai_b2.inc"' in world)
ck("ai_build_registered",'Cmd_AddCommand( "dw_tex_ai_build"' in init)
ck("ai_info_registered",'Cmd_AddCommand( "dw_tex_ai_info"' in init)
ck("b1_builder_not_registered",'Cmd_AddCommand( "dw_tex_restore"' not in init)
ck("prototypes","R_DWTextureAIBuild_f" in local and "R_DWTextureAIBackendInfo_f" in local)
ck("real_esrgan_model",'DWTR_AI_MODEL "realesrgan-x4plus"' in ai)
ck("create_process","CreateProcessA" in ai and "WaitForSingleObject" in ai)
ck("vulkan_failure_surface","Check Vulkan support" in ai)
ck("x4_command",'-s 4' in ai)
ck("opaque_guard","alpha/cutout texture refused" in ai)
ck("max_texture_guard","exceeds GPU max texture size" in ai)
ck("output_dimension_guard","expected %dx%d, got %dx%d" in ai)
ck("runtime_no_network",all(x not in ai.lower() for x in ("http://","https://","winhttp","winsock","curl_easy","socket(")))
ck("ab_label","B2 LOCAL AI 4X" in base)
ck("save_manifest","local_ai_realesrgan_x4plus" in base)
ck("pick_instruction","/dw_tex_ai_build" in base)
(ev/"DW_TEXTURE_AI_B2_V1_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n")
print("DW_TEXTURE_AI_B2_V1_STATIC_TESTS_PASS",len(checks))
