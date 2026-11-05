#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
# Keep all inherited ELSS V1 / IFLC V1.5U safety checks.
subprocess.run([sys.executable,'integration/elss-v1/run_tests.py',str(src),str(ev/'inherited')],check=True)
s=(src/'SP/code/rend2/tr_elss.inc').read_text()
frame=s[s.index('void R_ELSS_Frame'):s.index('void R_ELSS_CaptureShadowSlots')]
prep=s[s.index('static void R_ELSS_PrepareProfileFixture'):s.index('void R_ELSS_Frame')]
checks={
 'owners_upsert_before_profile_prepare':frame.index('R_ELSS_UpsertOwner') < frame.index('R_ELSS_PrepareProfileFixture'),
 'missing_owner_does_not_mark_built':prep.index('if(oi<0||s_elssOwners[oi].ambiguous)return;') < prep.index('s_elssFixtures[slot].built=qtrue;', prep.index('if(oi<0')),
 'profile_format_unchanged':'DW_ELSS 1' in s and 'DW_ELSS 2' not in s,
 'commands_unchanged':all(x in s for x in ('R_ELSS_Select_f','R_ELSS_SelfPick_f','R_ELSS_Save_f','R_ELSS_Reload_f')),
 'shadow_budget_unchanged':'r_dlightShadowMaxLights' not in s,
}
assert all(checks.values()),checks
(ev/'ELSS_V101_STATIC.json').write_text(json.dumps(checks,indent=2)+'\n')
print('ELSS_V101_STATIC_PASS',len(checks))
