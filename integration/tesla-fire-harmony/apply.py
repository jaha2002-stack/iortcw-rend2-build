#!/usr/bin/env python3
"""Surgical Fire/Tesla architectural world-occlusion over actual Sep18 Tesla-parity V03.

Reintroduce the original architectural depth pass, but ONLY for native authored
FireVol fire emitters and the stationary ET_TESLA_EF effect. September Tesla's
timing/positions/pulses/colors/bolt-crawl are untouched; no world marker is added
to generic lamps, local promoted lights, weapon Tesla or other transients.

Allow live CVar r_dlightWorldContainment: 0=none, 1=fire, 2=fire+stationary Tesla.
"""
from pathlib import Path
import hashlib,json,re,subprocess,sys
root=Path(sys.argv[1]).resolve()
original_patch=Path(sys.argv[2]).resolve()
out=Path(sys.argv[3]).resolve()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(original_patch.read_bytes())=="e3600847ed0d1def868439af0c94f5ce250e2e7afbb0584fbb151459ea009a2f"
base=root/"SP/code"
before={str(p.relative_to(root)):sha(p.read_bytes()) for p in (root/"SP/code").rglob("*") if p.is_file()}
assert len(before)>100
assert "DARKWOLF_CRYPT1_LIGHTMAP_SSGI_ISOLATION_V1" in (base/"rend2/tr_backend.c").read_text()
assert "DlightWorldVisibility" not in (base/"rend2/glsl/dlight_fp.glsl").read_text()
assert "DARKWOLF_REF_WORLD_OCCLUSION" not in (base/"qcommon/q_shared.h").read_text()
assert "DARKWOLF_UNIFIED_PRODUCTION_TESLA_TIMING_V1" not in (base/"cgame/cg_ents.c").read_text()

t=original_patch.read_text()
chunks=[piece for piece in re.split(r'(?=^diff --git a/)',t,flags=re.M) if piece.strip()]
assert len(chunks)==15 and all(x.startswith("diff --git a/") for x in chunks),len(chunks)
headers=[x.splitlines()[0] for x in chunks]
assert len(set(headers))==15
assert any("cg_ents.c" in x for x in headers)
filtered="".join(x for x in chunks if not x.startswith("diff --git a/SP/code/cgame/cg_ents.c "))
assert len(re.findall(r'^diff --git ',filtered,re.M))==14
patch=out.parent/"original_architecture_without_tesla_light_timing.patch"
patch.parent.mkdir(parents=True,exist_ok=True)
patch.write_text(filtered)
subprocess.run(["git","-C",str(root),"apply","--check",str(patch)],check=True)
subprocess.run(["git","-C",str(root),"apply",str(patch)],check=True)

# Mark JUST stationary Tesla effect lights (ET_TESLA_EF), not generic electric,
# explosion, weapon muzzle, or fire particle. Change two argument flags ONLY.
cg=base/"cgame/cg_ents.c"
source=cg.read_text()
entry=source.index("static void CG_Efx( centity_t *cent ) {")
start=source.index("\tif ( cent->currentState.eType == ET_TESLA_EF ) {",entry)
end=source.index("\t} else if ( cent->currentState.eType == ET_SPOTLIGHT_EF )",start)
block=source[start:end]
SEPT_SHA="fc79026dcb8923bada3851bfff09ede941292e17e93a27319d22dba268fd7845"
assert sha(block.encode())==SEPT_SHA,("baseline Sep18 Tesla semantics drift",sha(block.encode()))
orig_whole_sha=sha(source.encode())
first="( (float)b / 255.0f ) * pulse, 0,\n\t\t\t\t\tteslaLightType );"
second="(float)r / 255.0f, (float)g / 255.0f, (float)b / 255.0f, 0,\n\t\t\t\t\t\tteslaLightType );"
assert block.count(first)==block.count(second)==1
converted=block.replace(first,first.replace(", 0,",", DARKWOLF_REF_WORLD_OCCLUSION,"))
converted=converted.replace(second,second.replace(", 0,",", DARKWOLF_REF_WORLD_OCCLUSION,"))
assert converted.count("DARKWOLF_REF_WORLD_OCCLUSION")==2
assert converted.replace("DARKWOLF_REF_WORLD_OCCLUSION","0")==block
cg.write_text(source[:start]+converted+source[end:])
assert sha((source[:start]+block+source[end:]).encode())==orig_whole_sha
assert "DARKWOLF_UNIFIED_PRODUCTION_TESLA_TIMING_V1" not in cg.read_text()

# Original Oct15 bug: all 32 native authored lights were marked, including lamps.
# Apply world-depth to existing, explicitly classified FireVol emitters instead,
# and to the stationary Tesla effect via the opaque marker (above).
scene=base/"rend2/tr_scene.c";text=scene.read_text()
old="dl->worldOcclusion = worldOcclusionMarker || nativeAuthoredDlightMarker;"
new='''// DARKWOLF_TESLA_SEPTEMBER_FIRE_HARMONY_V1:
	// Never touch native authored lamps or promoted static lights.
	// Fire speaker classification already uses the approved FireVol source matcher.
	// A Tesla marker is passed only by ET_TESLA_EF, and does not change Tesla light energy.
	dl->worldOcclusion = ((r_dlightWorldContainment->integer >= 2) && worldOcclusionMarker)
		|| ((r_dlightWorldContainment->integer >= 1) && fireVolumetricSourceMarker);'''
