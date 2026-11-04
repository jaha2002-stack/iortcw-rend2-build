#!/usr/bin/env python3
"""Apply the inspectable V1.4 candidate to the exact V1.3 source artifact.
The zlib file is a lossless transport of unified source diff, not an executable.
Its decoded UTF-8 patch is exported with the source and verification artifacts.
"""
from pathlib import Path
import hashlib,json,subprocess,sys,zlib
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
kit=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
before={p.relative_to(src).as_posix():p.read_bytes() for p in (src/'SP/code').rglob('*') if p.is_file()}
expected=json.loads((ev/'IFLC14_BASE_SHA256.json').read_text())
assert {p:sha(b) for p,b in before.items()}==expected and len(before)==1650
patch=zlib.decompress((kit/'changes.patch.zlib').read_bytes())
assert sha(patch)=='eb3f213a17d5b01435d8beba5ccd5f48f35bc41d300d8dbeb440ad968f89d6ae'
patch.decode('utf-8');path=ev/'IFLC14.patch';path.write_bytes(patch)
subprocess.run(['git','apply','--check',str(path)],cwd=src,check=True)
subprocess.run(['git','apply',str(path)],cwd=src,check=True)
after={p.relative_to(src).as_posix():p.read_bytes() for p in (src/'SP/code').rglob('*') if p.is_file()}
changed=sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p))
assert changed==['SP/code/rend2/glsl/volumetriclocal_fp.glsl','SP/code/rend2/tr_architecture.inc','SP/code/rend2/tr_backend.c','SP/code/rend2/tr_iflc.inc','SP/code/rend2/tr_iflc_fixture.inc','SP/code/rend2/tr_iflc_self.inc','SP/code/rend2/tr_init.c','SP/code/rend2/tr_local.h','SP/code/rend2/tr_main.c','SP/code/rend2/tr_world.c'],changed
assert before['SP/code/rend2/tr_electric_fixture.inc']==after['SP/code/rend2/tr_electric_fixture.inc']
assert all(before[p]==after[p] for p in before if '/glsl/' in p and not p.endswith('volumetriclocal_fp.glsl'))
(ev/'IFLC14_SOURCE_SHA256.json').write_text(json.dumps({p:sha(b) for p,b in after.items()},indent=2)+'\n')
(ev/'IFLC14_SOURCE_PROOF.json').write_text(json.dumps({'base_run':41793236028,'accepted_production_run':41772470237,'input_files':len(before),'output_files':len(after),'changed':changed,'electric_fixture_unchanged':True,'new_budget_or_energy_cvars':[],'selfshadow_semantics':'0=own body off; 1=original own body on; auto=accepted V1.2 policy; no whole-light shadow disable','leak_checks_require_iflc_disabled':True,'status':'CANDIDATE_NOT_VISUALLY_ACCEPTED'},indent=2)+'\n')
print('IFLC14_EXACT_PATCH_APPLIED',len(after),changed)
