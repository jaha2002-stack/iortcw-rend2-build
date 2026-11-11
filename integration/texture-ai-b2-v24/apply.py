#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve(); ev.mkdir(parents=True,exist_ok=True)
code=src/"SP/code/rend2"
here=Path(__file__).resolve().parent
MARK="DARKWOLF_TEXTURE_AI_B2_V24"

def edit(rel,fn):
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

shutil.copy2(here/"tr_texture_ai_b2_v24.inc", code/"tr_texture_ai_b2_v24.inc")
changes=[]

def local_patch(s):
    anchor="void R_DWTextureSaveV23_f(void);\n"
    assert s.count(anchor)==1, ("local anchor",s.count(anchor))
    return s.replace(anchor,anchor+"""/* DARKWOLF_TEXTURE_AI_B2_V24 */
void R_DWTexturePickV24_f(void);
void R_DWTextureInfoV24_f(void);
""",1)
changes.append(edit("tr_local.h",local_patch))

def world_patch(s):
    return s + "\n/* "+MARK+": universal safe texture picker */\n#include \"tr_texture_ai_b2_v24.inc\"\n"
changes.append(edit("tr_world.c",world_patch))

def init_patch(s):
    old='\tri.Cmd_AddCommand( "dw_tex_pick", R_DWTexturePickV22_f );\n'
    assert s.count(old)==1, ("pick anchor",s.count(old))
    s=s.replace(old,
      '\t/* DARKWOLF_TEXTURE_AI_B2_V24 */\n'
      '\tri.Cmd_AddCommand( "dw_tex_pick", R_DWTexturePickV24_f );\n',1)

    old='\tri.Cmd_AddCommand( "dw_tex_info", R_DWTextureInfoV22_f );\n'
    assert s.count(old)==1, ("info anchor",s.count(old))
    s=s.replace(old,'\tri.Cmd_AddCommand( "dw_tex_info", R_DWTextureInfoV24_f );\n',1)
    return s
changes.append(edit("tr_init.c",init_patch))

proof={
 "version":"DarkWolf Local AI Texture Restoration B2 V2.4 Universal Texture Picker",
 "base_unified_run":42736840967,
 "base_unified_commit":"2cca3afcbe908b3f07d99afa6fd1085bc223d883",
 "inherits_b2_v23_commit":"aa60e4d0c68260b6752920cddd8011b718c7dbba",
 "scope":"picker-only expansion; AI/persistence unchanged",
 "picker":{
   "world_bsp":True,
   "brush_model_entities":True,
   "scaled_brush_entities":True,
   "md3_mdc_mod_mesh":True,
   "custom_shader":True,
   "custom_skin":True,
   "animated_frame_raycast":True,
   "nearest_hit_shared_distance":True,
   "sky_supported":False,
   "water_supported":False,
   "slime_lava_supported":False,
   "portal_supported":False,
   "mds_mdr_iqm_supported":False
 },
 "preserved":{
   "realesrgan_model":"realesrgan-x4plus",
   "variants":["FAITHFUL","BALANCED","STRONG"],
   "cumulative_pk3":"zzzzzz_DW_TextureRestoration.pk3",
   "pending_promotion":True,
   "network_at_runtime":False,
   "telemetry":False
 },
 "changes":changes
}
(ev/"DW_TEXTURE_AI_B2_V24_SOURCE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n")
print(json.dumps(proof,indent=2))