assert text.count(old)==1
scene.write_text(text.replace(old,new,1))
# Both modes are live-editable, not ROM/CHEAT/LATCH. CVar defaults for historical
# effects remain unchanged, including forceSun, dlightMode 2 and SSGI.
ini=base/"rend2/tr_init.c";s=ini.read_text()
decl="cvar_t  *r_dlightMode;"
assert s.count(decl)==1
s=s.replace(decl,decl+'''\ncvar_t  *r_dlightWorldContainment; // user-adjustable: 0 off, 1 fire, 2 fire+stationary Tesla''',1)
registered='r_dlightMode = ri.Cvar_Get( "r_dlightMode", "2", CVAR_ARCHIVE | CVAR_LATCH );'
assert s.count(registered)==1
s=s.replace(registered,registered+'''
	// Surgical architectural containment: default on for fire and map Tesla;
	// changing it in the console takes effect at the next scene/frame.
	r_dlightWorldContainment = ri.Cvar_Get( "r_dlightWorldContainment", "2", CVAR_ARCHIVE );
	ri.Cvar_CheckRange( r_dlightWorldContainment, 0, 2, qtrue );''',1)
ini.write_text(s)
hdr=base/"rend2/tr_local.h";s=hdr.read_text()
extern="extern  cvar_t  *r_dlightMode;"
assert s.count(extern)==1
hdr.write_text(s.replace(extern,extern+'\nextern  cvar_t  *r_dlightWorldContainment;',1))

# Verify the approved September Tesla logic with a masked exact byte comparison.
ss=cg.read_text();st=ss.index("\tif ( cent->currentState.eType == ET_TESLA_EF ) {",ss.index("static void CG_Efx("))
ed=ss.index("\t} else if ( cent->currentState.eType == ET_SPOTLIGHT_EF )",st)
assert sha(ss[st:ed].replace("DARKWOLF_REF_WORLD_OCCLUSION","0").encode())==SEPT_SHA
assert sha((ss[:st]+ss[st:ed].replace("DARKWOLF_REF_WORLD_OCCLUSION","0")+ss[ed:]).encode())==orig_whole_sha

after={str(p.relative_to(root)):sha(p.read_bytes()) for p in (root/"SP/code").rglob("*") if p.is_file()}
actual=sorted(k for k in before if after[k]!=before[k])
expected=sorted(set(re.search(r'^diff --git a/([^ ]+)',x,re.M).group(1) for x in chunks)
                | {"SP/code/rend2/tr_init.c"})
assert actual==expected,("unexpected production changes",sorted(set(actual)^set(expected)))
assert len(actual)==16
for unchanged in ("SP/code/cgame/cg_main.c","SP/code/game/g_misc.c",
                  "SP/code/rend2/glsl/ssgi_fp.glsl","SP/code/rend2/tr_flares.c"):
    assert before[unchanged]==after[unchanged],unchanged
assert "!(r_lightmap && r_lightmap->integer)" in (base/"rend2/tr_backend.c").read_text()
assert "DlightWorldVisibility" in (base/"rend2/glsl/dlight_fp.glsl").read_text()
assert "DlightWorldVisibility" in (base/"rend2/glsl/lightall_fp.glsl").read_text()
assert 'r_dlightWorldContainment", "2", CVAR_ARCHIVE' in ini.read_text()
assert "worldOcclusionMarker || nativeAuthoredDlightMarker" not in scene.read_text()
assert 'fireVolumetricSourceMarker' in scene.read_text()

manifest={
 "base":"EXACT_SEPTEMBER_TESLA_PARITY_FOURWEEK_V03_RELEASE_40186479404",
 "source":"Sep18 Clean Production patch + FourWeek V03 accepted features + exact Sep Tesla source",
 "original_oct15_architectural_patch_sha256":sha(original_patch.read_bytes()),
 "original_patch_files":15,"original_non_tesla_patch_files":14,
 "changed_source_files":actual,
 "stationary_tesla_CG_Efx_original_SHA256":SEPT_SHA,
 "stationary_tesla_normalized_postpatch_SHA256":sha(ss[st:ed].replace("DARKWOLF_REF_WORLD_OCCLUSION","0").encode()),
 "Tesla_code_unchanged_except_two_nonvisual_world_visibility_flags":True,
 "Tesla_light_radius_color_origin_pulse_bolt_timing_rhythm_unchanged":True,
 "cg_main_game_tesla_source_unchanged":True,
 "architectural_cubemap":"EXACT_ORIGINAL_BASIS_CAPTURE",
 "architectural_source_eligibility":"FIREVOL_MATCHED_NATIVE_FIRE_OR_EXPLICIT_ET_TESLA_EF_ONLY",
 "native_authored_lamps_shadowed_by_architecture":False,
 "other_light_sources_and_promoted_lamps_unchanged":True,
 "source_control_CVar":{"name":"r_dlightWorldContainment","default":"2","flags":"CVAR_ARCHIVE","runtime_editable":True,
    "0":"original September lighting, world containment disabled",
    "1":"contain matched fire only; original September Tesla visual",
    "2":"contain matched fire and stationary Tesla"},
 "SSGI_lightmap_stripes":"PREVIOUS_FIX_PRESERVED",
 "LUT_default_strength":"0.00_PRESERVED",
 "negative_controls":["No PCF4","No Oct SSGI Fire V04","No changes to 9/18 Tesla timer or bolt crawl"],
 "render_performance_and_gpu_visual":"REQUIRES_REAL_GAME_AB"
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
print("SEPT_TESLA_PULSE_UNCHANGED_FIRE_AND_TESLA_TARGETED_CONTAINMENT_SOURCE_PASS",json.dumps({
 "modified_files":len(actual),"tesla_branch_sha":SEPT_SHA,"mutable_switch":True,
 "excluded_native_lamps":True,"fire_matches_only":True}),flush=True)
