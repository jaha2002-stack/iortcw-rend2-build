#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys,re
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,'integration/iflc-v15/run_tests.py',str(src),str(ev/'inherited_v15')],check=True)
selfsrc=(src/'SP/code/rend2/tr_iflc_self.inc').read_text();cmd=(src/'SP/code/rend2/tr_iflc.inc').read_text()
manual=selfsrc[selfsrc.index('static qboolean R_IFLC_BuildManualSelfFixture'):selfsrc.index('/* Explicit profile is passed')]
selfpick=cmd[cmd.index('void R_IFLC_SelfPick_f'):cmd.index('void R_IFLC_Reset_f')]
checks={
 'manual_no_flame_bounds':'R_IFLC_SelfBounds' not in manual,
 'manual_owner_origin':'VectorCopy(s_iflcOwners[ownerIndex].origin,anchor)' in manual,
 'manual_rejects_ambiguous':'s_iflcOwners[ownerIndex].ambiguous' in manual,
 'manual_no_owner_kind_gate':all(x not in manual for x in ('IFLC_NATIVE','IFLC_PROMOTED','IFLC_SURFACE')),
 'selfpick_no_flame_bounds':'R_IFLC_SelfBounds' not in selfpick,
 'auto_still_flame_bounds':'if(!R_IFLC_SelfBounds(ownerIndex,flameLo,flameHi,anchor)) return qfalse;' in selfsrc,
 'all_flame_shaders_protected':'R_IFLC_FlameShader(s->shader)' in selfsrc,
 'architecture_guard':'R_IFLC_SelfSamePlaneAsLargeArchitecture' in selfsrc,
 'contact_flood':'R_IFLC_SelfContact(a,b)' in manual,
 'bounded_group':'hi[0]-lo[0]>160' in manual and 'hi[2]-lo[2]>224' in manual,
 'route_reporting':'R_IFLC_Route(&s_iflcOwners[s_iflcSelected])' in selfpick,
}
assert all(checks.values()),checks
(ev/'IFLC15U_STATIC_SAFETY.json').write_text(json.dumps(checks,indent=2)+'\n')
print('IFLC15U_STATIC_SAFETY_PASS',len(checks))
