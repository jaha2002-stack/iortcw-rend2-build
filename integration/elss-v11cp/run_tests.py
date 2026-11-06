#!/usr/bin/env python3
from pathlib import Path
import json,sys
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
elss=(root/'tr_elss.inc').read_text()
electric=(root/'tr_electric_fixture.inc').read_text()
local=(root/'tr_local.h').read_text()
backend=(root/'tr_backend.c').read_text()
init=(root/'tr_init.c').read_text()
frame=elss[elss.index('void R_ELSS_Frame'):elss.index('void R_ELSS_CaptureShadowSlots')]
prep=elss[elss.index('static void R_ELSS_PrepareProfileFixture'):elss.index('void R_ELSS_Frame')]
checks={
 'component_mask':'R_ELSS_ComponentMask' in elss,
 'hit_triangle':'R_ELSS_HitTriangle' in elss and 'R_IFLC_RayTriangle' in elss,
 'edge_connectivity':'R_ELSS_TriAdjacent' in elss,
 'compact_guard':'largest>256' in elss and 'second>160' in elss and 'largest>192&&second>80' in elss,
 'owner_distance_guard':'R_IFLC_SelfBoundsDistanceSquared(o->origin,lo,hi)>224.0f*224.0f' in elss,
 'profile_v1_v2_read':'version!=1&&version!=2' in elss,
 'profile_v2_write':'DW_ELSS 2' in elss,
 'triangle_seed':'seedTris' in elss,
 'triangle_trim_api':'R_ELSS_ManualOmitMask' in elss and 'R_ELSS_ManualOmitMask' in local,
 'legacy_whole_surface_preserved':'R_ELSS_SuppressManualDrawSurf' in elss and 'R_ELSS_SuppressManualDrawSurf' in electric,
 'trim_selected_triangles':'RB_SurfaceElectricTrim((srfBspSurface_t *)ds->surface,omit,triangleCount)' in electric,
 'trim_bound_512':'ELSS_MAX_TRIM_TRIANGLES 512' in elss,
 'v101_owner_first':frame.index('R_ELSS_UpsertOwner') < frame.index('R_ELSS_PrepareProfileFixture'),
 'v101_retry_if_owner_absent':prep.index('if(oi<0||s_elssOwners[oi].ambiguous)return;') < prep.index('s_elssFixtures[slot].built=qtrue;',prep.index('if(oi<0')),
 'shadow_budget_untouched':'r_dlightShadowMaxLights' not in elss,
 'light_energy_untouched':'.color' not in elss and 'r_dlightIntensity' not in elss,
 'profile_scope':'electricshadows/%s.elss' in elss,
 'no_map_specific_production':all(x not in elss.lower() for x in ('church','boss1','escape1','crypt1','10810','fixture:107')),
 'firevol_clean_preserved':'FIREVOL_CLEAN_PRODUCTION' in backend,
 'crypt1_reanchor_preserved':'DARKWOLF_FIREVOL_CRYPT1_SLOT6_REANCHOR_PRODUCTION' in backend,
 'diagnostics_default_off':'r_dwFireVolContinuityDiag' in init and 'r_dwFireVolFixtureDiag' in init,
}
assert all(checks.values()),checks
(ev/'ELSS_V11_STATIC_SAFETY.json').write_text(json.dumps(checks,indent=2)+'\n')
print('ELSS_V11_STATIC_SAFETY_PASS',len(checks))
