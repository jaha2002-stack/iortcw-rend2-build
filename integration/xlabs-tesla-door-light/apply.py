#!/usr/bin/env python3
"""Sep18 Tesla + selective Fire/Tesla run 40187645839: Xlabs-only door arc dlight.

Only cgame source is edited. Does NOT change the actual historic Tesla arcs,
pulses, entity triggers, Fire/Tesla world occlusion, shaders, CSM or SSGI.
BSP audit: Xlabs 20 shooter_tesla, 19 lack spawnflag DLIGHT; most form
three-bolt door groups, so aggregate ONE moving-free light per authored group.
"""
from pathlib import Path
import sys,re,json,hashlib
root=Path(sys.argv[1]).resolve()
report=Path(sys.argv[2]).resolve()
sp=root/"SP/code"
h=lambda b:hashlib.sha256(b).hexdigest()
paths=[sp/"cgame/cg_main.c",sp/"cgame/cg_local.h",sp/"cgame/cg_ents.c"]
before={str(p.relative_to(root)):h(p.read_bytes()) for p in paths}
assert "DARKWOLF_TESLA_SEPTEMBER_FIRE_HARMONY_V1" in (sp/"rend2/tr_scene.c").read_text()
assert 'r_dlightWorldContainment", "2", CVAR_ARCHIVE' in (sp/"rend2/tr_init.c").read_text()
assert "DARKWOLF_UNIFIED_PRODUCTION_TESLA_TIMING_V1" not in paths[2].read_text()
renderer_before={str(p.relative_to(sp)):h(p.read_bytes())
  for p in (sp/"rend2").rglob("*") if p.is_file()}
assert len(renderer_before)>70

def one(path,anchor,replacement):
 s=path.read_text()
 assert s.count(anchor)==1,(str(path),s.count(anchor))
 path.write_text(s.replace(anchor,replacement,1))

var_anchor="vmCvar_t cg_dlightElectricIntensityScale;"
var_new=var_anchor+"""
// DARKWOLF_XLABS_TESLA_DOOR_LIGHT_V1: live CVar defaults, not read-only.
vmCvar_t cg_xlabsTeslaDoorLight;
vmCvar_t cg_xlabsTeslaDoorRadius;
vmCvar_t cg_xlabsTeslaDoorIntensity;
vmCvar_t cg_xlabsTeslaDoorShadows;
"""
one(paths[0],var_anchor,var_new)
regs='\t{ &cg_dlightElectricIntensityScale, "cg_dlightElectricIntensityScale", "1.32", CVAR_ARCHIVE },'
regs_new=regs+"""
	// These apply only to Xlabs ET_TESLA_EF entities without a native DLIGHT.
	{ &cg_xlabsTeslaDoorLight, "cg_xlabsTeslaDoorLight", "1", CVAR_ARCHIVE },
	{ &cg_xlabsTeslaDoorRadius, "cg_xlabsTeslaDoorRadius", "300", CVAR_ARCHIVE },
	{ &cg_xlabsTeslaDoorIntensity, "cg_xlabsTeslaDoorIntensity", "0.95", CVAR_ARCHIVE },
	{ &cg_xlabsTeslaDoorShadows, "cg_xlabsTeslaDoorShadows", "1", CVAR_ARCHIVE },
"""
one(paths[0],regs,regs_new)
ex='extern vmCvar_t cg_dlightElectricIntensityScale;'
one(paths[1],ex,ex+"""
// Xlabs-only supplemental Tesla door glow; editable and archived.
extern vmCvar_t cg_xlabsTeslaDoorLight;
extern vmCvar_t cg_xlabsTeslaDoorRadius;
extern vmCvar_t cg_xlabsTeslaDoorIntensity;
extern vmCvar_t cg_xlabsTeslaDoorShadows;""")

