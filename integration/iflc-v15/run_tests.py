#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,'integration/iflc-v14/run_tests.py',str(src),str(ev/'inherited')],check=True)
text=(src/'SP/code/rend2/tr_iflc_self.inc').read_text();cmd=(src/'SP/code/rend2/tr_iflc.inc').read_text()
checks={
 'manual_precedes_auto':'if(profile->selfSeedCount)return R_IFLC_BuildManualSelfFixture' in text,
 'manual_exact_seed_guard':'R_IFLC_ManualSeedSafe' in text,
 'architecture_plane_guard':'R_IFLC_SelfSamePlaneAsLargeArchitecture' in text and 'planes[64]' in text,
 'bounded_flood':'hi[0]-lo[0]>160' in text and 'hi[2]-lo[2]>224' in text,
 'real_mesh_contact_only':'R_IFLC_SelfContact(a,b)' in text,
 'flame_surface_protected':'R_IFLC_SelfIsFlameSurface' in text,
 'self_pick_reports_exact':'bound exact body surface' in cmd,
 'auto_semantics_unchanged':'0=AUTO baseline, 1=OFF own body, 2=ON original' in (src/'SP/code/rend2/tr_iflc.inc').read_text(),
}
assert all(checks.values()),checks
(ev/'IFLC15_STATIC_SAFETY.json').write_text(json.dumps(checks,indent=2)+'\n')
print('IFLC15_STATIC_SAFETY_PASS',len(checks))
