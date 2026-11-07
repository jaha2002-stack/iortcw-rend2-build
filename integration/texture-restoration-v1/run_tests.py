#!/usr/bin/env python3
from pathlib import Path
import sys, json
root=Path(sys.argv[1])
ev=Path(sys.argv[2]); ev.mkdir(parents=True,exist_ok=True)
checks={}
def check(name,cond):
    checks[name]=bool(cond)
    assert cond,name
img=(root/"tr_image.c").read_text()
world=(root/"tr_world.c").read_text()
init=(root/"tr_init.c").read_text()
local=(root/"tr_local.h").read_text()
inc=(root/"tr_texture_restore.inc").read_text()
iinc=(root/"tr_texture_restore_image.inc").read_text()
check("image_include",'#include "tr_texture_restore_image.inc"' in img)
check("world_include",'#include "tr_texture_restore.inc"' in world)
for cmd in ("dw_tex_pick","dw_tex_restore","dw_tex_ab","dw_tex_save","dw_tex_discard","dw_tex_info","dw_tex_artistic"):
    check("cmd_"+cmd, ('Cmd_AddCommand( "'+cmd+'"') in init and ('Cmd_RemoveCommand( "'+cmd+'"') in init)
check("4x_fcbi","FCBIByBlock(work, width * 2" in iinc and "FCBIByBlock(work, finalWidth" in iinc)
check("authenticity_bound","delta > 10" in iinc and "delta < -10" in iinc)
check("no_network_api",all(x not in (inc+iinc).lower() for x in ("http://","https://","curl_easy","socket(","winsock","sendto(","recvfrom(")))\ncheck("explicit_offline_message","No internet or telemetry used." in inc)
check("ab_pointer_switch","image[0]=s_dwtr.preview" in inc and "image[0]=s_dwtr.original" in inc)
check("pk3_signatures","0x04034b50" in inc and "0x02014b50" in inc and "0x06054b50" in inc)
check("same_path_override","s_dwtr.original->imgName" in inc and "DWTR_MakePK3(internal" in inc)
check("jpg_tga_persist","DWTR_EncodeTGA" in inc and "DWTR_EncodeJPG" in inc)
check("artistic_disabled","optional backend intentionally not enabled" in inc)
check("prototypes","R_DWTextureRestoreBuild" in local and "R_DWTexturePick_f" in local)
(ev/"DWTR_V1_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n")
print("DWTR_V1_STATIC_TESTS_PASS",len(checks))
