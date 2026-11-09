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
checks['marker']='DARKWOLF_ESCAPE1_DLIGHT_RESIDENCY_FIX_V1' in inc
checks['escape1_only']='Q_stricmp(tr.world->baseName, "escape1") != 0' in inc
checks['default_on_test']='ri.Cvar_Get("r_dwEscape1StableDlightResidency", "1", CVAR_ARCHIVE)' in inc
checks['overflow_only']='eligiblePromoted > staticBudget' in inc
checks['force_on_first']='R_StaticPromoteUSLRDPriority(light) != 0' in scene
checks['tier_outer']='for (tier = DWSP_TIER_SURFACE_VISIBLE; tier <= DWSP_TIER_LATENT' in scene
checks['no_max_change']='MAX_DLIGHTS' not in inc or 'maxDlights' not in inc
checks['no_direct_property_write']=not re.search(r'->(?:radius|color|candidate\.intensity)\s*=(?!=)',inc)
checks['no_profile_write']=all(x not in inc for x in ('FS_WriteFile','R_StaticPromoteUserOverrideSet','R_StaticPromoteSyntheticAdd','R_ELSS_Set'))
checks['diag_energy_zero']='directEnergyMutated=0' in inc

# Small pure selection laboratory mirroring the new overflow ordering.
SURF,SPHERE,PHYS,HELD,LAT=0,1,2,3,4
def select(rows,budget,fix=True,mapname='escape1'):
    if len(rows)<=budget or not fix or mapname!='escape1':
        out=[]
        for pr in range(7):
            for retained in (1,0):
                for r in rows:
                    if r['id'] in out or r['priority']!=pr or r['resident']!=retained: continue
                    out.append(r['id'])
                    if len(out)>=budget:return out
        return out
    out=[]
    # force-on first
    for retained in (1,0):
        for r in rows:
            if r['id'] in out or r['priority']!=0 or r['resident']!=retained: continue
            out.append(r['id'])
            if len(out)>=budget:return out
    for tier in range(5):
        for pr in range(1,7):
            for retained in (1,0):
                for r in rows:
                    if r['id'] in out or r['priority']!=pr or r['tier']!=tier or r['resident']!=retained: continue
                    out.append(r['id'])
                    if len(out)>=budget:return out
    return out

rows=[{'id':i,'priority':4,'tier':LAT,'resident':1} for i in range(1,30)]
rows.append({'id':740,'priority':4,'tier':SURF,'resident':0})
base=select(rows,23,fix=False)
fixed=select(rows,23,fix=True)
checks['lab_visible_boundary_protected']=740 not in base and 740 in fixed
# Budget change 24 -> 23 must keep the visible lamp.
checks['lab_visible_survives_budget_change']=740 in select(rows,24,fix=True) and 740 in select(rows,23,fix=True)
# FORCE ON latent remains absolute.
rows2=[{'id':900,'priority':0,'tier':LAT,'resident':0}] + rows
checks['lab_force_on_absolute']=900 in select(rows2,1,fix=True)
# Other maps preserve old ordering.
checks['lab_other_map_unchanged']=select(rows,23,fix=True,mapname='factory')==base
# No overflow preserves old ordering.
small=rows[:10]
checks['lab_no_overflow_unchanged']=select(small,23,fix=True)==select(small,23,fix=False)

assert all(checks.values()),{k:v for k,v in checks.items() if not v}
(ev/'EDRF_V1_STATIC_SAFETY.json').write_text(json.dumps(checks,indent=2)+'\n')
print('EDRF_V1_STATIC_SAFETY_PASS',len(checks))
