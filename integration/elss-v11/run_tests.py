#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
# Keep all accepted V1.0.1 / IFLC V1.5U tests.
subprocess.run([sys.executable,'integration/elss-v101/run_tests.py',str(src),str(ev/'v101')],check=True)
s=(src/'SP/code/rend2/tr_elss.inc').read_text()
frame=s[s.index('void R_ELSS_Frame'):s.index('void R_ELSS_CaptureShadowSlots')]
prep=s[s.index('static void R_ELSS_PrepareProfileFixture'):s.index('void R_ELSS_Frame')]
manual=s[s.index('static qboolean R_ELSS_BuildExact'):s.index('static void R_ELSS_PrepareProfileFixture')]
pick=s[s.index('void R_ELSS_SelfPick_f'):s.index('void R_ELSS_Set_f')]
checks={
 'v101_owner_order_preserved':frame.index('R_ELSS_UpsertOwner') < frame.index('R_ELSS_PrepareProfileFixture'),
 'v101_retry_preserved':prep.index('if(oi<0||s_elssOwners[oi].ambiguous)return;') < prep.index('s_elssFixtures[slot].built=qtrue;', prep.index('if(oi<0')),
 'profile_format_still_v1':'DW_ELSS 1' in s and 'DW_ELSS 2' not in s,
 'flood_first_exact_second':'if(R_ELSS_BuildFlood(p,o,out))return qtrue;' in manual and 'return R_ELSS_BuildExact(p,o,out);' in manual,
 'exact_uses_only_explicit_seeds':'out->surfaces[out->count++]=p->seeds[i]' in manual,
 'exact_reuses_architecture_safety':'R_ELSS_ManualSurfaceSafe(o,p->seeds[i])' in manual,
 'exact_group_bounded':'groupHi[0]-groupLo[0]>192' in manual and 'groupHi[2]-groupLo[2]>256' in manual,
 'protected_hit_never_bound_directly':all(x in pick for x in ('firstSurface=surface','!R_ELSS_ManualSurfaceSafe(o,surface)','R_ELSS_FindHousingNearCrosshair(o,&surface)')),
 'fallback_owner_local':'owner2>112.0f*112.0f' in s,
 'fallback_requires_owner_visibility':'R_IFLC_LineVisible(s_iflcViewOrigin,o->origin)' in s,
 'fallback_ambiguous_refused':'secondScore-bestScore<.08f' in s,
 'shadow_budget_unchanged':'r_dlightShadowMaxLights' not in s,
 'light_energy_unchanged':'.color' not in s and 'r_dlightIntensity' not in s,
 'commands_unchanged':all(x in s for x in ('R_ELSS_Select_f','R_ELSS_SelfPick_f','R_ELSS_Save_f','R_ELSS_Reload_f')),
 'no_map_specific_production':all(x not in s.lower() for x in ('church','boss1','escape1','crypt1','fixture:107','10810')),
}
assert all(checks.values()),checks
(ev/'ELSS_V11_STATIC.json').write_text(json.dumps(checks,indent=2)+'\n')
print('ELSS_V11_STATIC_PASS',len(checks))
