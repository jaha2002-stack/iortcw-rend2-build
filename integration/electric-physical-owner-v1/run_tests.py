#!/usr/bin/env python3
from pathlib import Path
import json,re,sys,math

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve()
ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
local=(root/'tr_local.h').read_text()
scene=(root/'tr_scene.c').read_text()
main=(root/'tr_main.c').read_text()
backend=(root/'tr_backend.c').read_text()
inc=(root/'tr_electric_physical_owner.inc').read_text()

checks={}
checks['owner_field']='int physicalElectricOwnerId;' in local
checks['owner_initialized']='dl->physicalElectricOwnerId = -1;' in scene
checks['owner_called_after_begin_scene']=scene.index('R_DarkWolfAssignPhysicalElectricOwnerIds();') > scene.index('RE_BeginScene(fd);')
checks['default_enabled']='ri.Cvar_Get("r_dwElectricPhysicalOwner", "1", CVAR_ARCHIVE)' in inc
checks['diag_default_off']='ri.Cvar_Get("r_dwElectricPhysicalOwnerDiag", "0", CVAR_ARCHIVE)' in inc
checks['inherit_distance_48']='#define DW_EPO_V1_INHERIT_MAX_DIST 48.0f' in inc
checks['ambiguity_margin_16']='#define DW_EPO_V1_AMBIGUITY_MARGIN 16.0f' in inc
checks['radius_guard_16']='#define DW_EPO_V1_RADIUS_DELTA 16.0f' in inc
checks['color_guard']='DW_EPO_V1_COLOR_DELTA_SQ 0.01f' in inc
checks['real_owner_uses_electric_fixture']='fixture = R_ElectricFixtureForLight(dl);' in inc
checks['synthetic_only_inherits']='R_DarkWolfElectricOwnerIsSynthetic(syn)' in inc
checks['shadow_owner_equivalence']='a->physicalElectricOwnerId == b->physicalElectricOwnerId' in main
checks['localvol_owner_equivalence']='a->physicalElectricOwnerId == b->physicalElectricOwnerId' in backend
checks['legacy_shadow_fallback']='s_rStaticPromotePhysicalGroupMergeRadius->value' in main
checks['legacy_localvol_fallback']='s_rStaticPromotePhysicalGroupMergeRadius' in backend
checks['elss_capture_uses_owner']='fixture = tr.refdef.dlights[index].physicalElectricOwnerId > 0' in main
checks['iflc_source_untouched']='tr_iflc.inc' in json.loads((ev/'EPO_V1_APPLY_PROOF.json').read_text())['protected_unchanged']
checks['elss_source_untouched']='tr_elss.inc' in json.loads((ev/'EPO_V1_APPLY_PROOF.json').read_text())['protected_unchanged']
checks['direct_mutation_absent']=all(x not in inc for x in (
    '->radius =','->color[0] =','->color[1] =','->color[2] =',
    'VectorCopy(syn->origin','VectorCopy(real->origin','RE_AddLightToScene(',
    'R_StaticPromoteUSLRDTagPromotedDlight('))
checks['residency_mutation_absent']=all(x not in inc for x in (
    'unifiedResident','unifiedSelectedSlot','unifiedActualDlightIndex','r_staticPromoteMaxLights'))
checks['shadow_budget_untouched']='r_dlightShadowMaxLights' not in inc
checks['localvol_settings_untouched']=all(x not in inc for x in (
    'r_volumetricLocalStrength','r_volumetricLocalDensity','r_volumetricLocalSamples'))
checks['read_only_owner_metadata']='directMutated=0' in inc

# Pure laboratory model of the inheritance policy.
def compatible(a,b):
    return abs(a['radius']-b['radius'])<=16 and sum((a['color'][k]-b['color'][k])**2 for k in range(3))<=0.01

def inherit(syn,reals,self_fixture=0):
    best_owner=-1; second_owner=-1
    best2=1e30; second2=1e30
    for real in reals:
        owner=real['owner']
        if owner<=0: continue
        if self_fixture>0 and owner!=self_fixture: continue
        if not compatible(syn,real): continue
        d2=sum((syn['origin'][k]-real['origin'][k])**2 for k in range(3))
        if d2>48**2: continue
        if owner==best_owner:
            best2=min(best2,d2); continue
        if d2<best2:
            second2,second_owner=best2,best_owner
            best2,best_owner=d2,owner
        elif owner!=best_owner and d2<second2:
            second2,second_owner=d2,owner
    if best_owner<=0:return -1
    if self_fixture>0 and self_fixture!=best_owner:return -1
    if second_owner>0 and math.sqrt(second2)<math.sqrt(best2)+16:return -1
    return best_owner

base={'origin':(0,0,0),'radius':192,'color':(1.0,.8,.6),'owner':7}
checks['lab_plus8_inherits']=inherit({'origin':(8,0,0),'radius':192,'color':(1.0,.8,.6)},[base])==7
checks['lab_plus32_inherits']=inherit({'origin':(32,0,0),'radius':192,'color':(1.0,.8,.6)},[base])==7
checks['lab_plus49_rejected']=inherit({'origin':(49,0,0),'radius':192,'color':(1.0,.8,.6)},[base])==-1
checks['lab_radius_mismatch_rejected']=inherit({'origin':(32,0,0),'radius':220,'color':(1.0,.8,.6)},[base])==-1
checks['lab_color_mismatch_rejected']=inherit({'origin':(32,0,0),'radius':192,'color':(.7,.4,.2)},[base])==-1
checks['lab_ambiguous_two_owners_rejected']=inherit(
    {'origin':(20,0,0),'radius':192,'color':(1.0,.8,.6)},
    [base,{'origin':(30,0,0),'radius':192,'color':(1.0,.8,.6),'owner':8}])==-1
checks['lab_clear_nearest_owner_accepted']=inherit(
    {'origin':(8,0,0),'radius':192,'color':(1.0,.8,.6)},
    [base,{'origin':(44,0,0),'radius':192,'color':(1.0,.8,.6),'owner':8}])==7

bad={k:v for k,v in checks.items() if not v}
assert not bad,bad
(ev/'EPO_V1_STATIC_SAFETY.json').write_text(json.dumps(checks,indent=2)+'\n')
print('EPO_V1_STATIC_SAFETY_PASS',len(checks))
