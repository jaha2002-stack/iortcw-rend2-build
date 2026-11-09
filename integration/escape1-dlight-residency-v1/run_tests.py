#!/usr/bin/env python3
from pathlib import Path
import json,re,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve()
ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
scene=(root/'tr_scene.c').read_text()
inc=(root/'tr_escape1_dlight_residency_audit.inc').read_text()

checks={}
checks['marker']='DARKWOLF_ESCAPE1_DLIGHT_RESIDENCY_AUDIT_V1' in inc
checks['default_off']='ri.Cvar_Get("r_dwEscape1DlightResidencyAudit", "0", CVAR_ARCHIVE)' in inc
checks['escape1_only']='Q_stricmp(tr.world->baseName, "escape1") != 0' in inc
checks['summary']='EDRA_SUMMARY' in inc and 'sceneNative=%d' in inc and 'headroom=%d' in inc and 'budgetEvictions=%d' in inc
checks['eviction']='EDRA_EVICT' not in inc and '"EVICT"' in inc
checks['native_change']='EDRA_NATIVE_CHANGE' in inc and 'EDRA_NATIVE' in inc
checks['guard_fixture_ids']='{ 740, 741, 742, 743, 744, 745 }' in inc
checks['hook_after_uslrd']='R_StaticPromoteUSLRDDiagFrame();\n\tR_DarkWolfEscape1DlightResidencyAuditFrame(fd);' in scene
checks['no_render_calls']=all(x not in inc for x in ('R_RenderView(', 'FBO_Blit(', 'RE_AddLightToScene(', 'R_AddDrawSurfCmd('))
checks['no_profile_writes']=all(x not in inc for x in ('FS_WriteFile','R_StaticPromoteUserOverrideSet','R_StaticPromoteSyntheticAdd','R_ELSS_Set'))
checks['no_direct_mutation']=not re.search(r'(?:dl|light)->(?:radius|color|unifiedResident|unifiedRoute|unifiedBudgetEvicted|unifiedSelectedSlot|unifiedActualDlightIndex)\s*=(?!=)',inc)
checks['no_dlight_array_write']=not re.search(r'backEndData->dlights\[[^\]]+\]\.[A-Za-z_]\w*\s*=(?!=)',inc)
checks['reads_budget_fields']=all(x in inc for x in ('s_uslrdSceneNativeCount','s_uslrdHeadroom','s_uslrdStaticBudget','s_uslrdBudgetEvictions','s_uslrdSubmittedPromoted'))
assert all(checks.values()),{k:v for k,v in checks.items() if not v}
(ev/'EDRA_V1_STATIC_SAFETY.json').write_text(json.dumps(checks,indent=2)+'\n')
print('EDRA_V1_STATIC_SAFETY_PASS',len(checks))
