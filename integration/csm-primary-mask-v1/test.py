#!/usr/bin/env python3
"""Extend exact RC4 native source-extraction C harness with portal/main masks and real-door changes."""
import base64,zlib,subprocess,sys
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
ref=Path('integration/rc4-final-csm/test_csm_integration.py.zlib.b64')
raw=base64.b64decode(ref.read_bytes());source=zlib.decompress(raw).decode('utf-8')
def once(old,new,label):
    global source
    assert source.count(old)==1,(label,source.count(old))
    source=source.replace(old,new,1)
once('typedef struct {int time,rdflags;float fov_x,fov_y;vec3_t vieworg;vec3_t viewaxis[3];} refdef_t;',
'''typedef unsigned char byte;
#define MAX_MAP_AREA_BYTES 32
typedef struct {int time,rdflags;float fov_x,fov_y;vec3_t vieworg;vec3_t viewaxis[3];byte areamask[MAX_MAP_AREA_BYTES];} refdef_t;''','native FD primary mask type')
once('tr.refdef.areamaskModified=qtrue;reprime(10,1144,"area-mask-door");',
     'fd.areamask[0]^=1;tr.refdef.areamaskModified=qtrue;reprime(10,1144,"area-mask-door");', 'real primary mask invalidation')
once('    puts("ALL_CSM_NATIVE_INTEGRATION_TESTS_PASS");return 0;',
'''    // Simulate skybox changing the SHARED tr.refdef mask while the player's true fd mask stays stable.
    tr.refdef.areamaskModified=qtrue;
    zeroCounts();runFrame(129,3048);
    equals(1,0,0,0,"auxiliary-portal-must-not-reprime");
    puts("PASS secondary-skybox-mask-change-suppressed");
    // Actual main-view visibility change is still a hard invalidation of every cascade.
    fd.areamask[0]^=1;
    zeroCounts();runFrame(130,3064);
    equals(1,1,1,1,"real-primary-world-door-transition");
    puts("PASS real-primary-mask-door-reprimes");
    puts("ALL_CSM_NATIVE_INTEGRATION_TESTS_PASS");return 0;''','skybox and real door regression')
assert 'DARKWOLF_RC4_FORCE_SUN_CSM_REPRIME_V1' in (a.source/'SP/code/rend2/tr_scene.c').read_text()
assert 'DARKWOLF_CSM_PRIMARY_VIEW_AREAMASK_V1' in (a.source/'SP/code/rend2/tr_scene.c').read_text()
script=a.out/'source_extracted_csm_test.py';script.write_text(source)
run=subprocess.run([sys.executable,str(script),str(a.source),'--out',str(a.out/'native')],text=True,capture_output=True)
(a.out/'test-output.log').write_text(run.stdout+run.stderr)
print(run.stdout,flush=True)
if run.returncode:
  print(run.stderr,file=sys.stderr)
  raise SystemExit(run.returncode)
assert 'ALL_CSM_NATIVE_INTEGRATION_TESTS_PASS' in run.stdout
assert 'PASS secondary-skybox-mask-change-suppressed' in run.stdout
assert 'PASS real-primary-mask-door-reprimes' in run.stdout
print('DW_CSM_PRIMARY_MASK_NATIVE_REGRESSION_PASS',flush=True)