ent=paths[2]
s=ent.read_text()
entry=s.index("static void CG_Efx( centity_t *cent ) {")
start=s.index("\tif ( cent->currentState.eType == ET_TESLA_EF ) {",entry)
end=s.index("\t} else if ( cent->currentState.eType == ET_SPOTLIGHT_EF )",start)
original=s[start:end]
septsha="fc79026dcb8923bada3851bfff09ede941292e17e93a27319d22dba268fd7845"
assert h(original.replace("DARKWOLF_REF_WORLD_OCCLUSION","0").encode())==septsha
assert original.count("DARKWOLF_REF_WORLD_OCCLUSION")==2
# One isolated insertion before the existing "add dlight" block. It must not
# change one character of the original Tesla source when stripped.
anchor="		// add dlight\n		if ( cent->currentState.dl_intensity ) {"
assert original.count(anchor)==1
supplement=r'''
		// DARKWOLF_XLABS_TESLA_DOOR_LIGHT_V1
		// Map-authoring check: Xlabs door arcs have no native DLIGHT (19/20
		// Tesla shooters, many in 48-unit spaced triplets). Their bright bolt
		// shader therefore cannot illuminate the wall, door or floor.
		// Restrict this light to Xlabs and non-DLIGHT sources; keep the exact
		// September CG_Efx bolt and authored Tesla light code below intact.
		if ( !cent->currentState.dl_intensity && cg_xlabsTeslaDoorLight.integer
			&& strstr( cgs.mapname, "xlabs" ) != NULL && cg.snap ) {
			int k, leader = cent->currentState.number, count = 0;
			qboolean nativeLightInGroup = qfalse;
			vec3_t center, boltMid, segment;
			float pulse, radius, energy;
			VectorClear( center );
			// Group only co-visible authored Tesla bolts whose generator
			// origins are <=112 units apart and have the same trigger class.
			// Middle triplet emits ONE shadow-casting light, preventing triple
			// cubemap captures and competition for the two dynamic slots.
			for ( k = 0; k < cg.snap->numEntities; ++k ) {
				const entityState_t *other = &cg.snap->entities[k];
				vec3_t separation;
				if ( other->eType != ET_TESLA_EF ||
					 other->effect3Time != cent->currentState.effect3Time )
					continue;
				VectorSubtract( other->origin, cent->currentState.origin, separation );
				if ( DotProduct( separation, separation ) > 112.0f * 112.0f )
					continue;
				if ( other->dl_intensity ) {
					nativeLightInGroup = qtrue;
					continue;
				}
				if ( other->number < leader ) leader = other->number;
				VectorSubtract( other->origin2, other->origin, segment );
				VectorMA( other->origin, 0.48f, segment, boltMid );
				VectorAdd( center, boltMid, center );
				++count;
			}
			if ( !nativeLightInGroup && count > 0 &&
				cent->currentState.number == leader ) {
				VectorScale( center, 1.0f / (float)count, center );
				radius = Com_Clamp( 128.0f, 550.0f, cg_xlabsTeslaDoorRadius.value );
				energy = Com_Clamp( 0.0f, 1.8f, cg_xlabsTeslaDoorIntensity.value );
				pulse = 0.90f + 0.10f * sin( 0.019f * (float)cg.time
					+ 0.73f * (float)cent->currentState.number );
				if ( energy > 0.0f ) {
					// Uses existing Rend2 electric color and shadow-budget
					// pipeline. No new GL pass, no shader changes.
					CG_AddEffectLightToScene( center, radius * pulse,
						0.12f * energy * pulse,
						0.37f * energy * pulse,
						0.78f * energy * pulse,
						cg_xlabsTeslaDoorShadows.integer ? DARKWOLF_REF_WORLD_OCCLUSION : 0,
						cg_xlabsTeslaDoorShadows.integer
							? CG_EFFECTLIGHT_ENVIRONMENTAL_TESLA
							: CG_EFFECTLIGHT_ELECTRIC );
				}
			}
		}
'''
assert "DARKWOLF_XLABS_TESLA_DOOR_LIGHT_V1" not in s
modified=s.replace(anchor,supplement+"\n"+anchor,1)
ent.write_text(modified)
ns=ent.read_text()
i=ns.index(supplement)
restored=ns[:i]+ns[i+len(supplement)+1:]
assert restored==s, "Entire original CG_Efx must survive byte for byte"
restored_branch=restored[restored.index("\tif ( cent->currentState.eType == ET_TESLA_EF ) {",entry):
                         restored.index("\t} else if ( cent->currentState.eType == ET_SPOTLIGHT_EF )",entry)]
assert h(restored_branch.replace("DARKWOLF_REF_WORLD_OCCLUSION","0").encode())==septsha
assert "if ( cent->currentState.dl_intensity ) {" in ns
assert "strstr( cgs.mapname, \"xlabs\" )" in ns

renderer_after={str(p.relative_to(sp)):h(p.read_bytes())
  for p in (sp/"rend2").rglob("*") if p.is_file()}
assert renderer_before==renderer_after, "NO renderer modification permitted"
after={str(p.relative_to(root)):h(p.read_bytes()) for p in paths}
assert len([k for k in before if before[k]!=after[k]])==3
assert 'r_lightmap && r_lightmap->integer' in (sp/"rend2/tr_backend.c").read_text()
report.parent.mkdir(parents=True,exist_ok=True)
manifest={
 "base_run":40187645839,
 "base_git_sha":"326383604bde9a071e383f76c5ac49f33228f87f",
 "baseline_release_artifact":12596471801,
 "patched_source_files":sorted(after),
 "source_before":before,"source_after":after,
 "renderer_files_bit_identical":len(renderer_before),
 "september_tesla_original_normalized_sha256":septsha,
 "original_Tesla_effect_logic_byte_identical_after_removing_addendum":True,
 "map_restriction":"xlabs only",
 "dlight_authoring_precondition":"ET_TESLA_EF without dl_intensity",
 "door_grouping":"One light per co-visible <=112u 3-bolt authored group; suppress near native DLIGHT",
 "blue_radiance_base_rgb":[0.12,0.37,0.78],
 "live_cvars":{"cg_xlabsTeslaDoorLight":1,"cg_xlabsTeslaDoorRadius":300,
     "cg_xlabsTeslaDoorIntensity":0.95,"cg_xlabsTeslaDoorShadows":1},
 "shadow_path":"CG_EFFECTLIGHT_ENVIRONMENTAL_TESLA => Rend2 native point light cubemap dynamic slots",
 "preserved":["September Tesla bolts and pulse","Fire/Tesla containment 2","SSGI lightmap fix",
   "FourWeek V03 effects","neutral LUT","all other maps"],
 "linux_and_windows_gameplay_proof":"PENDING"
}
report.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("XLABS_TESLA_DOOR_SHADOWED_DLIGHT_SOURCE_ONLY_CGAME_PASS",
      json.dumps({"source_files":3,"renderer_unchanged":True,
        "september_tesla_sha":septsha,"group":True,"shadows":True}),flush=True)
