#!/usr/bin/env python3
"""SSGI TestLab v0.6: isolate false GI from discontinuous donor depth.

Use only after the v0.3 emitter and v0.4 receiver-edge patches. The new mode 6
uses mode-3 emitter attenuation and an additional depth-continuity test at the
DONOR coordinate, not the receiving surface. It leaves modes 0..5 unchanged.
Mode 7 of r_ssgiDebug visualizes the bright, discontinuous donor-candidate mask.
This is a diagnosis, NOT a production-quality fix or a validated performance
optimization.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "source")
shader = root / "SP/code/rend2/glsl/ssgi_fp.glsl"
init = root / "SP/code/rend2/tr_init.c"
s = shader.read_text()
guard_old = "\tif (u_ViewInfo.w >= 4.5)\n\t{\n\t\tfloat planeConfidence ="
guard_new = "\tif (u_ViewInfo.w >= 4.5 && u_ViewInfo.w < 5.5)\n\t{\n\t\tfloat planeConfidence ="
assert s.count(guard_old) == 1, "Cannot isolate prior mode-5 receiver guard"
s = s.replace(guard_old, guard_new)

function_anchor = "void SsgiAccumulate(const vec2 offset,"
function = """// FACTORY_SSGI_DONOR_DEPTH_CONTINUITY_V06: donor-space silhouette validity.
// Unlike the mode-5 test, this does not erase GI at receiving silhouettes.
// Four full-resolution depth taps detect mixed foreground/background samples.
float SsgiDonorDepthConfidence(const vec2 uv,
    const float sampleDepth, const vec2 generatorTexel)
{
    vec2 t = max(generatorTexel * 0.5, vec2(0.00001));
    vec2 lo = vec2(0.001);
    vec2 hi = vec2(0.999);
    float a = SsgiLinearDepth(clamp(uv + vec2(t.x, 0.0), lo, hi));
    float b = SsgiLinearDepth(clamp(uv - vec2(t.x, 0.0), lo, hi));
    float c = SsgiLinearDepth(clamp(uv + vec2(0.0, t.y), lo, hi));
    float d = SsgiLinearDepth(clamp(uv - vec2(0.0, t.y), lo, hi));
    float minDepth = min(sampleDepth, min(min(a, b), min(c, d)));
    float maxDepth = max(sampleDepth, max(max(a, b), max(c, d)));
    float worldGap = (maxDepth - minDepth) * u_ViewInfo.y;
    float worldDistance = max(sampleDepth * u_ViewInfo.y, 1.0);
    float start = max(2.5, worldDistance * 0.013);
    float end = start * 2.8 + 3.0;
    return 1.0 - smoothstep(start, end, worldGap);
}

"""
assert s.count(function_anchor) == 1, "Cannot find unique donor accumulation function"
s = s.replace(function_anchor, function + function_anchor)

donor_old = "\tif (donor <= 0.0001)\n\t\treturn;"
donor_new = """\t// Mode 6: unlike mode 5, veto BRIGHT donor samples straddling a true
\t// foreground/background depth discontinuity. Preserve donors from smooth
\t// surfaces and keep the legacy receiver weighting unchanged.
\tif (u_ViewInfo.w >= 5.5)
\t{
\t\tfloat brightContrast = smoothstep(0.025, 0.23, max(sourceLuma - centerLuma, 0.0));
\t\tfloat continuity = SsgiDonorDepthConfidence(uv, sampleDepth, maskTexel);
\t\tdonor *= mix(1.0, continuity, brightContrast);
\t}
\tif (donor <= 0.0001)
\t\treturn;"""
assert s.count(donor_old) == 1, "Cannot find unique donor weight gate"
s = s.replace(donor_old, donor_new)

debug_anchor = "\t// High-signal diagnostics. White means the tested condition is present."
debug = """\t// TestLab mode-7 visualization: BRIGHT donor candidates at depth jumps.
\tif (u_Color.w > 6.5 && u_Color.w < 7.5)
\t{
\t\tfloat validity = SsgiDonorDepthConfidence(var_ScreenTex, centerDepth, maskTexel);
\t\tfloat brightRisk = smoothstep(0.14, 0.80, SsgiLuma(centerColor));
\t\tgl_FragColor = vec4(vec3(brightRisk * (1.0 - validity)), 1.0);
\t\treturn;
\t}

"""
assert s.count(debug_anchor) == 1, "Cannot find unique debug hook"
s = s.replace(debug_anchor, debug + debug_anchor)
shader.write_text(s)

q = init.read_text()
before = "ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 5, qtrue ); // FACTORY_TESTLAB_ROOT_EDGE_5_ONLY"
after = "ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 6, qtrue ); // FACTORY_TESTLAB_DONOR_DEPTH_6_ONLY"
assert q.count(before) == 1, "Wrong SSGI test-range provenance"
init.write_text(q.replace(before, after))
print("FACTORY_SSGI_DONOR_DEPTH_V06_PATCH_PASS modes0to5=unchanged mode6=donor-continuity debug7=bright-edge")
