#!/usr/bin/env python3
"""Restore a checked source/test kit. No retail assets or external code execution."""
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
 assert git('write-tree')==lock['candidate_tree'],'Candidate source identity mismatch'
 git('-c','user.name=DarkWolf CI','-c','user.email=ci@invalid.local','commit','-qm','RC4 architectural light containment candidate')
 print('CONTAINMENT_SOURCE_TREE_PASS',lock['candidate_tree'],flush=True)
