#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve()
ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
scene=root/'tr_scene.c'
inc_src=Path(__file__).with_name('tr_escape1_dlight_residency_audit.inc')
inc_dst=root/'tr_escape1_dlight_residency_audit.inc'
text=scene.read_text()

include_marker='static int R_StaticPromoteFindCrosshairFixture(float *forwardDistanceOut, float *lateralDistanceOut)\n'
if '#include "tr_escape1_dlight_residency_audit.inc"' not in text:
    assert include_marker in text
    text=text.replace(include_marker,'#include "tr_escape1_dlight_residency_audit.inc"\n\n'+include_marker,1)

hook='\tR_StaticPromoteUSLRDDiagFrame();\n'
if 'R_DarkWolfEscape1DlightResidencyAuditFrame(fd);' not in text:
    assert hook in text
    text=text.replace(hook,hook+'\tR_DarkWolfEscape1DlightResidencyAuditFrame(fd);\n',1)

scene.write_text(text)
inc_dst.write_bytes(inc_src.read_bytes())

proof={
  'marker':'DARKWOLF_ESCAPE1_DLIGHT_RESIDENCY_AUDIT_V1',
  'scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest(),
  'inc_sha256':hashlib.sha256(inc_dst.read_bytes()).hexdigest(),
  'read_only':True,
  'map_scope':'escape1',
}
(ev/'EDRA_V1_APPLY_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof,indent=2))
