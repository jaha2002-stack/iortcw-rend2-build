#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path('evidence').resolve()
ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
scene=root/'tr_scene.c'
inc_src=Path(__file__).with_name('tr_electric_owner_audit.inc')
inc_dst=root/'tr_electric_owner_audit.inc'
assert scene.is_file() and inc_src.is_file()

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
protected=['tr_backend.c','tr_main.c','tr_init.c','tr_local.h','tr_iflc.inc','tr_elss.inc']
before={n:sha(root/n) for n in protected if (root/n).is_file()}
text=scene.read_text()
if '#include "tr_electric_owner_audit.inc"' not in text:
    if '#include "tr_elss.inc"' in text:
        text=text.replace('#include "tr_elss.inc"','#include "tr_elss.inc"\n#include "tr_electric_owner_audit.inc"',1)
    else:
        assert '#include "tr_iflc.inc"' in text
        text=text.replace('#include "tr_iflc.inc"','#include "tr_iflc.inc"\n#include "tr_electric_owner_audit.inc"',1)
call='\tR_ElectricPhysicalOwnerAuditFrame(fd); // DARKWOLF_ELECTRIC_PHYSICAL_OWNER_AUDIT_V1 read-only post-allocation telemetry.\n'
if 'R_ElectricPhysicalOwnerAuditFrame(fd);' not in text:
    if '\tR_ELSS_CaptureShadowSlots(fd);' in text:
        anchor='\tR_ELSS_CaptureShadowSlots(fd);\n'
    else:
        anchor='\tR_IFLC_CaptureShadowSlots(fd); // Read-only command diagnostics after actual allocation.\n'
    assert text.count(anchor)==1, text.count(anchor)
    text=text.replace(anchor,anchor+call,1)
scene.write_text(text)
shutil.copy2(inc_src,inc_dst)
after={n:sha(root/n) for n in protected if (root/n).is_file()}
assert before==after,(before,after)
proof={
  'version':'ELECTRIC_PHYSICAL_OWNER_AUDIT_V1',
  'read_only':True,
  'default_enabled':False,
  'scene_hook':'after actual point-shadow allocation and after IFLC/ELSS shadow-slot snapshots',
  'changed_existing':['SP/code/rend2/tr_scene.c'],
  'added':['SP/code/rend2/tr_electric_owner_audit.inc'],
  'protected_unchanged':sorted(before),
}
(ev/'EPOA_V1_APPLY_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
print('EPOA_V1_APPLIED',json.dumps(proof,sort_keys=True))
