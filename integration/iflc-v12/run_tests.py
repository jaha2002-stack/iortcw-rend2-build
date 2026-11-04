#!/usr/bin/env python3
from pathlib import Path
import argparse,tempfile,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('evidence',type=Path);a=p.parse_args();kit=Path(__file__).resolve().parent;a.evidence.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as d:
 d=Path(d)
 for f in (kit.parent/'iflc-v1/tests').iterdir():
  if f.is_file():shutil.copy2(f,d/f.name)
 f=d/'iflc_cpu_tests.c';s=f.read_text();shaft=(kit/'shaft_tests.inc').read_text()
 needle='      dl.iflcOptIn=qfalse;CHECK(R_IFLC_ShadowFixture(&dl)==0,"no native/promoted policy expansion");'
 assert shaft.count(needle)==1
 shaft=shaft.replace(needle,'''      R_IFLC_ResetFixtures();Q_strncpyz(sh[2].name,"props/torch_ember",sizeof(sh[2].name));
      CHECK(R_IFLC_ShadowFixture(&dl)==1 && s_iflcFixtures[0].count==4,"opaque emissive names remain actual fixture geometry");
      R_IFLC_ResetFixtures();sh[2].sort=SS_SEE_THROUGH;R_IFLC_ShadowFixture(&dl);
      for(i=0;i<s_iflcFixtures[0].count;++i)CHECK(s_iflcFixtures[0].surfaces[i]!=2,"transparent stage not adopted as opaque self-caster");
      R_IFLC_ResetFixtures();sh[2].sort=SS_OPAQUE;R_IFLC_ShadowFixture(&dl);
'''+needle)
 ext=(kit.parent/'iflc-v11/fixture_tests.inc').read_text()+'\n'+shaft
 s=s.replace('int main(void) {',ext+'\nint main(void) {').replace('    TestClearFiles();\n    free(backEndData);','    TestFixturePolicy();\n    TestSlenderTorch();\n    TestClearFiles();\n    free(backEndData);');f.write_text(s)
 subprocess.run(['python3',str(d/'run_cpu_tests.py'),str(a.source),'--sanitize','--output',str(a.evidence/'IFLC12_CPU_TESTS.json')],check=True)
for name in ('run_backend_tests.py','run_shadow_tests.py'):
 subprocess.run(['python3',str(kit.parent/'iflc-v1/tests'/name),str(a.source),'--output',str(a.evidence/name[:-3])],check=True)
