#!/usr/bin/env python3
"""Restore a checked source/test kit and apply verified GLSL compatibility correction."""
from pathlib import Path
import base64,hashlib,io,tarfile,json,subprocess,sys
h=Path(__file__).resolve().parent
expected='152bdbef5a389ca46a9006233e5ec1ccd4e03705a364b9c88d7a8dc3ee9bb14b'
names={'README.md','containment.patch','instrument.py','package.py','runtime.py','source-lock.json','test_cache.py'}
data=base64.b64decode(''.join((h/('kit.tar.xz.part%02d'%i)).read_text().strip() for i in range(4)),validate=True)
assert hashlib.sha256(data).hexdigest()==expected,'Containment kit checksum mismatch'
payload={}
with tarfile.open(fileobj=io.BytesIO(data),mode='r:xz') as archive:
 for member in archive:
  assert member.name in names and member.isfile() and member.size<1000000 and member.name not in payload
  payload[member.name]=archive.extractfile(member).read()
assert set(payload)==names
for name,value in payload.items():(h/name).write_bytes(value)
print('CONTAINMENT_KIT_VERIFIED',expected,flush=True)
if len(sys.argv)>1:
 source=Path(sys.argv[1]);lock=json.loads((h/'source-lock.json').read_text())
 def git(*args):return subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
 assert git('rev-parse','HEAD^{tree}')==lock['base_tree'],'Not exact RC4'
 assert not git('status','--porcelain'),'Dirty RC4 source'
 assert hashlib.sha256((h/'containment.patch').read_bytes()).hexdigest()==lock['patch_sha256']
 subprocess.run(['git','-C',str(source),'apply','--check',str(h/'containment.patch')],check=True)
 subprocess.run(['git','-C',str(source),'apply',str(h/'containment.patch')],check=True)
 assert sorted(git('diff','--name-only').splitlines())==sorted(lock['changed_files'])
 git('add','SP/code')
 assert git('write-tree')==lock['candidate_tree'],'Initial candidate source identity mismatch'
 # Mesa compilation identified `packed` as a reserved GLSL word. Rename only
 # this local depth sample; no formula, policy or emitted source is changed.
 for name in ['lightall_fp.glsl','dlight_fp.glsl']:
  p=source/'SP/code/rend2/glsl'/name;t=p.read_text()
  assert t.count('vec3 packed =')==2 and t.count('dot(packed,')==1
  p.write_text(t.replace('vec3 packed =','vec3 encodedDepth =').replace('dot(packed,','dot(encodedDepth,'))
 git('add','SP/code')
 assert git('write-tree')=='3bd8085e2169af3cd40686bbcaa986c92c49cca4','GLSL corrected source identity mismatch'
 patch=subprocess.check_output(['git','-C',str(source),'diff','--cached','--binary'])
 assert hashlib.sha256(patch).hexdigest()=='66990f63e1295d6ea691e75d8404066a803866e546831c9b83b212fd636ffc26'
 lock['candidate_tree']=git('write-tree');lock['patch_sha256']=hashlib.sha256(patch).hexdigest()
 (h/'containment.patch').write_bytes(patch);(h/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
 git('-c','user.name=DarkWolf CI','-c','user.email=ci@invalid.local','commit','-qm','RC4 architectural light containment candidate, verified GLSL compatibility')
 print('CONTAINMENT_SOURCE_TREE_PASS',lock['candidate_tree'],flush=True)
