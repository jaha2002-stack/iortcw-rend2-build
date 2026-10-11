#!/usr/bin/env python3
"""TestLab-only depth-boundary SSGI diagnostic; DO NOT promote to production.

Runs AFTER apply_factory_emitter_fix_v01.py. Modes 3 and 4 remain unchanged;
mode 5 uses EXACT mode-3 donor rejection plus a hard receiver depth-edge guard.
An additional debug view plots the depth-edge risk so improvements can be
attributed to a cause rather than another arbitrary brightness threshold.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "source")
shader = root / "SP/code/rend2/glsl/ssgi_fp.glsl"
init = root / "SP/code/rend2/tr_init.c"

s = shader.read_text()
old = "\tif (u_ViewInfo.w >= 3.5)\n\t{\n\t\tconst float start = 0.56;"
new = "\tif (u_ViewInfo.w >= 3.5 && u_ViewInfo.w < 4.5)\n\t{\n\t\tconst float start = 0.56;"
assert s.count(old) == 1, "Expected unique mode-4 donor branch"
s = s.replace(old, new)

old = "\tbounce *= edgeStability;"
new = """\tbounce *= edgeStability;
\t// FACTORY_SSGI_ROOTCAUSE_DEPTH_EDGE_V04: mode 5 only.
\t// Existing SsgiEdgeStabilityAt() bottoms out at 0.60, leaving substantial
\t// false GI at silhouettes of tiny lamps. This test rejects the receiver
\t// contribution at strongly non-planar scene-depth boundaries while keeping
\t// the ORIGINAL mode-3 bright-donor function unmodified.
\tif (u_ViewInfo.w >= 4.5)
\t{
\t\tfloat planeConfidence = clamp((edgeStability - 0.60) * 2.5, 0.0, 1.0);
\t\tfloat receiverGuard = smoothstep(0.10, 0.75, planeConfidence);
\t\tbounce *= receiverGuard;
\t}
"""
assert s.count(old) == 1, "Expected unique depth confidence weighting"
s = s.replace(old, new)
shader.write_text(s)

s = init.read_text()
old = "ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 4, qtrue ); // FACTORY_TESTLAB_MODES_3_4_ONLY"
new = "ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 5, qtrue ); // FACTORY_TESTLAB_ROOT_EDGE_5_ONLY"
assert s.count(old) == 1, "Expected unique TestLab brightfix range"
s = s.replace(old, new)
old = "r_ssgiDebug = &s_darkwolfProductionDiagOffCvar;"
new = 'r_ssgiDebug = ri.Cvar_Get( "r_ssgiDebug", "0", 0 ); // TESTLAB_ROOT_CAUSE_DEBUG'
assert s.count(old) == 1, "Expected unique source diagnostic cvar"
s = s.replace(old, new)
init.write_text(s)
print("FACTORY_ROOT_CAUSE_EDGE_TEST_V04_PATCH_PASS modes3-4-unchanged mode5=hard-edge")
