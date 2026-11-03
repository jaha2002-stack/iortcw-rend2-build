#!/usr/bin/env python3
from pathlib import Path
import argparse, subprocess, tempfile, shutil
ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('evidence',type=Path);a=ap.parse_args()
kit=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as d:
 d=Path(d)
 for p in (kit.parent/'iflc-v1/tests').iterdir():
  if p.is_file():shutil.copy2(p,d/p.name)
 p=d/'iflc_cpu_tests.c';t=p.read_text();t=t.replace('int main(void) {',(kit/'fixture_tests.inc').read_text()+'\nint main(void) {');t=t.replace('    TestClearFiles();\n    free(backEndData);','    TestFixturePolicy();\n    TestClearFiles();\n    free(backEndData);');p.write_text(t)
 a.evidence.mkdir(parents=True,exist_ok=True)
 subprocess.run(['python3',str(d/'run_cpu_tests.py'),str(a.source),'--sanitize','--output',str(a.evidence/'IFLC_V11_CPU_TESTS.json')],check=True)
 for n in ('run_backend_tests.py','run_shadow_tests.py'):
  subprocess.run(['python3',str(kit.parent/'iflc-v1/tests'/n),str(a.source),'--output',str(a.evidence/n[:-3])],check=True)
