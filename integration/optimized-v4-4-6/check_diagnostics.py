#!/usr/bin/env python3
"""Syntax-check diagnostic adapters early, before expensive builds."""
from pathlib import Path
import subprocess,sys,tempfile
kit=Path(__file__).resolve().parent;repo=kit.parent.parent
baseline=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as tmp:
 for label in ['baseline','optimized']:
  dst=Path(tmp)/label
  subprocess.run(['git','clone','-q','--shared',str(baseline),str(dst)],check=True)
  if label=='optimized':subprocess.run(['git','-C',str(dst),'apply',str(kit/'optimized.patch')],check=True)
  subprocess.run([sys.executable,str(repo/'testlab/scripts/apply_testlab_instrumentation.py'),str(dst)],check=True)
  subprocess.run([sys.executable,str(kit/'instrument_runtime.py'),str(dst)],check=True)
  subprocess.run(['gcc','-fsyntax-only','-DARCH_STRING="x86_64"','-D_GNU_SOURCE','-I',str(dst/'SP/code/SDL2/include'),*[str(dst/'SP/code'/f) for f in ['cgame/cg_view.c','cgame/cg_servercmds.c','rend2/tr_scene.c']]],check=True)
print('BOTH_DIAGNOSTIC_VARIANTS_SYNTAX_PASS')
