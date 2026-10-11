#!/usr/bin/env python3
"""Factory SSGI donor-origin proof v0.8 (TESTLAB ONLY, NEVER production).

Mode 8 deliberately vetoes donor samples from the *screen-space region* of
the pipe lamp on the already fixed Factory camera. This is NOT a game fix:
the rectangle is a scientific intervention to isolate whether the visible
artifact is *generated* from samples on the lamp itself. Mode 3 stays the
unchanged reference, mode 6 keeps its depth-veto and mode 7 remains full-res.
r_ssgiDebug=8 draws the intervention rectangle for visual verification.
When the hypothesis is confirmed, replace this rectangle with material-space
emissive identity; do not promote camera-specific logic.
"""
from pathlib import Path
import sys
root = Path(sys.argv[1] if len(sys.argv)>1 else "source")
base = root / "SP/code/rend2"
shader = base / "glsl/ssgi_fp.glsl"
backend = base / "tr_backend.c"
init = base / "tr_init.c"
s = shader.read_text()
old = "\tif (u_ViewInfo.w >= 5.5)\n\t{\n\t\tfloat brightContrast ="
new = "\tif (u_ViewInfo.w >= 5.5 && u_ViewInfo.w < 7.5)\n\t{\n\t\tfloat brightContrast ="
assert s.count(old)==1, "mode6 donor depth guard altered"
s = s.replace(old, new)

# uv x/y in source color buffer: screenshot lamp spans x=810..930,
# y=160..350 at 1024x768. GL screen UV y is bottom-up.
def_old = "\tif (donor <= 0.0001)\n\t\treturn;"
def_new = """\t// FACTORY_SSGI_V08_LAMP_DONOR_ISOLATION: screen-space TEST ONLY.
\t// Half-res mode 8 = SAME mode-3 donor filtering except skip all samples
\t// from the lamp area. This box must never enter production shaders.
\tif (u_ViewInfo.w >= 7.5 && u_ViewInfo.w < 8.5)
\t{
\t\tif (uv.x > 0.765 && uv.x < 0.945 &&
\t\t\tuv.y > 0.53 && uv.y < 0.83)
\t\t\treturn;
\t}
\tif (donor <= 0.0001)
\t\treturn;"""
assert s.count(def_old)==1, "donor gate altered"
s = s.replace(def_old, def_new)

debug_anchor = "\t// High-signal diagnostics. White means the tested condition is present."
debug = """\t// FACTORY_SSGI_V08_LAMP_REGION_MASK; white=source donor veto rectangle.
\tif (u_Color.w > 7.5 && u_Color.w < 8.5)
\t{
\t\tfloat boxMask = step(0.765, var_ScreenTex.x) *
\t\t\t(1.0 - step(0.945, var_ScreenTex.x)) *
\t\t\tstep(0.53, var_ScreenTex.y) *
\t\t\t(1.0 - step(0.83, var_ScreenTex.y));
\t\tgl_FragColor = vec4(vec3(boxMask), 1.0);
\t\treturn;
\t}

"""
assert s.count(debug_anchor)==1, "debug shader anchor altered"
shader.write_text(s.replace(debug_anchor,debug+debug_anchor))

s = backend.read_text()
old = "if (debugMode > 7) debugMode = 7;"
new = "if (debugMode > 8) debugMode = 8;"
assert s.count(old)==1, "debug mode clamp altered"
backend.write_text(s.replace(old,new))

s=init.read_text()
old = "ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 7, qtrue ); // FACTORY_SSGI_V07_NATIVE_RESOLUTION"
new = "ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 8, qtrue ); // FACTORY_SSGI_V08_LAMP_DONOR_ISOLATION_TEST_ONLY"
assert s.count(old)==1, "mode7 cvar provenance altered"
init.write_text(s.replace(old,new))
print("FACTORY_SSGI_V08_LAMP_DONOR_PROOF_PASS locked_camera_only=1 mode8=source-isolation debug8=ROI modes0to7=unchanged")
