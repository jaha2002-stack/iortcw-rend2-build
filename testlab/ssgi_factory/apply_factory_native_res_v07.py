#!/usr/bin/env python3
"""Isolated SSGI full-resolution GENERATION test, not a production fix.

Apply after all previous SSGI TestLab patches, including donor-depth v0.6.
Modes 0..6 remain unchanged. Mode 7 inherits mode-6 donor depth validation
but renders GI into a dedicated native-size GL_RGBA8 FBO, avoiding the
512x384->1024x768 upsample for the same camera, sample radius and shader.
Do not resize or share either quarterFbo: bloom, volumetrics and other passes
must retain their original buffers. Also make r_ssgiDebug=7 actually reachable.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "source")
base = root / "SP/code/rend2"
local = base / "tr_local.h"
img = base / "tr_image.c"
fbo = base / "tr_fbo.c"
backend = base / "tr_backend.c"
init = base / "tr_init.c"

def patch_once(path, old, new):
    s = path.read_text()
    assert s.count(old) == 1, f"{path}: anchor found {s.count(old)} times: {old[:100]!r}"
    assert "FACTORY_SSGI_V07_NATIVE_RESOLUTION" not in s, f"{path}: already patched"
    path.write_text(s.replace(old, new))
    
path=local
s=path.read_text()
a="\timage_t                 *ssgiEntityDepthImage;"
b="\tFBO_t                   *ssgiEntityDepthFbo;"
assert s.count(a)==1 and s.count(b)==1, "ssgi mask local fields missing"
s=s.replace(a, a+"\n\timage_t                 *ssgiNativeImage; // FACTORY_SSGI_V07_NATIVE_RESOLUTION")
s=s.replace(b, b+"\n\tFBO_t                   *ssgiNativeFbo; // FACTORY_SSGI_V07_NATIVE_RESOLUTION")
path.write_text(s)

path=img
s=path.read_text()
anchor="\t\tqglTextureParameterfEXT(tr.ssgiEntityDepthImage->texnum, GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);"
assert s.count(anchor)==1, "ssgi entity depth image init anchor missing"
s=s.replace(anchor, anchor+"""
\t\t// FACTORY_SSGI_V07_NATIVE_RESOLUTION: dedicated isolated full-size GI target.
\t\t// Match the legacy GL_RGBA8 format: only resolution changes in the A/B.
\t\ttr.ssgiNativeImage = R_CreateImage("*ssgiNativeV07", NULL, width, height,
\t\t\tIMGTYPE_COLORALPHA, IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE, GL_RGBA8);
""")
path.write_text(s)

path=fbo
s=path.read_text()
anchor="\t\tR_CheckFBO(tr.ssgiEntityDepthFbo);\n\t}"
assert s.count(anchor)==1, "ssgi mask FBO init anchor missing"
s=s.replace(anchor, anchor+"""
\t// FACTORY_SSGI_V07_NATIVE_RESOLUTION: do NOT touch quarterFbo[0/1].
\tif (tr.ssgiNativeImage)
\t{
\t\ttr.ssgiNativeFbo = FBO_Create("_ssgiNativeV07",
\t\t\ttr.ssgiNativeImage->width, tr.ssgiNativeImage->height);
\t\tFBO_AttachImage(tr.ssgiNativeFbo, tr.ssgiNativeImage, GL_COLOR_ATTACHMENT0, 0);
\t\tR_CheckFBO(tr.ssgiNativeFbo);
\t}
""")
path.write_text(s)

path=backend
s=path.read_text()
clamp_old="\t\t\t\tif (debugMode > 6) debugMode = 6;"
assert s.count(clamp_old)==1, "v0.6 diagnostics are still clamped to 6?"
s=s.replace(clamp_old, "\t\t\t\tif (debugMode > 7) debugMode = 7; // FACTORY_SSGI_V07_NATIVE_RESOLUTION: enable real donor-depth debug7")
# Validate native FBO only when mode 7 was explicitly requested.
gate="\t\t\telse if (!tr.quarterFbo[0])\n\t\t\t\tssgiReason = \"no-quarter-fbo\";"
assert s.count(gate)==1, "SSGI quarter FBO gate not found"
s=s.replace(gate,gate+"""
\t\t\telse if (r_ssgiBrightSourceFix && r_ssgiBrightSourceFix->integer == 7
\t\t\t\t&& (!tr.ssgiNativeFbo || !tr.ssgiNativeImage))
\t\t\t\tssgiReason = "no-native-fbo";
""")

start_marker="\t\t\t\tivec4_t giSrcBox, giBox;"
end_marker="\t\t\t\tssgiActive = qtrue;"
start=s.find(start_marker)
end=s.find(end_marker,start)
assert start>=0 and end>start, "SSGI postprocess block could not be isolated"
body=s[start:end]
assert body.count("tr.quarterFbo[0]")>=3, "SSGI half-res FBO generation/resolve usages unexpected"
assert body.count("tr.quarterImage[0]")>=2, "SSGI half-res image usage unexpected"
# All target references inside JUST this SSGI pass become selected work target.
body=body.replace("tr.quarterFbo[0]", "ssgiWorkFbo")
body=body.replace("tr.quarterImage[0]", "ssgiWorkImage")
decl="""\n\t\t\t\t// FACTORY_SSGI_V07_NATIVE_RESOLUTION.
\t\t\t\t// Mode 7 = full-res generator, all other modes = unchanged half-res.
\t\t\t\tqboolean nativeSsgi = (r_ssgiBrightSourceFix &&
\t\t\t\t\tr_ssgiBrightSourceFix->integer == 7) ? qtrue : qfalse;
\t\t\t\tFBO_t *ssgiWorkFbo = nativeSsgi ? tr.ssgiNativeFbo : tr.quarterFbo[0];
\t\t\t\timage_t *ssgiWorkImage = nativeSsgi ? tr.ssgiNativeImage : tr.quarterImage[0];
\t\t\t\t{
\t\t\t\t\tstatic int lastMode = -1;
\t\t\t\t\tint mode = r_ssgiBrightSourceFix ? r_ssgiBrightSourceFix->integer : -1;
\t\t\t\t\tif (lastMode != mode)
\t\t\t\t\t{
\t\t\t\t\t\tlastMode = mode;
\t\t\t\t\t\tri.Printf(PRINT_ALL,
\t\t\t\t\t\t\t"FACTORY_SSGI_GEN_TARGET mode=%d size=%dx%d native=%d\\n",
\t\t\t\t\t\t\tmode, ssgiWorkFbo->width, ssgiWorkFbo->height,
\t\t\t\t\t\t\tnativeSsgi ? 1 : 0);
\t\t\t\t\t}
\t\t\t\t}
"""
body=body.replace(start_marker,start_marker+decl,1)
s=s[:start]+body+s[end:]
path.write_text(s)

path=init
s=path.read_text()
old="ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 6, qtrue ); // FACTORY_TESTLAB_DONOR_DEPTH_6_ONLY"
new="ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 7, qtrue ); // FACTORY_SSGI_V07_NATIVE_RESOLUTION"
assert s.count(old)==1, "BrightSourceFix mode6 range missing"
path.write_text(s.replace(old,new))
print("FACTORY_SSGI_V07_NATIVE_RESOLUTION_PATCH_PASS isolated_FBO=1 debug7_reachable=1")
