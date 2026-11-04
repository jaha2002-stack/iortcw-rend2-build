#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile,zipfile
E=Path('evidence');S=Path('source');E.mkdir(exist_ok=True)
zip_path=E/'iflc14_exact_source_artifact.zip'
with zip_path.open('wb') as f:
    subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13310164270/zip'],stdout=f,check=True)
with zipfile.ZipFile(zip_path) as z:
    z.extractall(E/'iflc14')
tar=next((E/'iflc14').rglob('IFLC_V14_EXACT_SOURCE.tar.gz'))
manifest=json.loads(next((E/'iflc14').rglob('IFLC14_SOURCE_SHA256.json')).read_text())
if S.exists(): shutil.rmtree(S)
S.mkdir()
with tarfile.open(tar,'r:gz') as t:t.extractall(S,filter='data')
sha=lambda b:hashlib.sha256(b).hexdigest()
actual={p.relative_to(S).as_posix():sha(p.read_bytes()) for p in (S/'SP/code').rglob('*') if p.is_file()}
assert actual==manifest and len(actual)==1652,(len(actual),len(manifest))
(E/'IFLC15_BASE_SHA256.json').write_text(json.dumps(actual,indent=2)+'\n')
print('IFLC15_EXACT_V14_BASE_VERIFIED',len(actual))
