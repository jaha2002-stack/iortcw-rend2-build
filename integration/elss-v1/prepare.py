#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile,tempfile,zipfile
E=Path('evidence');S=Path('source');E.mkdir(exist_ok=True)
artifact=E/'iflc15u_exact_source_artifact.zip'
with artifact.open('wb') as f:
    subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13354259063/zip'],stdout=f,check=True)
assert hashlib.sha256(artifact.read_bytes()).hexdigest()=='d4c71f7b1fa830568bdae6c7472a6f5488709ebc2078679c92b9bac7886ae0d4'
with zipfile.ZipFile(artifact) as z:z.extractall(E/'iflc15u')
tar=next((E/'iflc15u').rglob('IFLC_V15U_EXACT_SOURCE.tar.gz'))
manifest=json.loads(next((E/'iflc15u').rglob('IFLC15U_SOURCE_SHA256.json')).read_text())
assert hashlib.sha256(tar.read_bytes()).hexdigest()=='e4026d4827151a3c6d87d7cfd7489332ea67b6e391f7ca19a742091246ea33e4'
with tempfile.TemporaryDirectory() as td:
    exact=Path(td)/'exact';exact.mkdir()
    with tarfile.open(tar,'r:gz') as t:t.extractall(exact,filter='data')
    if S.exists():shutil.rmtree(S)
    subprocess.run(['git','clone','--filter=blob:none','--no-checkout','https://github.com/iortcw/iortcw',str(S)],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['git','-C',str(S),'checkout','438e7d413b5f7277187c35b032eb0ef9093ae778'],check=True,stdout=subprocess.DEVNULL)
    shutil.rmtree(S/'SP/code')
    shutil.copytree(exact/'SP/code',S/'SP/code')
    shutil.copy2(exact/'SP/Makefile',S/'SP/Makefile')
sha=lambda b:hashlib.sha256(b).hexdigest()
actual={p.relative_to(S).as_posix():sha(p.read_bytes()) for p in (S/'SP/code').rglob('*') if p.is_file()}
assert actual==manifest and len(actual)==1652,(len(actual),len(manifest))
assert (S/'SP/misc/wolf.ico').is_file()
(E/'ELSS_V1_BASE_SHA256.json').write_text(json.dumps(actual,indent=2)+'\n')
print('ELSS_V1_EXACT_IFLC15U_BASE_VERIFIED',len(actual),'RUN=41895006605')
