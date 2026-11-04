#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,sys
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
kit=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest()
before={p.relative_to(src).as_posix():p.read_bytes() for p in (src/'SP/code').rglob('*') if p.is_file()}
expected=json.loads((ev/'IFLC15_BASE_SHA256.json').read_text());assert {p:sha(b) for p,b in before.items()}==expected
patch=kit/'IFLC15.patch';subprocess.run(['git','apply','--check',str(patch)],cwd=src,check=True);subprocess.run(['git','apply',str(patch)],cwd=src,check=True)
after={p.relative_to(src).as_posix():p.read_bytes() for p in (src/'SP/code').rglob('*') if p.is_file()}
changed=sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p))
assert changed==['SP/code/rend2/tr_iflc.inc','SP/code/rend2/tr_iflc_self.inc'],changed
assert before['SP/code/rend2/tr_electric_fixture.inc']==after['SP/code/rend2/tr_electric_fixture.inc']
assert all(before[p]==after[p] for p in before if '/glsl/' in p), 'V1.5 must not touch GLSL'
(ev/'IFLC15_SOURCE_SHA256.json').write_text(json.dumps({p:sha(b) for p,b in after.items()},indent=2)+'\n')
(ev/'IFLC15_SOURCE_PROOF.json').write_text(json.dumps({'base_run':41808242270,'accepted_production_run':41772470237,'input_files':len(before),'output_files':len(after),'changed':changed,'v14_native_containment_unchanged':True,'v13_electric_fixture_unchanged':True,'glsl_unchanged':True,'purpose':'manual exact-body self-shadow binding only','status':'TEST_CANDIDATE'},indent=2)+'\n')
print('IFLC15_PATCH_APPLIED',changed)
