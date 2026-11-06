#!/usr/bin/env python3
from pathlib import Path
import json,re,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve()
ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
scene=(root/'tr_scene.c').read_text()
inc=(root/'tr_electric_owner_audit.inc').read_text()

checks={}
checks['marker']='DARKWOLF_ELECTRIC_PHYSICAL_OWNER_AUDIT_V1' in inc
checks['default_off']='ri.Cvar_Get("r_dwElectricOwnerAudit", "0", CVAR_ARCHIVE)' in inc
checks['hook_after_shadow_allocation']=scene.index('R_ElectricPhysicalOwnerAuditFrame(fd);') > scene.index('R_RenderDlightCubemaps(fd);')
checks['hook_before_firevol_shadow']=scene.index('R_ElectricPhysicalOwnerAuditFrame(fd);') < scene.index('R_RenderFireVolumetricSyntheticShadows(fd);')
checks['exact_current_merge']='EPOA_CURRENT_MERGE_RADIUS 16.0f' in inc
checks['shadow_semantics']='dl->iflcActive && !dl->iflcOptIn' in inc and 'DWSHADOW_SOURCE_PERSISTENT_PHYSICAL' in inc
checks['localvol_semantics']='dl->iflcActive ? dl->iflcBaseRadius : dl->radius' in inc
checks['synthetic_identity']='STATIC_PROMOTE_SYNTHETIC_ENTITY_BASE' in inc
checks['actual_shadow_slots']='tr.refdef.dlightShadowMask' in inc and 'tr.refdef.dlightShadowSlot' in inc
checks['localvol_active_radius']='r_volumetricLocalLampActiveRadius' in inc
checks['near_pair_telemetry']='EPOA_NEAR' in inc and 'nearSyntheticPairs' in inc
checks['registry_telemetry']='EPOA_REGISTRY' in inc and 'EPOA_REG map=' in inc
checks['no_scene_dlight_writes']=not re.search(r'(?:tr\.refdef\.dlights|backEndData->dlights)\[[^\]]+\]\.[A-Za-z_]\w*\s*=(?!=)',inc)
checks['no_shadow_state_writes']=not re.search(r'dlightShadow(?:Mask|Slot)(?:\[[^\]]+\])?\s*=(?!=)',inc)
checks['no_render_calls']=all(x not in inc for x in ('R_RenderView(', 'FBO_Blit(', 'RE_AddLightToScene(', 'R_AddDrawSurfCmd('))
checks['no_profile_writes']=all(x not in inc for x in ('FS_WriteFile','R_StaticPromoteSyntheticAdd','R_StaticPromoteUserOverrideSet','R_ELSS_Set'))

def equiv(a,b):
    if a['id']==b['id']: return False
    if sum((a['o'][k]-b['o'][k])**2 for k in range(3)) > 16**2: return False
    if abs(a['r']-b['r']) > 16: return False
    if sum((a['c'][k]-b['c'][k])**2 for k in range(3)) > 0.01: return False
    return True

def groups(xs):
    ids=[None]*len(xs)
    for s in range(len(xs)):
        if ids[s] is not None: continue
        q=[s]
        ids[s]=-2
        comp=[]
        while q:
            i=q.pop(0)
            comp.append(i)
            for j in range(len(xs)):
                if ids[j] is None and equiv(xs[i],xs[j]):
                    ids[j]=-2
                    q.append(j)
        can=min(xs[i]['id'] for i in comp)
        for i in comp: ids[i]=can
    return ids

mk=lambda i,x,r=200,c=(0.30,0.27,0.24):dict(id=i,o=(x,0,0),r=r,c=c)
checks['lab_close_cluster_one_group']=len(set(groups([mk(918,0),mk(1000001,8),mk(1000002,15)])))==1
checks['lab_17_units_split']=len(set(groups([mk(918,0),mk(1000001,17)])))==2
checks['lab_transitive_chain']=len(set(groups([mk(918,0),mk(1000001,15),mk(1000002,30)])))==1
checks['lab_radius_guard']=len(set(groups([mk(918,0),mk(1000001,8,r=217)])))==2
checks['lab_color_guard']=len(set(groups([mk(918,0),mk(1000001,8,c=(0.50,0.10,0.10))])))==2

assert all(checks.values()),{k:v for k,v in checks.items() if not v}
(ev/'EPOA_V1_STATIC_SAFETY.json').write_text(json.dumps(checks,indent=2)+'\n')
print('EPOA_V1_STATIC_SAFETY_PASS',len(checks))
