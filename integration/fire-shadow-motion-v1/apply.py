#!/usr/bin/env python3
"""Opt-in one-real-torch Crypt1 fire shadow motion, exact production source only."""
from pathlib import Path
import sys, hashlib, json
source=Path(sys.argv[1] if len(sys.argv)>1 else "source")
p=source/"SP/code/rend2/tr_scene.c"
s=p.read_text()
marker="DARKWOLF_FIRE_SHADOW_MOTION_V1_CRYPT1_291"
assert marker not in s, "Already applied"
anchor="\tR_IFLC_Frame(fd);\n\n\tRE_BeginScene(fd);"
assert s.count(anchor)==1, ("Expected unique post-IFLC pre-RE_BeginScene hook",s.count(anchor))
helper=r"""
// DARKWOLF_FIRE_SHADOW_MOTION_V1_CRYPT1_291
// Deliberately only the verified real Crypt1 authored fire #291. Disabled by default.
// Apply after native fire ownership and IFLC have resolved the unmodified authored
// origin, and before RE_BeginScene snapshots all DLight positions into the refdef.
// One DLight: never append synthetic partners or affect static promotion/slot budgets.
// 80ms phase hold allows world cubemap cache hits between updates; no per-frame RNG.
static void R_DWFireShadowMotionV1Frame(const refdef_t *fd)
{
	static cvar_t *enabled = NULL, *amplitude = NULL;
	int i, match = -1, matches = 0;
	int tick;
	float ms, amp;
	dlight_t *dl;
	if (!enabled) enabled = ri.Cvar_Get("r_dwFireShadowMotion", "0", CVAR_ARCHIVE);
	if (!amplitude) amplitude = ri.Cvar_Get("r_dwFireShadowMotionAmplitude", "2", CVAR_ARCHIVE);
	if (!enabled || !enabled->integer || !fd || !tr.world ||
		Q_stricmp(tr.world->baseName, "crypt1") ||
		(fd->rdflags & (RDF_NOWORLDMODEL | RDF_SKYBOXPORTAL)))
		return;
	if (!amplitude) return;
	amp = Com_Clamp(0.0f, 4.0f, amplitude->value);
	if (amp <= 0.0f) return;

	for (i = r_firstSceneDlight; i < r_numdlights && i < MAX_DLIGHTS; ++i)
	{
		const dlight_t *candidate = &backEndData->dlights[i];
		if (!candidate->nativeAuthoredDlight ||
			!candidate->fireVolumetricSource ||
			candidate->shadowSourceClass != DWSHADOW_SOURCE_PERSISTENT_FIRE ||
			candidate->fireVolumetricNativeOrdinal != 291 ||
			candidate->staticPromoteFixtureId >= 0 ||
			fabsf(candidate->origin[0] + 152.0f) > 3.0f ||
			fabsf(candidate->origin[1] - 1668.0f) > 3.0f ||
			fabsf(candidate->origin[2] - 636.0f) > 3.0f)
			continue;
		match = i;
		++matches;
	}
	// Fail closed on missing or ambiguous physical ownership.
	if (matches != 1) return;

	dl = &backEndData->dlights[match];
	tick = fd->time > 0 ? fd->time / 80 : 0;
	ms = (float)(tick * 80);
	// Small non-repeating coupled oscillations; never edit the flame model.
	dl->origin[0] += amp * (0.52f * sinf(ms * 0.00383f) +
	                          0.18f * sinf(ms * 0.00837f + 0.9f));
	dl->origin[1] += amp * (0.46f * sinf(ms * 0.00493f + 1.4f) +
	                          0.14f * sinf(ms * 0.00921f));
	dl->origin[2] += amp * 0.22f * sinf(ms * 0.00531f + 2.1f);
}
"""
# Function before RE_RenderScene rather than inside it.
function_anchor="void RE_RenderScene( const refdef_t *fd ) {"
assert s.count(function_anchor)==1
s=s.replace(function_anchor,helper+"\n"+function_anchor,1)
s=s.replace(anchor,"\tR_IFLC_Frame(fd);\n\tR_DWFireShadowMotionV1Frame(fd); // "+marker+"\n\n\tRE_BeginScene(fd);",1)
p.write_text(s)
assert s.count("R_DWFireShadowMotionV1Frame(fd);")==1
assert s.count(marker)==2
print("DW_FSM_V1_CRYPT1_291_APPLY_PASS",hashlib.sha256(s.encode()).hexdigest())
