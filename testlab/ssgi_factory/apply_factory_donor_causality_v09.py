#!/usr/bin/env python3
"""Factory SSGI v0.9 donor causality controls, TESTLAB ONLY.

Runs after isolated v0.8. At the SAME fixed camera and screen-space ROI:
 mode 8  = remove ALL donors in the ROI (positive control).
 mode 9  = remove ONLY bright donors in the ROI (emissive-core hypothesis).
 mode 10 = remove ONLY nonbright donors in the ROI (complement).
 mode 11 = remove donors in a matching, distant screen ROI (negative control).
 r_ssgiDebug=9 = visualize core brightness mask in the ROI (same source RGB).
This experiment must NEVER be promoted: the screen-space region is camera-
dependent and can suppress useful indirect light.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "source")/"SP/code/rend2"
shader=root/"glsl/ssgi_fp.glsl"
backend=root/"tr_backend.c"
init=root/"tr_init.c"
s=shader.read_text()
anchor="\tif (donor <= 0.0001)\n\t\treturn;"
new="""\t// FACTORY_SSGI_V09_DONOR_CAUSALITY_CONTROLS
\t// Bright-only and its complement share the exact v0.8 spatial region.
\t// Source sampled from current frame: NOT a production emissive material id.
\tif (u_ViewInfo.w >= 8.5 && u_ViewInfo.w < 10.5)
\t{
\t\tbool lampROI = uv.x > 0.765 && uv.x < 0.945
\t\t\t&& uv.y > 0.53 && uv.y < 0.83;
\t\tbool highLuma = sourceLuma >= 0.72;
\t\tif (lampROI && ((u_ViewInfo.w < 9.5 && highLuma) ||
\t\t\t(u_ViewInfo.w >= 9.5 && !highLuma)))
\t\t\treturn;
\t}
\t// Same-size unrelated wall rectangle: negative spatial control.
\tif (u_ViewInfo.w >= 10.5 && u_ViewInfo.w < 11.5)
\t{
\t\tif (uv.x > 0.10 && uv.x < 0.28 &&
\t\t\tuv.y > 0.53 && uv.y < 0.83)
\t\t\treturn;
\t}
\tif (donor <= 0.0001)
\t\treturn;"""
assert s.count(anchor)==1,"unique donor tail anchor missing"
s=s.replace(anchor,new)
anchor="\t// High-signal diagnostics. White means the tested condition is present."
new="""\t// FACTORY_SSGI_V09_BRIGHT_CORE_MASK: high-luma area in the source ROI.
\tif (u_Color.w > 8.5 && u_Color.w < 9.5)
\t{
\t\tfloat roi = step(0.765, var_ScreenTex.x) *
\t\t\t(1.0-step(0.945, var_ScreenTex.x)) *
\t\t\tstep(0.53, var_ScreenTex.y) *
\t\t\t(1.0-step(0.83, var_ScreenTex.y));
\t\tfloat luma = SsgiLuma(centerColor);
\t\tfloat white = step(0.72, luma);
\t\tgl_FragColor = vec4(vec3(roi * white), 1.0);
\t\treturn;
\t}

\t// High-signal diagnostics. White means the tested condition is present."""
assert s.count(anchor)==1,"unique debug anchor missing"
s=s.replace(anchor,new)
shader.write_text(s)

s=backend.read_text()
anchor="if (debugMode > 8) debugMode = 8;"
assert s.count(anchor)==1,"debug clamp no longer mode8"
backend.write_text(s.replace(anchor,"if (debugMode > 9) debugMode = 9; // FACTORY_SSGI_V09_BRIGHT_CORE_MASK"))

s=init.read_text()
anchor="ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 8, qtrue ); // FACTORY_SSGI_V08_LAMP_DONOR_ISOLATION_TEST_ONLY"
assert s.count(anchor)==1,"SSGI v08 cvar gate changed"
init.write_text(s.replace(anchor,"ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 11, qtrue ); // FACTORY_SSGI_V09_DIAGNOSTIC_ONLY"))

print("FACTORY_SSGI_V09_CONTROLS_PASS original_v08_untouched=1 bright9_nonbright10_control11=1")
