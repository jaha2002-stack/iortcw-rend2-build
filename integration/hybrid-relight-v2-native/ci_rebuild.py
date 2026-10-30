#!/usr/bin/env python3
"""Replays source-construction steps from the accepted pinned HDR16F workflow."""
from pathlib import Path
import os,re,subprocess
WORKFLOW=Path('.github/workflows/DW_SUN_HDR16F_PRECISION_V1_FROM_40878732886.yml')
PRE='Apply Sun-only HDR16F V1 to exact completed 408787 source'
COMP='Cross-compile ALL five game and renderer Win64 binaries from September base'
def scripts(data):
    chunks=re.split(r'(?m)^      - name: ',data)
    for x in chunks[1:]:
        name=x.splitlines()[0].strip()
        lines=x.splitlines(keepends=True)
        p=[i for i,line in enumerate(lines) if line=='        run: |\n']
        if not p:continue
        n=p[0]+1;body=[]
        while n<len(lines):
            line=lines[n]
            if line.startswith('          '):body.append(line[10:])
            elif not line.strip():body.append('\n')
            else:break
            n+=1
        if body:yield name,''.join(body)
def run(name,cmd):
    print('DW_SOURCE_REPLAY',name,flush=True)
    res=subprocess.run(['/bin/bash','-e'],input=cmd,text=True,env=os.environ.copy())
    if res.returncode:raise RuntimeError(f'source stage failed {name}: {res.returncode}')
def main():
    data=WORKFLOW.read_text()
    assert '438e7d413b5f7277187c35b032eb0ef9093ae778' in data
    assert 'SUN_HDR16F_V1_PRODUCTION_SOURCE_READY' in data
    patched=compiled=False;names=[]
    for name,cmd in scripts(data):
        run(name,cmd);names.append(name)
        if name==PRE:
            run('NATIVE_PREFLIGHT',
                'python3 integration/hybrid-relight-v2-native/renderer_integration.py sept-source --check-only --proof evidence/NATIVE_PREFLIGHT.json')
            run('NATIVE_PATCH',
                'python3 integration/hybrid-relight-v2-native/renderer_integration.py sept-source --proof evidence/NATIVE_SOURCE_PROOF.json')
            run('VERIFY_NATIVE_SOURCE','git -C sept-source diff --check && grep -Fq "DW_HYBRID_V2:" sept-source/SP/code/rend2/tr_bsp.c')
            patched=True
        if name==COMP:
            compiled=True
            break
    if not patched or not compiled:raise RuntimeError('Failed to reach pinned source and build stages')
    Path('evidence/NATIVE_SOURCE_REPLAY_STAGES.txt').write_text('\n'.join(names)+'\n')
    print('DW_HYBRID_V2_NATIVE_SOURCE_REBUILD_PASS')
if __name__=='__main__':main()
