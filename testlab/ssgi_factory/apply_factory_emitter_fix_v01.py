#!/usr/bin/env python3
"""Isolated v4.4.6 Factory SSGI source experiment, never applied to production.
BrightSourceFix=3 adds a stronger high-contrast bright-donor fringe rejection.
Legacy cvar modes 0, 1 and 2 remain unchanged for a true A/B comparison.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "source")
shader = root / "SP/code/rend2/glsl/ssgi_fp.glsl"
renderer = root / "SP/code/rend2/tr_init.c"
text = shader.read_text()
anchor = "\t// Final current-experiment correction: the bulb/flame core is both absolutely bright"
insertion = """\t// DARKWOLF_FACTORY_SSGI_EMITTER_FRINGE_TEST_V02 (TestLab mode 4).
\t// More selective than mode 3: keep most ordinary surface bounce while
\t// attenuating bright, high-contrast donors around a luminous fixture.
\tif (u_ViewInfo.w >= 3.5)
\t{
\t\tconst float start = 0.56;
\t\tconst float full = 1.04;
\t\tconst float contrastStart = 0.08;
\t\tconst float contrastFull = 0.39;
\t\tconst float donorFloor = 0.04;
\t\tfloat brightGate = smoothstep(start, full, metric);
\t\tfloat contrast = max(luma - centerLuma, 0.0);
\t\tfloat contrastGate = smoothstep(contrastStart, contrastFull, contrast);
\t\treturn mix(1.0, donorFloor, clamp(brightGate * contrastGate, 0.0, 1.0));
\t}

\t// DARKWOLF_FACTORY_SSGI_EMITTER_FRINGE_TEST_V01 (isolated TestLab mode 3).
\t// Existing modes 0, 1 and 2 are unchanged. Reject fringe donors when
\t// they are bright and substantially brighter than their receiving pixel.
\tif (u_ViewInfo.w >= 2.5)
\t{
\t\tconst float fringeStart = 0.42;
\t\tconst float fringeFull = 0.92;
\t\tconst float contrastStart = 0.055;
\t\tconst float contrastFull = 0.30;
\t\tfloat absoluteGate = smoothstep(fringeStart, fringeFull, metric);
\t\tfloat localContrast = max(luma - centerLuma, 0.0);
\t\tfloat contrastGate = smoothstep(contrastStart, contrastFull, localContrast);
\t\treturn 1.0 - clamp(absoluteGate * contrastGate, 0.0, 1.0);
\t}

"""
assert text.count(anchor) == 1, "SSGI donor shader anchor missing or ambiguous"
assert "DARKWOLF_FACTORY_SSGI_EMITTER_FRINGE_TEST_V01" not in text
shader.write_text(text.replace(anchor, insertion + anchor))
text = renderer.read_text()
old = "ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 2, qtrue );"
new = "ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 4, qtrue ); // FACTORY_TESTLAB_MODES_3_4_ONLY"
assert text.count(old) == 1, "BrightSourceFix runtime range anchor missing or ambiguous"
renderer.write_text(text.replace(old, new))
print("FACTORY_SSGI_MODE3_TESTLAB_INSTRUMENTATION_PASS")
