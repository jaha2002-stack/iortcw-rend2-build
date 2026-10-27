#!/usr/bin/env python3
"""Static integrity checks for the V3 diagnostic repair, not a GPU runtime substitute."""
import ast
import hashlib
from pathlib import Path
import re

root=Path(__file__).resolve().parent
header=(root/'sky_diag_runtime.h').read_text()
patcher=(root/'apply.py').read_text()
packager=(root/'package.py').read_text()
assert 'DARKWOLF_SKY_MSAA_ROOT_CAUSE_MATRIX_V1' in header
# Parenthesis/brace/bracket balancing, excluding C strings and comments.
clean = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
               lambda m: " " * len(m.group(0)), header, flags=re.S)
opened=[]
for index, char in enumerate(clean):
    if char in "({[": opened.append((char,index))
    elif char in ")}]":
        assert opened, ("UNBALANCED_C_HEADER_UNEXPECTED_CLOSE",index,char)
        previous,_=opened.pop()
        assert (previous,char) in (("(",")"),("{","}"),("[","]")), ("MISMATCHED_C_HEADER_BRACKET",index)
assert not opened, ("UNBALANCED_C_HEADER_OPEN", opened[-5:])
assert 'V3 DIAGNOSTIC CAPTURE CORRECTION' in header
assert '#define DW_SKY_DIAG_MODES 5' in header
assert re.search(r'if \(!dwSkyDiagModeLogged\)\s*\{\s*dwSkyDiagModeLogged=1;',header)
assert 'DW_SKY_DIAG_TRACE_CAPACITY 65536' in header
assert re.search(r'!dwSkyDiagAuto->integer \|\| !dwSkyDiagArmed',header)
assert 'r_skyDiagArm' in header and 'dwSkyDiagArm->integer' in header
assert 'DW_SkyDiagSkyStage' in header and 'dwSkyDiagSkyCaptureDone=1' in header
assert 'DW_SkyDiagAfterResolve' in header and 'DW_SkyDiagOnSwap' in header
assert 'DW_SkyDiagRead(NULL,"final",0,1)' in header
assert 'GL_RGBA' in header and 'GL_FLOAT' in header
assert 'GL_PREEXISTING_ERROR' in header and 'READBACK_ERROR' in header
assert 'MODE_TIMEOUT_MS 9500' in header
assert 'dwSkyDiagCameraMotion' in header
assert 'RUN_COMPLETE,5,failures=' in header
assert re.search(r'if \(DW_SkyDiagRead\(tr\.msaaResolveFbo,"sky_early",0,0\)\)',header)
assert not re.search(r'(?<![A-Za-z0-9_])(glIsEnabled|glPixelStorei|glReadBuffer)\s*\(',header)
assert 'SKY_DIAG_V3' in patcher and 'DARKWOLF_HDR_MSAA_SELECTIVE_SAMPLE_SHADING_PRODUCTION_INTEGRATION' in patcher
m=ast.parse(packager)
vars={}
for node in m.body:
    if isinstance(node,ast.Assign):
        for t in node.targets:
            if isinstance(t,ast.Name) and t.id in ('launcher','cfg','readme','verifier'):
                vars[t.id]=ast.literal_eval(node.value)
assert set(vars)=={'launcher','cfg','readme','verifier'}
assert 'bind F8 "set r_skyDiagArm 1"' in vars['cfg']
assert 'press F8 ONCE' in vars['launcher']
assert 'VERIFY_SKY_DIAG.ps1' in vars['launcher']
assert 'r_customwidth 1280' in vars['launcher']
assert 'RUN_COMPLETE,5,failures=' in vars['verifier']
assert "'sky_early.pfm','resolved_hdr.pfm','resolved_depth.pfm','final.ppm'" in vars['verifier']
assert 'allValid = $false' in vars['verifier']
assert 'exit 2' in vars['verifier']
assert 'V2 FAILED:' in vars['readme']
assert 'DarkWolf_Sky_MSAA_RootCause_Matrix_V3_Win64.zip' in packager
assert 'EXPECTED_BASE_ZIP' in packager
assert 'REFERENCE_UNMODIFIED_FILES' in packager
# Regression gates: the V2 skySeen prerequisite suppressed ALL GPU captures.
# These static checks reject that architecture even when C itself compiles.
import re
begin=header.index('static void DW_SkyDiagAfterResolve(FBO_t *resolved)')
end=header.index('static void DW_SkyDiagOnSwap(void)',begin)
after=header[begin:end]
swap=header[end:]
assert '!dwSkyDiagSkySeen' not in after, 'V2_REGRESSION_HDR_GATED_BY_SKY'
assert 'dwSkyDiagSkySeen &&' not in swap, 'V2_REGRESSION_FINAL_GATED_BY_SKY'
assert 'DW_SkyDiagCaptureNow() && !dwSkyDiagFinalCaptureDone' in swap
assert 'DW_SkyDiagPreResolve(void)' in header
assert 'SKY_EARLY_SOURCE,FALLBACK_PRE_POST_SCENE_NOT_SKY_ONLY' in header
assert 'SKY_PROBE,mode=' in header and 'DW_SkyDiagSkyProbe(int phase)' in header
assert 'dwSkyDiagWorldSeen || dwSkyDiagMode>=' not in header[header.index('int DW_SkyDiagMode(void)'):header.index('static void DW_SkyDiagBeginView')]
assert "DW_SkyDiagPreResolve();" in patcher, 'PRE_RESOLVE_HOOK_REQUIRED'
assert 'DW_SkyDiagSkyProbe(0);' in patcher
assert 'DW_SkyDiagControlUsed(DW_SkyDiagMode());' in patcher
assert "dwSkyDiagSkySeen && !dwSkyDiagFinalCaptureDone" not in header
assert 'DARKWOLF_SKY_DIAG_V3' in packager
print('DARKWOLF_SKY_DIAG_V3_STATIC_FEATURE_GATES_PASS')
for p in (root/'sky_diag_runtime.h',root/'apply.py',root/'package.py',root/'test.py'):
    print('SHA256',p.name,hashlib.sha256(p.read_bytes()).hexdigest())
