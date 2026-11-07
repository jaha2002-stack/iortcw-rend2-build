#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve(); ev.mkdir(parents=True,exist_ok=True)
code=src/"SP/code/rend2"
here=Path(__file__).resolve().parent
MARK="DARKWOLF_TEXTURE_AI_B2_V1"

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

shutil.copy2(here/"tr_texture_ai_b2.inc", code/"tr_texture_ai_b2.inc")
changes=[]

def local_patch(s):
    anchor="void R_DWTextureArtistic_f(void);\n"
    assert s.count(anchor)==1, ("local anchor",s.count(anchor))
    return s.replace(anchor,anchor+"""/* DARKWOLF_TEXTURE_AI_B2_V1 */
void R_DWTextureAIBuild_f(void);
void R_DWTextureAIBackendInfo_f(void);
""",1)
changes.append(edit("tr_local.h",local_patch))

def world_patch(s):
    return s + "\n/* DARKWOLF_TEXTURE_AI_B2_V1: local neural runtime */\n#include \"tr_texture_ai_b2.inc\"\n"
changes.append(edit("tr_world.c",world_patch))

def init_patch(s):
    old='\tri.Cmd_AddCommand( "dw_tex_restore", R_DWTextureRestore_f );\n'
    assert s.count(old)==1, ("add restore anchor",s.count(old))
    s=s.replace(old,
        '\t/* DARKWOLF_TEXTURE_AI_B2_V1 */\n'
        '\tri.Cmd_AddCommand( "dw_tex_ai_build", R_DWTextureAIBuild_f );\n'
        '\tri.Cmd_AddCommand( "dw_tex_ai_info", R_DWTextureAIBackendInfo_f );\n',1)
    oldrm='\tri.Cmd_RemoveCommand( "dw_tex_restore" );\n'
    assert s.count(oldrm)==1, ("remove restore anchor",s.count(oldrm))
    s=s.replace(oldrm,
        '\tri.Cmd_RemoveCommand( "dw_tex_ai_build" );\n'
        '\tri.Cmd_RemoveCommand( "dw_tex_ai_info" );\n',1)
    return s
changes.append(edit("tr_init.c",init_patch))

def restore_text_patch(s):
    replacements={
      "DWTR: use /dw_tex_restore, then /dw_tex_ab; /dw_tex_save persists B in an automatic PK3.\\n":
      "DWTR AI B2: use /dw_tex_ai_build, then /dw_tex_ab; /dw_tex_save persists B2 in an automatic PK3.\\n",
      's_dwtr.showingB?"B RESTORED 4X":"A ORIGINAL"':
      's_dwtr.showingB?"B2 LOCAL AI 4X":"A ORIGINAL"',
      "mode offline_hybrid_fidelity\\npk3 %s\\nrestart persistent yes\\n":
      "mode local_ai_realesrgan_x4plus\\npk3 %s\\nrestart persistent yes\\n",
      "DWTR: SAVED %s containing %s. It will override the original after game restart.\\n":
      "DWTR AI B2: SAVED %s containing %s. It will override the original after game restart.\\n",
      "DWTR: manifest %s. No internet or telemetry used.\\n":
      "DWTR AI B2: manifest %s. Local AI only; no internet or telemetry used.\\n"
    }
    for a,b in replacements.items():
        assert a in s, "missing text anchor: "+a[:50]
        s=s.replace(a,b,1)
    s += "\n/* "+MARK+": B1 conservative builder is intentionally not registered; B2 is the user path. */\n"
    return s
changes.append(edit("tr_texture_restore.inc",restore_text_patch))

proof={
 "version":"DarkWolf Local AI Texture Restoration B2 V1",
 "base_clean_production_run":42198541106,
 "base_clean_production_sha":"5ba3e923803674c9acee71600412720a0eeaf81e",
 "b1_infrastructure_reused":True,
 "user_visible_builder":"dw_tex_ai_build",
 "conservative_builder_registered":False,
 "model":"realesrgan-x4plus",
 "runtime":"Real-ESRGAN ncnn/Vulkan portable Win64",
 "scale":4,
 "network_at_runtime":False,
 "telemetry":False,
 "scope":"opaque BSP world diffuse textures only",
 "ab":"A original <-> B2 local AI, no vid_restart",
 "persistence":"automatic zz_dwtr_<hash>.pk3",
 "changes":changes
}
(ev/"DW_TEXTURE_AI_B2_V1_SOURCE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n")
print(json.dumps(proof,indent=2))
