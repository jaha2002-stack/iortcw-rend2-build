#!/usr/bin/env python3
from pathlib import Path
import json,re,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve()
ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
scene=(root/'tr_scene.c').read_text()
inc=(root/'tr_escape1_dlight_residency_fix.inc').read_text()
checks={}
checks['marker']='DARKWOLF_ESCAPE1_DLIGHT_RESIDENCY_FIX_V1_1' in inc
checks['escape1_only']='Q_stricmp(tr.world->baseName, "escape1") != 0' in inc
checks['default_on_test']='ri.Cvar_Get("r_dwEscape1StableDlightResidency", "1", CVAR_ARCHIVE)' in inc
checks['native_reserve_9']='EDRF_ESCAPE1_DEFAULT_NATIVE_RESERVE 9' in inc
checks['stable_budget']='MAX_DLIGHTS - reserve' in inc
checks['coherence_260']='EDRF_COHERENCE_RADIUS 260.0f' in inc
checks['camera_distance_zero']='cameraDistanceUsed=0' in inc
checks['force_on_first']='R_StaticPromoteUSLRDPriority(light) != 0' in scene
checks['coherence_order']='R_DarkWolfEscape1FixtureCoherenceScore(light) != coherence' in scene
checks['no_direct_property_write']=not re.search(r'->(?:radius|color|candidate\.intensity)\s*=(?!=)',inc)
checks['no_profile_write']=all(x not in inc for x in ('FS_WriteFile','R_StaticPromoteUserOverrideSet','R_StaticPromoteSyntheticAdd','R_ELSS_Set'))
checks['diag_energy_zero']='directEnergyMutated=0' in inc

# Pure selection model for the V1.1 policy.
def stable_budget(eligible,actual,mapname='escape1',enabled=True,reserve=9):
    if not enabled or mapname!='escape1': return actual
    cap=32-reserve
    if eligible<=cap: return actual
    return min(actual,cap)

def old_select(rows,budget):
    out=[]
    for pr in range(7):
        for retained in (1,0):
            for r in rows:
                if r['id'] in out or r['priority']!=pr or r['resident']!=retained: continue
                out.append(r['id'])
                if len(out)>=budget:return out
    return out

def fixed_select(rows,actual,mapname='escape1',enabled=True):
    budget=stable_budget(len(rows),actual,mapname,enabled)
    if not enabled or mapname!='escape1' or len(rows)<=budget:
        return old_select(rows,actual)
    out=[]
    for retained in (1,0):
        for r in rows:
            if r['id'] in out or r['priority']!=0 or r['resident']!=retained: continue
            out.append(r['id'])
            if len(out)>=budget:return out
    for pr in range(1,7):
        for coh in range(31,-1,-1):
            for retained in (1,0):
                for r in rows:
                    if r['id'] in out or r['priority']!=pr or r['coh']!=coh or r['resident']!=retained: continue
                    out.append(r['id'])
                    if len(out)>=budget:return out
    return out

# 24 equally-prioritized residents; fixture 740 belongs to a coherent lamp group.
rows=[{'id':i,'priority':4,'coh':0,'resident':1} for i in range(100,123)]
rows.append({'id':740,'priority':4,'coh':2,'resident':1})
# Add six already-evicted accepted lights so total accepted is the proven 30.
rows += [
 {'id':745,'priority':4,'coh':3,'resident':0},
 {'id':1279,'priority':4,'coh':1,'resident':0},
 {'id':352,'priority':5,'coh':1,'resident':0},
 {'id':355,'priority':5,'coh':1,'resident':0},
 {'id':848,'priority':5,'coh':1,'resident':0},
 {'id':1285,'priority':5,'coh':1,'resident':0},
]
off24=old_select(rows,24)
off23=old_select(rows,23)
on24=fixed_select(rows,24)
on23=fixed_select(rows,23)
checks['lab_old_boundary_churn']=740 in off24 and 740 not in off23
checks['lab_stable_budget_23_at_headroom24']=stable_budget(30,24)==23
checks['lab_stable_budget_23_at_headroom23']=stable_budget(30,23)==23
checks['lab_fix_same_set_24_to_23']=on24==on23
checks['lab_guard_fixture_preserved']=740 in on24 and 740 in on23
checks['lab_coherent_peer_can_enter']=745 in on23
# FORCE ON remains absolute even when isolated.
rows2=[{'id':900,'priority':0,'coh':0,'resident':0}] + rows
checks['lab_force_on_absolute']=900 in fixed_select(rows2,23)
# Other maps and feature OFF preserve legacy ordering.
checks['lab_other_map_unchanged']=fixed_select(rows,23,mapname='factory')==old_select(rows,23)
checks['lab_feature_off_unchanged']=fixed_select(rows,23,enabled=False)==old_select(rows,23)
# No overflow / accepted <= reserve budget preserves old path.
small=rows[:20]
checks['lab_no_overflow_unchanged']=fixed_select(small,24)==old_select(small,24)

assert all(checks.values()),{k:v for k,v in checks.items() if not v}
(ev/'EDRF_V1_STATIC_SAFETY.json').write_text(json.dumps(checks,indent=2)+'\n')
print('EDRF_V1_STATIC_SAFETY_PASS',len(checks))
