#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve()
ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
scene=root/'tr_scene.c'
inc_src=Path(__file__).with_name('tr_escape1_physical_dlight_owner_v12.inc')
inc_dst=root/'tr_escape1_physical_dlight_owner_v12.inc'
text=scene.read_text()

# V1.2 is applied directly to the production USLRD selection path.  The withdrawn
# Escape1 Residency V1.1 patch must NOT already be present.
assert 'DARKWOLF_ESCAPE1_DLIGHT_RESIDENCY_FIX_V1_1' not in text
assert 'DARKWOLF_ESCAPE1_PHYSICAL_DLIGHT_OWNER_RESIDENCY_V12' not in text

include_anchor='// DARKWOLF_USLRD_ALWAYS_ON_DIRECT_SHADOW_CAPTURE_FIX_V1\n'
assert include_anchor in text
text=text.replace(include_anchor,
    '#include "tr_escape1_physical_dlight_owner_v12.inc"\n\n'+include_anchor,1)

decl='int selectedCount = 0, classifierAccepted = 0, classifierRejected = 0;\n\tint visibleCount = 0, heldCount = 0, eligiblePromoted = 0;'
assert decl in text
text=text.replace(decl,
'''int selectedCount = 0, classifierAccepted = 0, classifierRejected = 0;
	int visibleCount = 0, heldCount = 0, eligiblePromoted = 0;
	int acceptedNativeRoutes = 0, externalNativeCount = 0;
	int physicalOwnerBudget = 0, promotedBudget = 0;
	qboolean edr12OwnerFirst = qfalse;''',1)

native_mark='''			light->unifiedNativeRuntimePresent = qtrue;
			light->unifiedNativeSceneIndex = nativeIndex;'''
assert native_mark in text
text=text.replace(native_mark,
'''			light->unifiedNativeRuntimePresent = qtrue;
			acceptedNativeRoutes++;
			light->unifiedNativeSceneIndex = nativeIndex;''',1)

