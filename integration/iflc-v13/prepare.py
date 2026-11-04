#!/usr/bin/env python3
"""Restore all 1649 exact source files of the user's accepted IFLC V1.2."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile,zipfile
out=Path('source');ev=Path('evidence');ev.mkdir(exist_ok=True);archive=ev/'accepted-v12.zip'
with archive.open('wb') as f:subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13295796794/zip'],stdout=f,check=True)
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='91b4427ae536b9ebf8f0a963f9fbceaef75a62e635c5f8cbf133603d8505e748'
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None;z.extractall(ev/'accepted')
up='438e7d413b5f7277187c35b032eb0ef9093ae778'
subprocess.run(['git','init',str(out)],check=True,stdout=subprocess.DEVNULL)
subprocess.run(['git','-C',str(out),'fetch','--depth=1','https://github.com/iortcw/iortcw',up],check=True)
subprocess.run(['git','-C',str(out),'checkout','--detach','FETCH_HEAD'],check=True,stdout=subprocess.DEVNULL)
shutil.rmtree(out/'SP/code')
with tarfile.open(next((ev/'accepted').rglob('IFLC_V12_EXACT_SOURCE.tar.gz'))) as t:t.extractall(out,filter='data')
manifest=json.loads(next((ev/'accepted').rglob('IFLC12_SOURCE_SHA256.json')).read_text())
actual={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'SP/code').rglob('*') if p.is_file()}
assert actual==manifest and len(actual)==1649
assert hashlib.sha256((out/'SP/Makefile').read_bytes()).hexdigest()=='9cb33a3b0ce2e449edd449fb97c885a1174c868ce5e77c9b84b0645518351740'
(ev/'IFLC13_BASE_SHA256.json').write_text(json.dumps(actual,indent=2)+'\n')
print('EXACT_ACCEPTED_IFLC12_41772470237_VERIFIED',len(actual),flush=True)
