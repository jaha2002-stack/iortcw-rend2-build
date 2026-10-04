#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source")
B = ROOT / "SP/code/rend2/tr_backend.c"
I = ROOT / "SP/code/rend2/tr_image.c"
F = ROOT / "SP/code/rend2/tr_fbo.c"
H = ROOT / "SP/code/rend2/tr_local.h"
MARK = "DARKWOLF_VOLUMETRIC_NATIVE_AA_ATTEMPT3"


def rep(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ERROR {label}: expected 1 anchor, found {n}")
    return text.replace(old, new, 1)


b = B.read_text(encoding="utf-8")
i = I.read_text(encoding="utf-8")
f = F.read_text(encoding="utf-8")
h = H.read_text(encoding="utf-8")
if MARK in b:
    print("Attempt3 already applied")
    raise SystemExit(0)

required = [
    "DARKWOLF_SUN_VOLUMETRIC_V0_3",
    "DARKWOLF_LOCAL_VOLUMETRIC_V0_1",
    "DARKWOLF_FIREVOL_SPATIAL_RECONSTRUCTION_EDGE_QUALITY_PC02",
    "FBO_FastBlit(tr.renderFbo, NULL, tr.msaaResolveFbo, NULL, GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT, GL_NEAREST);",
]
for x in required:
    if x not in b:
        raise SystemExit("ERROR backend missing parent marker: " + x)
if "tr.quarterImage[x] = R_CreateImage" not in i:
    raise SystemExit("ERROR image quarter buffer contract missing")
if "tr.quarterFbo[i] = FBO_Create" not in f:
    raise SystemExit("ERROR quarter FBO contract missing")

# Dedicated full-resolution HDR scratch. This preserves the accepted main render FBO and
# all existing quarter buffers. It is color-only because the volumetric shaders sample
# tr.renderDepthImage; attaching that texture here would create framebuffer feedback.
img_anchor = '''\t\ttr.renderImage = R_CreateImage("_render", NULL, width, height, IMGTYPE_COLORALPHA, IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE, hdrFormat);\n\n\t\tif (r_shadowBlur->integer || r_hdr->integer)\n'''
img_new = '''\t\ttr.renderImage = R_CreateImage("_render", NULL, width, height, IMGTYPE_COLORALPHA, IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE, hdrFormat);\n\n\t\t// DARKWOLF_VOLUMETRIC_NATIVE_AA_ATTEMPT3\n\t\tif (r_hdr->integer)\n\t\t\ttr.volumetricFullresImage = R_CreateImage("*volumetricFullres", NULL, width, height, IMGTYPE_COLORALPHA, IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE, hdrFormat);\n\n\t\tif (r_shadowBlur->integer || r_hdr->integer)\n'''
i = rep(i, img_anchor, img_new, "create fullres volumetric HDR image")

h = rep(h,
'''\timage_t\t\t\t\t\t*screenScratchImage;\n\timage_t\t\t\t\t\t*textureScratchImage[2];\n''',
'''\timage_t\t\t\t\t\t*screenScratchImage;\n\timage_t                 *volumetricFullresImage; // DARKWOLF_VOLUMETRIC_NATIVE_AA_ATTEMPT3\n\timage_t\t\t\t\t\t*textureScratchImage[2];\n''',
"declare fullres volumetric image")

h = rep(h,
'''\tFBO_t\t\t\t\t\t*screenScratchFbo;\n\tFBO_t\t\t\t\t\t*textureScratchFbo[2];\n''',
'''\tFBO_t\t\t\t\t\t*screenScratchFbo;\n\tFBO_t                   *volumetricFullresFbo; // DARKWOLF_VOLUMETRIC_NATIVE_AA_ATTEMPT3\n\tFBO_t\t\t\t\t\t*textureScratchFbo[2];\n''',
"declare fullres volumetric FBO")

fbo_anchor = '''\tif (tr.screenScratchImage)\n\t{\n\t\ttr.screenScratchFbo = FBO_Create("screenScratch", tr.screenScratchImage->width, tr.screenScratchImage->height);\n\t\tFBO_AttachImage(tr.screenScratchFbo, tr.screenScratchImage, GL_COLOR_ATTACHMENT0, 0);\n\t\tFBO_AttachImage(tr.screenScratchFbo, tr.renderDepthImage, GL_DEPTH_ATTACHMENT, 0);\n\t\tR_CheckFBO(tr.screenScratchFbo);\n\t}\n\n'''
fbo_new = fbo_anchor + '''\t// DARKWOLF_VOLUMETRIC_NATIVE_AA_ATTEMPT3\n\tif (tr.volumetricFullresImage)\n\t{\n\t\ttr.volumetricFullresFbo = FBO_Create("_volumetricFullres", tr.volumetricFullresImage->width, tr.volumetricFullresImage->height);\n\t\tFBO_AttachImage(tr.volumetricFullresFbo, tr.volumetricFullresImage, GL_COLOR_ATTACHMENT0, 0);\n\t\tR_CheckFBO(tr.volumetricFullresFbo);\n\t}\n\n'''
f = rep(f, fbo_anchor, fbo_new, "create fullres volumetric FBO")

sun_anchor = '''// DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3\nstatic void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)\n{\n'''
sun_helper = r'''// DARKWOLF_VOLUMETRIC_NATIVE_AA_ATTEMPT3
// Final diagnostic candidate. Bit 0 = Local full-resolution reconstruction,
// bit 1 = Sun native full-resolution raymarch. Default 0 keeps exact v4.4.2 behavior.
#define VAA3_LOCAL 1
#define VAA3_SUN   2
static cvar_t *s_rVolumetricAAFinal;
static cvar_t *s_rVolumetricAAFinalTrace;
static unsigned int s_vaa3SunFull;
static unsigned int s_vaa3SunBase;
static unsigned int s_vaa3LocalFull;
static unsigned int s_vaa3LocalBase;

static void RB_VolumetricAA3EnsureCvars(void)
{
\tif (!s_rVolumetricAAFinal)
\t\ts_rVolumetricAAFinal = ri.Cvar_Get("r_volumetricAAFinal", "0", 0);
\tif (!s_rVolumetricAAFinalTrace)
\t\ts_rVolumetricAAFinalTrace = ri.Cvar_Get("r_volumetricAAFinalTrace", "0", 0);
}

static qboolean RB_VolumetricAA3Enabled(int bit)
{
\tRB_VolumetricAA3EnsureCvars();
\treturn (s_rVolumetricAAFinal && (s_rVolumetricAAFinal->integer & bit)) ? qtrue : qfalse;
}

// DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3
static void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)
{
'''.replace("\\t", "\t")
b = rep(b, sun_anchor, sun_helper, "insert Attempt3 controls")

sun_old = '''\ttr.volumetricSunPerfRaymarchThisFrame = 1; // DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3\n\tFBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricSunShader, params, 0);\n\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n'''
sun_new = '''\ttr.volumetricSunPerfRaymarchThisFrame = 1; // DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3\n\tRB_VolumetricAA3EnsureCvars();\n\tif (RB_VolumetricAA3Enabled(VAA3_SUN) && tr.volumetricFullresFbo)\n\t{\n\t\t// Native full-resolution raymarch: same shader, samples, PCF, jitter and energy.\n\t\t// Only raster/ray origin density changes from 1/2 x 1/2 to full resolution.\n\t\tFBO_Blit(srcFbo, srcBox, NULL, tr.volumetricFullresFbo, srcBox, &tr.volumetricSunShader, params, 0);\n\t\tFBO_Blit(tr.volumetricFullresFbo, srcBox, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t\ts_vaa3SunFull++;\n\t}\n\telse\n\t{\n\t\tFBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricSunShader, params, 0);\n\t\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t\ts_vaa3SunBase++;\n\t}\n'''
b = rep(b, sun_old, sun_new, "Sun native fullres raymarch")

local_branch = '''\t\tif (reconstructionMode == 3 && tr.screenScratchFbo && tr.volumetricLocalUpscaleShader.program)\n\t\t{\n\t\t\tvec4_t upscaleParams;\n\t\t\tVectorSet4(upscaleParams, Com_Clamp(0.0f, 64.0f, reconstructionDepthReject), 2.0f, 1.0f, 0.0f);\n\t\t\tGL_BindToTMU(tr.renderDepthImage, TB_NORMALMAP);\n\t\t\tGLSL_BindProgram(&tr.volumetricLocalUpscaleShader);\n\t\t\tGLSL_SetUniformVec4(&tr.volumetricLocalUpscaleShader, UNIFORM_VIEWINFO, viewInfo);\n\t\t\t// Full-resolution reconstruction output; raymarch remains quarter-resolution. screenScratchFbo is depth-detached.\n\t\t\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, tr.screenScratchFbo, srcBox, &tr.volumetricLocalUpscaleShader, upscaleParams, 0);\n\t\t\tFBO_Blit(tr.screenScratchFbo, srcBox, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t\t}\n\t\telse if (reconstructionMode > 0 && tr.quarterFbo[1] && tr.volumetricLocalUpscaleShader.program)\n'''
local_new = '''\t\tRB_VolumetricAA3EnsureCvars();\n\t\tif (RB_VolumetricAA3Enabled(VAA3_LOCAL) && tr.volumetricFullresFbo && tr.volumetricLocalUpscaleShader.program &&\n\t\t\t((mode >= 1 && mode <= 3) || reconstructionMode > 0))\n\t\t{\n\t\t\tvec4_t upscaleParams;\n\t\t\tfloat kernelMode = (reconstructionMode == 1) ? 1.0f : 2.0f;\n\t\t\t// Local point modes have no legacy reconstruction control; use the already validated 5x5 kernel.\n\t\t\t// Spotlight/Fire keep their selected 3x3/5x5 kernel and depth-reject value, changing output resolution only.\n\t\t\tVectorSet4(upscaleParams, Com_Clamp(0.0f, 64.0f, reconstructionDepthReject), kernelMode, 1.0f, 0.0f);\n\t\t\tGL_BindToTMU(tr.renderDepthImage, TB_NORMALMAP);\n\t\t\tGLSL_BindProgram(&tr.volumetricLocalUpscaleShader);\n\t\t\tGLSL_SetUniformVec4(&tr.volumetricLocalUpscaleShader, UNIFORM_VIEWINFO, viewInfo);\n\t\t\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, tr.volumetricFullresFbo, srcBox, &tr.volumetricLocalUpscaleShader, upscaleParams, 0);\n\t\t\tFBO_Blit(tr.volumetricFullresFbo, srcBox, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t\t\ts_vaa3LocalFull++;\n\t\t}\n\t\telse if (reconstructionMode == 3 && tr.screenScratchFbo && tr.volumetricLocalUpscaleShader.program)\n\t\t{\n\t\t\tvec4_t upscaleParams;\n\t\t\tVectorSet4(upscaleParams, Com_Clamp(0.0f, 64.0f, reconstructionDepthReject), 2.0f, 1.0f, 0.0f);\n\t\t\tGL_BindToTMU(tr.renderDepthImage, TB_NORMALMAP);\n\t\t\tGLSL_BindProgram(&tr.volumetricLocalUpscaleShader);\n\t\t\tGLSL_SetUniformVec4(&tr.volumetricLocalUpscaleShader, UNIFORM_VIEWINFO, viewInfo);\n\t\t\t// Exact accepted PC02 fallback.\n\t\t\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, tr.screenScratchFbo, srcBox, &tr.volumetricLocalUpscaleShader, upscaleParams, 0);\n\t\t\tFBO_Blit(tr.screenScratchFbo, srcBox, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t\t\ts_vaa3LocalBase++;\n\t\t}\n\t\telse if (reconstructionMode > 0 && tr.quarterFbo[1] && tr.volumetricLocalUpscaleShader.program)\n'''
b = rep(b, local_branch, local_new, "Local fullres reconstruction")

# Count remaining baseline Local composites without changing their behavior.
local_quarter = '''\t\telse\n\t\t{\n\t\t\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t\t}\n\t}\n\t// PC02 has no temporal accumulation/history; mode 3 changes reconstruction output resolution only.\n'''
local_quarter_new = '''\t\telse\n\t\t{\n\t\t\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t\t\ts_vaa3LocalBase++;\n\t\t}\n\t}\n\t// PC02 has no temporal accumulation/history; mode 3 changes reconstruction output resolution only.\n'''
b = rep(b, local_quarter, local_quarter_new, "count Local baseline")

# Also count the legacy quarter-reconstruction branch.
legacy_quarter_end = '''\t\t\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, tr.quarterFbo[1], NULL, &tr.volumetricLocalUpscaleShader, upscaleParams, 0);\n\t\t\tFBO_Blit(tr.quarterFbo[1], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t\t}\n'''
legacy_quarter_new = '''\t\t\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, tr.quarterFbo[1], NULL, &tr.volumetricLocalUpscaleShader, upscaleParams, 0);\n\t\t\tFBO_Blit(tr.quarterFbo[1], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t\t\ts_vaa3LocalBase++;\n\t\t}\n'''
b = rep(b, legacy_quarter_end, legacy_quarter_new, "count legacy Local reconstruction")

post_anchor = '''\tdstBox[0] = backEnd.viewParms.viewportX;\n'''
post_new = r'''\tRB_VolumetricAA3EnsureCvars();
\tif (s_rVolumetricAAFinalTrace && s_rVolumetricAAFinalTrace->integer)
\t{
\t\tstatic int lastTraceFrame = -1000000;
\t\tstatic int lastMode = -999;
\t\tint curMode = s_rVolumetricAAFinal ? s_rVolumetricAAFinal->integer : 0;
\t\tif (curMode != lastMode || tr.frameCount < lastTraceFrame || tr.frameCount - lastTraceFrame >= 30)
\t\t{
\t\t\tlastTraceFrame = tr.frameCount;
\t\t\tlastMode = curMode;
\t\t\tri.Printf(PRINT_ALL,
\t\t\t\t"VAA3_TRACE frame=%d map=%s mode=%d msaa=%d src=%s srcSize=%dx%d quarter=%dx%d fullres=%dx%d sunFull=%u sunBase=%u localFull=%u localBase=%u localMode=%d\n",
\t\t\t\ttr.frameCount, tr.world ? tr.world->baseName : "<none>", curMode,
\t\t\t\tr_ext_framebuffer_multisample ? r_ext_framebuffer_multisample->integer : 0,
\t\t\t\tsrcFbo ? srcFbo->name : "<null>", srcFbo ? srcFbo->width : 0, srcFbo ? srcFbo->height : 0,
\t\t\t\ttr.quarterFbo[0] ? tr.quarterFbo[0]->width : 0, tr.quarterFbo[0] ? tr.quarterFbo[0]->height : 0,
\t\t\t\ttr.volumetricFullresFbo ? tr.volumetricFullresFbo->width : 0, tr.volumetricFullresFbo ? tr.volumetricFullresFbo->height : 0,
\t\t\t\ts_vaa3SunFull, s_vaa3SunBase, s_vaa3LocalFull, s_vaa3LocalBase,
\t\t\t\tr_volumetricLocalMode ? r_volumetricLocalMode->integer : -1);
\t\t}
\t}

\tdstBox[0] = backEnd.viewParms.viewportX;
'''.replace("\\t", "\t")
b = rep(b, post_anchor, post_new, "Attempt3 telemetry")

for x in [MARK, "r_volumetricAAFinal", "VAA3_TRACE frame=", "volumetricFullresFbo", "s_vaa3SunFull++", "s_vaa3LocalFull++"]:
    if x not in b and x not in h and x not in i and x not in f:
        raise SystemExit("ERROR final marker missing: " + x)

B.write_text(b, encoding="utf-8", newline="\n")
I.write_text(i, encoding="utf-8", newline="\n")
F.write_text(f, encoding="utf-8", newline="\n")
H.write_text(h, encoding="utf-8", newline="\n")
print("DARKWOLF_VOLUMETRIC_NATIVE_AA_ATTEMPT3_PATCH_OK")
