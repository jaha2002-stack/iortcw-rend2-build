#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve(); ev.mkdir(parents=True,exist_ok=True)
code=src/"SP/code/rend2"
here=Path(__file__).resolve().parent
MARK="DARKWOLF_TEXTURE_AI_B2_V2"

def edit(rel, fn):
    p=code/rel
    before=p.read_text()
    assert MARK not in before, rel+" already patched"
    after=fn(before)
    assert after != before, rel+" unchanged"
    p.write_text(after)
    return {"file":"SP/code/rend2/"+rel,
            "before":hashlib.sha256(before.encode()).hexdigest(),
            "after":hashlib.sha256(after.encode()).hexdigest()}

shutil.copy2(here/"tr_texture_ai_b2_v2.inc", code/"tr_texture_ai_b2_v2.inc")
changes=[]

def local_patch(s):
    anchor="void R_DWTextureAIBackendInfo_f(void);\n"
    assert s.count(anchor)==1, ("local anchor",s.count(anchor))
    return s.replace(anchor, anchor+"""/* DARKWOLF_TEXTURE_AI_B2_V2 */
void R_DWTextureV2ResetCandidates(void);
void R_DWTextureAIBuildV2_f(void);
void R_DWTextureNext_f(void);
void R_DWTexturePrev_f(void);
void R_DWTextureABV2_f(void);
void R_DWTextureInfoV2_f(void);
void R_DWTextureSaveV2_f(void);
""",1)
changes.append(edit("tr_local.h",local_patch))

def world_patch(s):
    return s + "\n/* DARKWOLF_TEXTURE_AI_B2_V2: save/orientation/multi-variant */\n#include \"tr_texture_ai_b2_v2.inc\"\n"
changes.append(edit("tr_world.c",world_patch))

def init_patch(s):
    replacements={
      '\tri.Cmd_AddCommand( "dw_tex_ai_build", R_DWTextureAIBuild_f );\n':
      '\t/* DARKWOLF_TEXTURE_AI_B2_V2 */\n'
      '\tri.Cmd_AddCommand( "dw_tex_ai_build", R_DWTextureAIBuildV2_f );\n'
      '\tri.Cmd_AddCommand( "dw_tex_next", R_DWTextureNext_f );\n'
      '\tri.Cmd_AddCommand( "dw_tex_prev", R_DWTexturePrev_f );\n',
      '\tri.Cmd_AddCommand( "dw_tex_ab", R_DWTextureAB_f );\n':
      '\tri.Cmd_AddCommand( "dw_tex_ab", R_DWTextureABV2_f );\n',
      '\tri.Cmd_AddCommand( "dw_tex_save", R_DWTextureSave_f );\n':
      '\tri.Cmd_AddCommand( "dw_tex_save", R_DWTextureSaveV2_f );\n',
      '\tri.Cmd_AddCommand( "dw_tex_info", R_DWTextureInfo_f );\n':
      '\tri.Cmd_AddCommand( "dw_tex_info", R_DWTextureInfoV2_f );\n',
      '\tri.Cmd_RemoveCommand( "dw_tex_ai_build" );\n':
      '\tri.Cmd_RemoveCommand( "dw_tex_ai_build" );\n'
      '\tri.Cmd_RemoveCommand( "dw_tex_next" );\n'
      '\tri.Cmd_RemoveCommand( "dw_tex_prev" );\n'
    }
    for a,b in replacements.items():
        assert s.count(a)==1, ("init anchor",a,s.count(a))
        s=s.replace(a,b,1)
    return s
changes.append(edit("tr_init.c",init_patch))

def restore_patch(s):
    anchor="""void R_DWTextureRestoreReset(void)
{
    DWTR_Show(qfalse);
    if (s_dwtr.pixels) ri.Free(s_dwtr.pixels);
    Com_Memset(&s_dwtr,0,sizeof(s_dwtr));
}
"""
    assert s.count(anchor)==1, ("reset anchor",s.count(anchor))
    repl="""void R_DWTextureRestoreReset(void)
{
    DWTR_Show(qfalse);
    /* DARKWOLF_TEXTURE_AI_B2_V2: owns all candidate CPU buffers. */
    R_DWTextureV2ResetCandidates();
    if (s_dwtr.pixels) ri.Free(s_dwtr.pixels);
    Com_Memset(&s_dwtr,0,sizeof(s_dwtr));
}
"""
    return s.replace(anchor,repl,1)
changes.append(edit("tr_texture_restore.inc",restore_patch))

proof={
 "version":"DarkWolf Local AI Texture Restoration B2 V2",
 "base_clean_production_run":42198541106,
 "inherits_b2_v1":True,
 "stage1":{
   "pk3_save":"physical Win32 stored-ZIP + atomic .tmp rename",
   "engine_pk3_write_guard_bypassed_safely":True,
   "orientation":"pre-flip RGB before RE_SaveJPG to cancel renderer JPEG bottom-up traversal",
   "asymmetric_texture_regression_target":"window/wood"
 },
 "stage2":{
   "variants":[
     {"name":"FAITHFUL","luma_ai_percent":35,"chroma_ai_percent":10,"max_luma_delta":36},
     {"name":"BALANCED","luma_ai_percent":55,"chroma_ai_percent":20,"max_luma_delta":56},
     {"name":"STRONG","luma_ai_percent":80,"chroma_ai_percent":35,"max_luma_delta":88}
   ],
   "default":"BALANCED",
   "commands":["dw_tex_next","dw_tex_prev","dw_tex_ab","dw_tex_save","dw_tex_info"]
 },
 "network_at_runtime":False,
 "telemetry":False,
 "changes":changes
}
(ev/"DW_TEXTURE_AI_B2_V2_SOURCE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n")
print(json.dumps(proof,indent=2))
