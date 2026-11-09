#!/usr/bin/env python3
from pathlib import Path
import json,sys

root=Path(sys.argv[1]); ev=Path(sys.argv[2]); ev.mkdir(parents=True,exist_ok=True)
rend=root/"rend2"
init=(rend/"tr_init.c").read_text()
local=(rend/"tr_local.h").read_text()
world=(rend/"tr_world.c").read_text()
v23=(rend/"tr_texture_ai_b2_v23.inc").read_text()
files=(root/"qcommon/files.c").read_text()
checks={}
def ck(k,v):
    checks[k]=bool(v); assert v,k

ck("v23_include",'#include "tr_texture_ai_b2_v23.inc"' in world)
ck("save_v23_registered",'Cmd_AddCommand( "dw_tex_save", R_DWTextureSaveV23_f )' in init)
ck("old_save_not_registered",'Cmd_AddCommand( "dw_tex_save", R_DWTextureSaveV2_f )' not in init)
ck("v23_prototype","R_DWTextureSaveV23_f" in local)
ck("single_pack_name",'DWTRV23_PACK_NAME "zzzzzz_DW_TextureRestoration.pk3"' in v23)
ck("no_hash_in_pack_filename","Com_sprintf(pk3Name" not in v23)
ck("existing_entries_preserved","DWTRV23_CopyArchiveEntries" in v23)
ck("same_qpath_replaced","replaceTexture" in v23 and "Q_stricmp(name, replaceTexture)" in v23)
ck("manifest_replaced","replaceManifest" in v23 and "Q_stricmp(name, replaceManifest)" in v23)
ck("new_entry_added","DWTRV23_WriteMemoryEntry(out, texturePath" in v23)
ck("legacy_merge","DWTRV23_CopyLegacyPaks" in v23)
ck("legacy_delete_after_success",v23.index("DWTRV23_DeleteLegacyPaks") < v23.index("void R_DWTextureSaveV23_f"))
ck("pending_used","pendingPhysical" in v23 and '"%s.pending"' in v23)
ck("pending_source_reused","pendingExists" in v23 and "sourcePhysical, pendingPhysical" in v23)
ck("mounted_final_not_replaced_directly","else if (finalExists)" in v23 and "targetPhysical, pendingPhysical" in v23)
ck("first_save_direct_final","sourcePhysical[0] = '\\0'" in v23 and "targetPhysical, finalPhysical" in v23)
ck("qcommon_pending_hook","FS_DWTRV23_PromotePendingPack" in files)
ck("hook_before_pk3_listing",files.index("FS_DWTRV23_PromotePendingPack( path, dir );") < files.index('Sys_ListFiles( pakfile, ".pk3"'))
ck("startup_backup_restore","DWTR_V23_BACKUP_FILE" in files and "rename( backupPath, finalPath )" in files)
ck("legacy_cleanup_qcommon","FS_DWTRV23_DeleteLegacyPaks" in files)
ck("safe_prefix","zzzzzz_DW_TextureRestoration.pk3" in files)
ck("brush_picker_preserved","R_DWTexturePickV22_f" in init)
ck("next_prev_preserved",'Cmd_AddCommand( "dw_tex_next"' in init and 'Cmd_AddCommand( "dw_tex_prev"' in init)

(ev/"DW_TEXTURE_AI_B2_V23_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n")
print("DW_TEXTURE_AI_B2_V23_STATIC_TESTS_PASS",len(checks))
