#!/usr/bin/env python3
from pathlib import Path
import json,re,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve()
ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
scene=(root/'tr_scene.c').read_text()
inc=(root/'tr_escape1_physical_dlight_owner_v12.inc').read_text()

checks={}
checks['marker']='DARKWOLF_ESCAPE1_PHYSICAL_DLIGHT_OWNER_RESIDENCY_V12' in inc
checks['escape1_only']='Q_stricmp(tr.world->baseName, "escape1") != 0' in inc
checks['default_enabled_test']='r_dwEscape1PhysicalDlightOwnerResidency' in inc and '"1", CVAR_ARCHIVE' in inc
checks['external_reserve_9']='EDR12_DEFAULT_EXTERNAL_NATIVE_RESERVE 9' in inc
checks['external_native_subtraction']='sceneNativeCount - acceptedNativeRoutes' in inc
checks['owner_budget']='MAX_DLIGHTS - hardReserve' in inc
checks['promoted_budget_subtracts_native_routes']='physicalOwnerBudget - acceptedNativeRoutes' in inc
checks['owner_first_marker']='ownerFirst=1 routeIndependent=1' in inc
checks['native_capable_stability']='R_EDR12_NativeCapableOwner' in inc
checks['relevance_before_latent']='DWSP_TIER_SURFACE_VISIBLE' in scene and 'DWSP_TIER_GRACE_HELD' in scene
checks['no_direct_property_write']=not re.search(
    r'->(?:radius|color|candidate\.intensity)\s*=(?!=)',inc)
checks['no_profile_write']=all(x not in inc for x in (
    'FS_WriteFile','R_StaticPromoteUserOverrideSet',
    'R_StaticPromoteSyntheticAdd','R_ELSS_Set'))
checks['no_max_dlights_change']='#define MAX_DLIGHTS' not in inc
checks['camera_distance_unused']='cameraDistance' not in inc
checks['v11_not_present']='DARKWOLF_ESCAPE1_DLIGHT_RESIDENCY_FIX_V1_1' not in scene

# Pure model mirroring V1.2.  IDs 851 and 298 are the two accepted fixtures
# observed in the user's real Escape1 log changing native/promoted route.
SURF,SPHERE,PHYS,GRACE,LAT=0,1,2,3,4

def owner_budget(external_native,reserve=9,requested=32):
    return min(requested,32-max(reserve,external_native))

def promoted_budget(owners,native_routes,actual_headroom):
    return min(max(0,owners-native_routes),actual_headroom)

def rank(rows,current_native):
    # Native-routed owners are already physically delivered and do not need a promoted slot.
    candidates=[r for r in rows if r['id'] not in current_native]
    out=[]
    # FORCE ON
    for retained in (1,0):
        for r in candidates:
            if r['id'] in out or r['priority']!=0 or r['resident']!=retained: continue
            out.append(r['id'])
    # Relevant tiers
    for tier in (SURF,SPHERE,PHYS,GRACE):
        for pr in range(1,7):
            for retained in (1,0):
                for r in candidates:
                    if r['id'] in out or r['tier']!=tier or r['priority']!=pr or r['resident']!=retained: continue
                    out.append(r['id'])
    # Native-capable latent
    for pr in range(1,7):
        for retained in (1,0):
            for r in candidates:
                if r['id'] in out or r['tier']!=LAT or not r['nativeCapable'] or r['priority']!=pr or r['resident']!=retained: continue
                out.append(r['id'])
    # Remaining latent
    for pr in range(1,7):
        for retained in (1,0):
            for r in candidates:
                if r['id'] in out or r['tier']!=LAT or r['priority']!=pr or r['resident']!=retained: continue
                out.append(r['id'])
    return out

# Build 30 accepted owners.  All six guard-room lamps are SURFACE_VISIBLE.
guard=[740,741,742,743,744,745]
rows=[]
for n,f in enumerate(guard):
    rows.append({'id':f,'priority':4,'tier':SURF,'resident':1,'nativeCapable':False})
rows += [
 {'id':1279,'priority':4,'tier':SURF,'resident':0,'nativeCapable':False},
 {'id':736,'priority':4,'tier':SPHERE,'resident':1,'nativeCapable':False},
 {'id':735,'priority':4,'tier':SPHERE,'resident':1,'nativeCapable':False},
 {'id':737,'priority':4,'tier':SPHERE,'resident':1,'nativeCapable':False},
 {'id':835,'priority':4,'tier':PHYS,'resident':1,'nativeCapable':False},
 {'id':782,'priority':4,'tier':GRACE,'resident':1,'nativeCapable':False},
 {'id':851,'priority':4,'tier':LAT,'resident':1,'nativeCapable':True},
 {'id':298,'priority':4,'tier':LAT,'resident':1,'nativeCapable':True},
]
nextid=2000
while len(rows)<30:
    rows.append({'id':nextid,'priority':5 if len(rows)%2 else 4,'tier':LAT,
                 'resident':1 if len(rows)<23 else 0,'nativeCapable':False})
    nextid+=1

budget=owner_budget(9)
checks['model_owner_budget_23']=budget==23

owner_sets=[]
for native_routes in (set(),{298},{298,851}):
    scene_native=9+len(native_routes)
    headroom=32-scene_native
    pbudget=promoted_budget(budget,len(native_routes),headroom)
    ordered=rank(rows,native_routes)
    promoted=set(ordered[:pbudget])
    physical=set(native_routes)|promoted
    owner_sets.append(physical)
    checks[f'model_physical_count_routes_{len(native_routes)}']=len(physical)==23
    checks[f'model_promoted_budget_routes_{len(native_routes)}']=pbudget==23-len(native_routes)
    checks[f'model_guard_all_on_routes_{len(native_routes)}']=all(x in physical for x in guard)

checks['model_route_independent_owner_set']=owner_sets[0]==owner_sets[1]==owner_sets[2]
checks['model_fixture745_never_donates_slot']=all(745 in s for s in owner_sets)
checks['model_native_capable_851_298_stable']=all(851 in s and 298 in s for s in owner_sets)

# Hard safety when external-native occupancy exceeds the configured reserve.
checks['model_external_native_10_shrinks_safely']=owner_budget(10)==22
checks['model_external_native_11_shrinks_safely']=owner_budget(11)==21

assert all(checks.values()), {k:v for k,v in checks.items() if not v}
(ev/'EDR12_STATIC_SAFETY.json').write_text(json.dumps(checks,indent=2)+'\n')
print('EDR12_STATIC_SAFETY_PASS',len(checks))
