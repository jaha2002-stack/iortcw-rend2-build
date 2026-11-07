#!/usr/bin/env python3
from pathlib import Path
import hashlib, shutil, sys, json

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve(); ev.mkdir(parents=True,exist_ok=True)
code=src/"SP/code/rend2"
here=Path(__file__).resolve().parent
MARK="DARKWOLF_ORIGINAL_TEXTURE_RESTORATION_V1"

def edit(rel, fn):
    p=code/rel
    before=p.read_text()
    assert MARK not in before, rel+" already patched"
    after=fn(before)
    assert after != before, rel+" unchanged"
    p.write_text(after)
    return {
      "file":"SP/code/rend2/"+rel,
      "before":hashlib.sha256(before.encode()).hexdigest(),
      "after":hashlib.sha256(after.encode()).hexdigest()
    }

shutil.copy2(here/"tr_texture_restore.inc",code/"tr_texture_restore.inc")
shutil.copy2(here/"tr_texture_restore_image.inc",code/"tr_texture_restore_image.inc")

changes=[]

def image_patch(s):
    return s + "\n/* "+MARK+": selected-texture-only offline restoration */\n#include \"tr_texture_restore_image.inc\"\n"
changes.append(edit("tr_image.c",image_patch))

def local_patch(s):
    anchor="image_t\t\t*R_FindImageFile( const char *name, imgType_t type, imgFlags_t flags );\n"
    assert s.count(anchor)==1, ("tr_local image anchor",s.count(anchor))
    add=anchor+"""/* DARKWOLF_ORIGINAL_TEXTURE_RESTORATION_V1 */
qboolean R_DWTextureRestoreBuild(image_t *source, image_t **outImage,
                                 byte **outPixels, int *outWidth, int *outHeight);
void R_DWTextureRestoreReset(void);
void R_DWTexturePick_f(void);
void R_DWTextureRestore_f(void);
void R_DWTextureAB_f(void);
void R_DWTextureSave_f(void);
void R_DWTextureDiscard_f(void);
void R_DWTextureInfo_f(void);
void R_DWTextureArtistic_f(void);
"""
    return s.replace(anchor,add,1)
changes.append(edit("tr_local.h",local_patch))

def world_patch(s):
    return s + "\n/* "+MARK+": runtime picker, A/B and persistence */\n#include \"tr_texture_restore.inc\"\n"
changes.append(edit("tr_world.c",world_patch))

def init_patch(s):
    add_anchor='\tri.Cmd_AddCommand( "imagelist", R_ImageList_f );\n'
    assert s.count(add_anchor)==1, ("add anchor",s.count(add_anchor))
    commands=add_anchor+"""\t/* DARKWOLF_ORIGINAL_TEXTURE_RESTORATION_V1 */
\tri.Cmd_AddCommand( "dw_tex_pick", R_DWTexturePick_f );
\tri.Cmd_AddCommand( "dw_tex_restore", R_DWTextureRestore_f );
\tri.Cmd_AddCommand( "dw_tex_ab", R_DWTextureAB_f );
\tri.Cmd_AddCommand( "dw_tex_save", R_DWTextureSave_f );
\tri.Cmd_AddCommand( "dw_tex_discard", R_DWTextureDiscard_f );
\tri.Cmd_AddCommand( "dw_tex_info", R_DWTextureInfo_f );
\tri.Cmd_AddCommand( "dw_tex_artistic", R_DWTextureArtistic_f );
"""
    s=s.replace(add_anchor,commands,1)
    rm_anchor='\tri.Cmd_RemoveCommand( "imagelist" );\n'
    assert s.count(rm_anchor)==1, ("remove anchor",s.count(rm_anchor))
    removals=rm_anchor+"""\tri.Cmd_RemoveCommand( "dw_tex_pick" );
\tri.Cmd_RemoveCommand( "dw_tex_restore" );
\tri.Cmd_RemoveCommand( "dw_tex_ab" );
\tri.Cmd_RemoveCommand( "dw_tex_save" );
\tri.Cmd_RemoveCommand( "dw_tex_discard" );
\tri.Cmd_RemoveCommand( "dw_tex_info" );
\tri.Cmd_RemoveCommand( "dw_tex_artistic" );
\tR_DWTextureRestoreReset();
"""
    return s.replace(rm_anchor,removals,1)
changes.append(edit("tr_init.c",init_patch))

proof={
 "version":"DarkWolf Original Texture Restoration V1",
 "base_run":42198541106,
 "base_sha":"5ba3e923803674c9acee71600412720a0eeaf81e",
 "scope":"selected BSP diffuse texture only",
 "network":False,
 "telemetry":False,
 "upscale":"4x FCBI in YCoCg + bounded high-frequency recovery",
 "ab":"same runtime, shader stage pointer switch, no vid_restart",
 "persistence":"one deterministic zz_dwtr_<pathhash>.pk3 per accepted texture plus manifest",
 "artistic":"optional backend placeholder only; disabled",
 "commands":["dw_tex_pick","dw_tex_restore","dw_tex_ab","dw_tex_save","dw_tex_discard","dw_tex_info","dw_tex_artistic"],
 "changes":changes
}
(ev/"DWTR_V1_SOURCE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n")
print("DWTR_V1_APPLIED",json.dumps(proof,indent=2))
