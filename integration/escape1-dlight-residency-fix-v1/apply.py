#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve()
ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
scene=root/'tr_scene.c'
inc_src=Path(__file__).with_name('tr_escape1_dlight_residency_fix.inc')
inc_dst=root/'tr_escape1_dlight_residency_fix.inc'
text=scene.read_text()

include_anchor='// DARKWOLF_USLRD_ALWAYS_ON_DIRECT_SHADOW_CAPTURE_FIX_V1\n'
assert text.count(include_anchor)>=1
if '#include "tr_escape1_dlight_residency_fix.inc"' not in text:
    text=text.replace(include_anchor,'#include "tr_escape1_dlight_residency_fix.inc"\n\n'+include_anchor,1)

old='''	if (allAcceptedDelivery)
	{
		for (priority = 0; priority <= 6 && selectedCount < s_uslrdStaticBudget; ++priority)
		{
			for (retainedPass = 0; retainedPass < 2 && selectedCount < s_uslrdStaticBudget; ++retainedPass)
			{
				for (i = 0; i < s_staticPromotePersistentCount && selectedCount < s_uslrdStaticBudget; ++i)
				{
					staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
					if (selectedFlags[i] || !light->unifiedClassAccepted || light->unifiedNativeRuntimePresent)
						continue;
					if (R_StaticPromoteUSLRDPriority(light) != priority)
						continue;
					if ((retainedPass == 0) != (light->unifiedWasResident ? 1 : 0))
						continue;
					selected[selectedCount] = light;
					selectedFlags[i] = 1;
					light->unifiedResident = qtrue;
					light->unifiedRoute = USLRD_ROUTE_PROMOTED;
					light->unifiedSelectedSlot = selectedCount;
					selectedCount++;
				}
			}
		}
	}
	else
	{
		// Parent A/B path: current physical relevance is the outer criterion.
'''
new='''	if (allAcceptedDelivery &&
		!R_DarkWolfEscape1OverflowRelevantSelection(eligiblePromoted, s_uslrdStaticBudget))
	{
		for (priority = 0; priority <= 6 && selectedCount < s_uslrdStaticBudget; ++priority)
		{
			for (retainedPass = 0; retainedPass < 2 && selectedCount < s_uslrdStaticBudget; ++retainedPass)
			{
				for (i = 0; i < s_staticPromotePersistentCount && selectedCount < s_uslrdStaticBudget; ++i)
				{
					staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
					if (selectedFlags[i] || !light->unifiedClassAccepted || light->unifiedNativeRuntimePresent)
						continue;
					if (R_StaticPromoteUSLRDPriority(light) != priority)
						continue;
					if ((retainedPass == 0) != (light->unifiedWasResident ? 1 : 0))
						continue;
					selected[selectedCount] = light;
					selectedFlags[i] = 1;
					light->unifiedResident = qtrue;
					light->unifiedRoute = USLRD_ROUTE_PROMOTED;
					light->unifiedSelectedSlot = selectedCount;
					selectedCount++;
				}
			}
		}
	}
	else if (allAcceptedDelivery)
	{
		// DARKWOLF_ESCAPE1_DLIGHT_RESIDENCY_FIX_V1:
		// Overflow only. FORCE ON remains absolute; all other accepted fixtures are
		// ordered by current physical relevance before their static priority.
		// This keeps a visible room lamp from losing its slot to a LATENT lamp when
		// native DLight count changes. No camera distance participates.
		priority = 0;
		for (retainedPass = 0; retainedPass < 2 && selectedCount < s_uslrdStaticBudget; ++retainedPass)
		{
			for (i = 0; i < s_staticPromotePersistentCount && selectedCount < s_uslrdStaticBudget; ++i)
			{
				staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
				if (selectedFlags[i] || !light->unifiedClassAccepted || light->unifiedNativeRuntimePresent)
					continue;
				if (R_StaticPromoteUSLRDPriority(light) != 0)
					continue;
				if ((retainedPass == 0) != (light->unifiedWasResident ? 1 : 0))
					continue;
				selected[selectedCount] = light;
				selectedFlags[i] = 1;
				light->unifiedResident = qtrue;
				light->unifiedRoute = USLRD_ROUTE_PROMOTED;
				light->unifiedSelectedSlot = selectedCount;
				selectedCount++;
			}
		}
		for (tier = DWSP_TIER_SURFACE_VISIBLE; tier <= DWSP_TIER_LATENT &&
			selectedCount < s_uslrdStaticBudget; ++tier)
		{
			for (priority = 1; priority <= 6 && selectedCount < s_uslrdStaticBudget; ++priority)
			{
				for (retainedPass = 0; retainedPass < 2 && selectedCount < s_uslrdStaticBudget; ++retainedPass)
				{
					for (i = 0; i < s_staticPromotePersistentCount && selectedCount < s_uslrdStaticBudget; ++i)
					{
						staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
						if (selectedFlags[i] || !light->unifiedClassAccepted || light->unifiedNativeRuntimePresent)
							continue;
						if (light->unifiedVisibilityTier != tier)
							continue;
						if (R_StaticPromoteUSLRDPriority(light) != priority)
							continue;
						if ((retainedPass == 0) != (light->unifiedWasResident ? 1 : 0))
							continue;
						selected[selectedCount] = light;
						selectedFlags[i] = 1;
						light->unifiedResident = qtrue;
						light->unifiedRoute = USLRD_ROUTE_PROMOTED;
						light->unifiedSelectedSlot = selectedCount;
						selectedCount++;
					}
				}
			}
		}
	}
	else
	{
		// Parent A/B path: current physical relevance is the outer criterion.
'''
assert text.count(old)==1,text.count(old)
text=text.replace(old,new,1)

needle='''	if (classifierRejectedOut) *classifierRejectedOut = classifierRejected;
	return selectedCount;
}
'''
repl='''	if (classifierRejectedOut) *classifierRejectedOut = classifierRejected;
	R_DarkWolfEscape1ResidencyFixDiag(eligiblePromoted, s_uslrdStaticBudget,
		selectedCount, R_DarkWolfEscape1OverflowRelevantSelection(eligiblePromoted, s_uslrdStaticBudget));
	return selectedCount;
}
'''
# Apply to the unified function only: choose the occurrence immediately before wrapper by replacing last matching occurrence before wrapper.
pos=text.find('static int R_StaticPromoteSelectPersistentInfluence(const refdef_t *fd,')
assert pos>0
prefix=text[:pos]; suffix=text[pos:]
idx=prefix.rfind(needle)
assert idx>=0
prefix=prefix[:idx]+prefix[idx:].replace(needle,repl,1)
text=prefix+suffix

scene.write_text(text)
shutil.copy2(inc_src,inc_dst)
proof={
 'version':'ESCAPE1_DLIGHT_RESIDENCY_FIX_V1',
 'base_run':42217883095,
 'inherits':'ELECTRIC_PHYSICAL_OWNER_V1_SHADOW_LOCALVOL',
 'map_scope':'escape1',
 'activation':'only when accepted promoted > actual static budget',
 'policy':'FORCE_ON first; then visibility tier; then StaticPromote priority; then previous residency',
 'direct_radius_color_intensity_mutated':False,
 'max_dlights_changed':False,
 'other_maps_changed':False,
 'legacy_no_overflow_path_preserved':True,
 'scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest(),
 'inc_sha256':hashlib.sha256(inc_dst.read_bytes()).hexdigest()
}
(ev/'EDRF_V1_APPLY_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof,indent=2))