old='''	// DARKWOLF_USLRD_ALWAYS_ON_DIRECT_SHADOW_CAPTURE_FIX_V1
	// If all-accepted delivery fits the actual front-end headroom, PVS/tier never turns a lamp off.
	// When the accepted set exceeds headroom, deterministic priority + previous ownership decides
	// which fixtures remain delivered; visibility still does not alter base Direct energy.
	if (allAcceptedDelivery)
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
new='''	// DARKWOLF_USLRD_ALWAYS_ON_DIRECT_SHADOW_CAPTURE_FIX_V1
	// Production normally delivers every classifier-accepted fixture while real
	// MAX_DLIGHTS headroom exists.
	//
	// DARKWOLF_ESCAPE1_PHYSICAL_DLIGHT_OWNER_RESIDENCY_V12:
	// Under Escape1 overflow, capacity is owned by PHYSICAL fixtures rather than by
	// the promoted/native route used in the current frame.  Native-route owners
	// subtract from the promoted budget, so a route switch cannot open a temporary
	// slot for a neighbouring lamp and later evict it again.
	externalNativeCount = R_EDR12_ExternalNativeCount(
		s_uslrdSceneNativeCount, acceptedNativeRoutes);
	physicalOwnerBudget = R_EDR12_PhysicalOwnerBudget(
		requestedMaxLights, externalNativeCount);
	edr12OwnerFirst = (allAcceptedDelivery && R_EDR12_Enabled() &&
		classifierAccepted > physicalOwnerBudget) ? qtrue : qfalse;
	promotedBudget = edr12OwnerFirst
		? R_EDR12_PromotedBudget(physicalOwnerBudget,
			acceptedNativeRoutes, s_uslrdStaticBudget)
		: s_uslrdStaticBudget;

	if (allAcceptedDelivery && !edr12OwnerFirst)
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
		// Owner-first Escape1 overflow selection.
		//
		// 1) Explicit FORCE ON remains absolute.
		priority = 0;
		for (retainedPass = 0; retainedPass < 2 && selectedCount < promotedBudget; ++retainedPass)
		{
			for (i = 0; i < s_staticPromotePersistentCount && selectedCount < promotedBudget; ++i)
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

		// 2) Every currently relevant owner is preferred before LATENT owners.
		// Existing 8s GRACE_HELD provides hysteresis while moving between rooms.
		for (tier = DWSP_TIER_SURFACE_VISIBLE; tier <= DWSP_TIER_GRACE_HELD &&
			selectedCount < promotedBudget; ++tier)
		{
			for (priority = 1; priority <= 6 && selectedCount < promotedBudget; ++priority)
			{
				for (retainedPass = 0; retainedPass < 2 && selectedCount < promotedBudget; ++retainedPass)
				{
					for (i = 0; i < s_staticPromotePersistentCount && selectedCount < promotedBudget; ++i)
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

		// 3) A native-capable owner is preferred over an arbitrary LATENT owner.
		// This makes fixtures such as authored/promoted aliases route-independent:
		// when their native DLight appears/disappears, the physical owner remains
		// part of the same stable set instead of donating its slot to another lamp.
		for (priority = 1; priority <= 6 && selectedCount < promotedBudget; ++priority)
		{
			for (retainedPass = 0; retainedPass < 2 && selectedCount < promotedBudget; ++retainedPass)
			{
				for (i = 0; i < s_staticPromotePersistentCount && selectedCount < promotedBudget; ++i)
				{
					staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
					if (selectedFlags[i] || !light->unifiedClassAccepted || light->unifiedNativeRuntimePresent)
						continue;
					if (light->unifiedVisibilityTier != DWSP_TIER_LATENT)
						continue;
					if (!R_EDR12_NativeCapableOwner(light))
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

		// 4) Fill remaining owner capacity with ordinary LATENT fixtures.
		for (priority = 1; priority <= 6 && selectedCount < promotedBudget; ++priority)
		{
			for (retainedPass = 0; retainedPass < 2 && selectedCount < promotedBudget; ++retainedPass)
			{
				for (i = 0; i < s_staticPromotePersistentCount && selectedCount < promotedBudget; ++i)
				{
					staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
					if (selectedFlags[i] || !light->unifiedClassAccepted || light->unifiedNativeRuntimePresent)
						continue;
					if (light->unifiedVisibilityTier != DWSP_TIER_LATENT)
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
assert text.count(old)==1, text.count(old)
text=text.replace(old,new,1)

needle='''	if (classifierAcceptedOut) *classifierAcceptedOut = classifierAccepted;
	if (classifierRejectedOut) *classifierRejectedOut = classifierRejected;
	return selectedCount;
}
'''
repl='''	if (classifierAcceptedOut) *classifierAcceptedOut = classifierAccepted;
	if (classifierRejectedOut) *classifierRejectedOut = classifierRejected;
	R_EDR12_Diag(classifierAccepted, acceptedNativeRoutes, eligiblePromoted,
		externalNativeCount, physicalOwnerBudget, promotedBudget,
		selectedCount, s_uslrdBudgetEvictions);
	return selectedCount;
}
'''
assert text.count(needle)>=1
# Only the unified function precedes the wrapper. Replace the last matching return block
# before R_StaticPromoteSelectPersistentInfluence wrapper.
pos=text.find('static int R_StaticPromoteSelectPersistentInfluence(const refdef_t *fd,')
assert pos>0
prefix=text[:pos]
suffix=text[pos:]
idx=prefix.rfind(needle)
assert idx>=0
prefix=prefix[:idx]+prefix[idx:].replace(needle,repl,1)
text=prefix+suffix

scene.write_text(text)
shutil.copy2(inc_src,inc_dst)

proof={
  'version':'ESCAPE1_PHYSICAL_DLIGHT_OWNER_RESIDENCY_V12',
  'base_run':42217883095,
  'map_scope':'escape1',
  'external_native_reserve':9,
  'physical_owner_budget_when_external_native_le_9':23,
  'owner_identity_route_independent':True,
  'accepted_native_routes_subtract_from_promoted_budget':True,
  'selection_order':'FORCE_ON; SURFACE/PVS/PHYSICAL/GRACE by priority+retention; native-capable LATENT; ordinary LATENT',
  'direct_radius_color_intensity_mutated':False,
  'max_dlights_changed':False,
  'camera_distance_used':False,
  'other_maps_changed':False,
  'withdraws_escape1_residency_v11':True,
  'inherits_electric_physical_owner_v1':True,
  'scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest(),
  'inc_sha256':hashlib.sha256(inc_dst.read_bytes()).hexdigest(),
}
(ev/'EDR12_APPLY_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof,indent=2))
