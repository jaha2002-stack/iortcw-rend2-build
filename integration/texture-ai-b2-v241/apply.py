#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve(); ev.mkdir(parents=True,exist_ok=True)
p=src/"SP/code/rend2/tr_texture_ai_b2_v24.inc"
before=p.read_text()
MARK="DARKWOLF_TEXTURE_AI_B2_V241"
assert MARK not in before
s=before

old='''            if (surfIndex < 0 || surfIndex >= tr.world->numWorldSurfaces) {
                continue;
            }
'''
new='''            /* DARKWOLF_TEXTURE_AI_B2_V241:
             * Inline BSP models use the shared world->surfaces array, but their
             * firstSurface commonly starts after numWorldSurfaces.  The valid
             * upper bound is total numsurfaces, not world-only surfaces. */
            if (surfIndex < 0 || surfIndex >= tr.world->numsurfaces) {
                continue;
            }
'''
assert s.count(old)==1, s.count(old)
s=s.replace(old,new,1)

old='''        model = R_GetModelByHandle(ent->e.hModel);
        if (!model || model->type != MOD_MESH) {
            continue;
        }

        mdv = DWTRV24_GetMDV0(model);
'''
new='''        model = R_GetModelByHandle(ent->e.hModel);
        if (!model || model->type != MOD_MESH) {
            continue;
        }

        /* DARKWOLF_TEXTURE_AI_B2_V241:
         * Do not let invisible local-player/view models intercept an
         * environment texture pick.  Character and weapon meshes are outside
         * this environment-restoration tool's scope. */
        if (ent->e.renderfx & (RF_THIRD_PERSON | RF_FIRST_PERSON | RF_DEPTHHACK)) {
            continue;
        }
        if (!Q_stricmpn(model->name, "models/players/", 15) ||
            !Q_stricmpn(model->name, "models/weapons2/", 16) ||
            !Q_stricmpn(model->name, "models/weapons/", 15)) {
            continue;
        }

        mdv = DWTRV24_GetMDV0(model);
'''
assert s.count(old)==1, s.count(old)
s=s.replace(old,new,1)

s=s.replace("DWTR AI B2 V2.4:", "DWTR AI B2 V2.4.1:")
s=s.replace("B2 V2.4 Universal Texture Picker", "B2 V2.4.1 Universal Texture Picker")
s += "\n/* DARKWOLF_TEXTURE_AI_B2_V241: inline-brush range fix + player/viewmodel exclusion */\n"

p.write_text(s)

proof={
 "version":"DarkWolf Local AI Texture Restoration B2 V2.4.1",
 "base_v24_run":42930103256,
 "base_v24_commit":"d6f24744f895e9c602b1b6606c6826f3c92595b9",
 "fixes":{
   "inline_brush_surface_bound":"tr.world->numsurfaces",
   "old_wrong_bound":"tr.world->numWorldSurfaces",
   "player_viewmodel_interception":True,
   "excluded_renderfx":["RF_THIRD_PERSON","RF_FIRST_PERSON","RF_DEPTHHACK"],
   "excluded_model_prefixes":["models/players/","models/weapons2/","models/weapons/"]
 },
 "preserved":{
   "ai_pipeline":"B2 V2.3",
   "cumulative_pk3":"zzzzzz_DW_TextureRestoration.pk3",
   "sky_supported":False,
   "water_supported":False,
   "pbr_owner_renderer_features_unchanged":True
 },
 "file":"SP/code/rend2/tr_texture_ai_b2_v24.inc",
 "before":hashlib.sha256(before.encode()).hexdigest(),
 "after":hashlib.sha256(s.encode()).hexdigest()
}
(ev/"DW_TEXTURE_AI_B2_V241_SOURCE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n")
print(json.dumps(proof,indent=2))
