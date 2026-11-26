#!/usr/bin/env python3
import gzip, hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LOCK=json.loads((ROOT/'baseline_source_manifest.json').read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def run(*args,cwd=None):subprocess.run(args,cwd=cwd,check=True)
def reconstruct(dest):
    dest=Path(dest).resolve()
    if dest.exists():raise SystemExit(f'Refusing to overwrite {dest}')
    run('git','clone','--quiet',LOCK['upstream'],str(dest))
    run('git','checkout','--quiet','--detach',LOCK['upstream_sha'],cwd=dest)
    for row in LOCK['patches']:
        data=(ROOT/row['file']).read_bytes();assert sha(data)==row['compressed_sha256'],row['file']
        patch=gzip.decompress(data);assert sha(patch)==row['sha256'],row['file']
        args=['git','apply','--binary','--whitespace=nowarn']+['--include='+s for s in row['includes']]
        subprocess.run(args+['--check','-'],input=patch,cwd=dest,check=True)
        subprocess.run(args+['-'],input=patch,cwd=dest,check=True)
    for name,digest in LOCK['baseline_source_files'].items():
        assert sha((dest/name).read_bytes())==digest,name
    run('git','add','-A',cwd=dest)
    tree=subprocess.check_output(['git','write-tree'],cwd=dest,text=True).strip()
    assert tree==LOCK['baseline_source_tree'],(tree,LOCK['baseline_source_tree'])
    run('git','-c','user.name=DarkWolf Engineering','-c','user.email=ci@example.invalid','commit','-qm','Component-correct v4.4.6 baseline',cwd=dest)
    print('BASELINE_SOURCE_TREE_PASS',tree)
if __name__=='__main__':reconstruct(sys.argv[1])
