#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve(); ev.mkdir(parents=True,exist_ok=True)
code=src/"SP/code/rend2"
here=Path(__file__).resolve().parent
MARK="DARKWOLF_TEXTURE_AI_B2_V22"

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

shutil.copy2(here/"tr_texture_ai_b2_v22.inc", code/"tr_texture_ai_b2_v22.inc")
changes=[]

def local_patch(s):
    anchor="void R_DWTextureSaveV2_f(void);\n"
    assert s.count(anchor)==1, ("local anchor",s.count(anchor))
    return s.replace(anchor,anchor+"""/* DARKWOLF_TEXTURE_AI_B2_V22 */
void R_DWTextureV22CleanupLegacyPaks(const char *home, const char *game,
                                     unsigned int hash, const char *keepPhysical);
void R_DWTexturePickV22_f(void);
void R_DWTextureInfoV22_f(void);
""",1)
changes.append(edit("tr_local.h",local_patch))

def world_patch(s):
    return s + "\n/* "+MARK+": deterministic persistence + brush model picker */\n#include \"tr_texture_ai_b2_v22.inc\"\n"
changes.append(edit("tr_world.c",world_patch))

def init_patch(s):
    old='\tri.Cmd_AddCommand( "dw_tex_pick", R_DWTexturePick_f );\n'
    assert s.count(old)==1, ("pick anchor",s.count(old))
    s=s.replace(old,
      '\t/* DARKWOLF_TEXTURE_AI_B2_V22 */\n'
      '\tri.Cmd_AddCommand( "dw_tex_pick", R_DWTexturePickV22_f );\n',1)

    old='\tri.Cmd_AddCommand( "dw_tex_info", R_DWTextureInfoV2_f );\n'
    assert s.count(old)==1, ("info anchor",s.count(old))
    s=s.replace(old,
      '\tri.Cmd_AddCommand( "dw_tex_info", R_DWTextureInfoV22_f );\n',1)
    return s
changes.append(edit("tr_init.c",init_patch))

def v2_patch(s):
    old='Com_sprintf(pk3Name, sizeof(pk3Name), "zzz_dwtr_%08x.pk3", hash);'
    assert s.count(old)==1, ("pk3 prefix anchor",s.count(old))
    s=s.replace(old,
      'Com_sprintf(pk3Name, sizeof(pk3Name), "zzzzzz_dwtr_%08x.pk3", hash);',1)

    old='''    if (!DWTRV2_WritePhysicalPK3(pk3Physical, internal,
                                 encoded, encodedLen,
                                 manifestInternal,
                                 (const byte *)manifest, (int)strlen(manifest))) {
        ri.Free(encoded);
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2: PK3 save failed; game remains running.\\n");
        return;
    }
    ri.Free(encoded);
'''
    assert s.count(old)==1, ("save success anchor",s.count(old))
    new='''    if (!DWTRV2_WritePhysicalPK3(pk3Physical, internal,
                                 encoded, encodedLen,
                                 manifestInternal,
                                 (const byte *)manifest, (int)strlen(manifest))) {
        ri.Free(encoded);
        ri.Printf(PRINT_WARNING, "DWTR AI B2 V2.2: PK3 save failed; game remains running.\\n");
        return;
    }
    ri.Free(encoded);

    /* B2 V2.2: exactly one persistent pack per texture qpath.
     * The stable hash gives the same filename every time; after a successful
     * replacement, remove only known DWTR legacy prefix variants for this hash. */
    R_DWTextureV22CleanupLegacyPaks(home, game, hash, pk3Physical);
'''
    s=s.replace(old,new,1)

    s=s.replace("DarkWolf Local AI Texture Restoration B2 V2\\n",
                "DarkWolf Local AI Texture Restoration B2 V2.2\\n",1)
    s=s.replace("DWTR AI B2 V2.1: SAVED %s variant=%s. It will override %s after restart.\\n",
                "DWTR AI B2 V2.2: SAVED %s variant=%s. It will override %s after restart.\\n",1)
    s=s.replace("DWTR AI B2 V2.1: physical PK3=%s\\n",
                "DWTR AI B2 V2.2: physical PK3=%s\\n",1)
    s += "\n/* "+MARK+": one deterministic zzzzzz_dwtr pack per texture hash */\n"
    return s
changes.append(edit("tr_texture_ai_b2_v2.inc",v2_patch))

proof={
 "version":"DarkWolf Local AI Texture Restoration B2 V2.2",
 "base_clean_production_run":42198541106,
 "inherits_b2_v2_run":42574596120,
 "persistence":{
   "stable_prefix":"zzzzzz_dwtr_",
   "key":"FNV1a normalized texture qpath",
   "same_texture_repeated_save":"same filename, atomic replacement",
   "legacy_cleanup":"after successful save remove only 2..10-z DWTR filenames with same hash",
   "one_pack_per_texture":True
 },
 "picker":{
   "world_bsp":True,
   "brush_model_entities":True,
   "targets":"func_door / rotating doors / lifts / inline brush models",
   "nearest_hit":"WORLD and BRUSH compete on same ray distance",
   "console_source_label":True,
   "scaled_brush_entities":"skipped in V2.2 to keep distance comparison safe"
 },
 "network_at_runtime":False,
 "telemetry":False,
 "changes":changes
}
(ev/"DW_TEXTURE_AI_B2_V22_SOURCE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n")
print(json.dumps(proof,indent=2))
