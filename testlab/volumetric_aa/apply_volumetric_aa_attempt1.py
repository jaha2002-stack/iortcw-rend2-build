#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('source')
BACKEND = ROOT / 'SP/code/rend2/tr_backend.c'
MARK = 'DARKWOLF_VOLUMETRIC_AA_ATTEMPT1'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'ERROR: {label}: expected exactly one anchor, found {n}')
    return text.replace(old, new, 1)


def require(text: str, needles, label: str) -> None:
    missing = [n for n in needles if n not in text]
    if missing:
        raise SystemExit(f'ERROR: {label}: missing contract: {missing}')


text = BACKEND.read_text(encoding='utf-8')
if MARK in text:
    require(text, [
        'r_volumetricAAResolve',
        'VAA_TRACE frame=',
        'RB_VolumetricAAFullResComposite',
        's_vaaSunReconCount',
        's_vaaLocalReconCount',
    ], 'already applied')
    print('Volumetric AA Attempt 1 already applied')
    raise SystemExit(0)

require(text, [
    'DARKWOLF_SUN_VOLUMETRIC_V0_3',
    'DARKWOLF_LOCAL_VOLUMETRIC_V0_1',
    'DARKWOLF_FIREVOL_SPATIAL_RECONSTRUCTION_EDGE_QUALITY_PC02',
    'tr.volumetricLocalUpscaleShader.program',
    'FBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);',
    'FBO_FastBlit(tr.renderFbo, NULL, tr.msaaResolveFbo, NULL, GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT, GL_NEAREST);',
], 'v4.4.2 renderer parent')

helper_anchor = '''// DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3\nstatic void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)\n{\n'''
helper = r'''// DARKWOLF_VOLUMETRIC_AA_ATTEMPT1
// Diagnostic-only A/B gate. This deliberately reuses the already validated
// Local/Fire depth-aware reconstruction shader instead of introducing a new
// beauty shader or changing any raymarch/shadow/light-selection math.
static cvar_t *s_rVolumetricAAResolve;
static cvar_t *s_rVolumetricAADepthReject;
static cvar_t *s_rVolumetricAATrace;
static unsigned int s_vaaSunReconCount;
static unsigned int s_vaaSunBaselineCount;
static unsigned int s_vaaLocalReconCount;
static unsigned int s_vaaLocalBaselineCount;

static void RB_VolumetricAAEnsureCvars(void)
{
    if (!s_rVolumetricAAResolve)
        s_rVolumetricAAResolve = ri.Cvar_Get("r_volumetricAAResolve", "0", 0);
    if (!s_rVolumetricAADepthReject)
        s_rVolumetricAADepthReject = ri.Cvar_Get("r_volumetricAADepthReject", "10.0", 0);
    if (!s_rVolumetricAATrace)
        s_rVolumetricAATrace = ri.Cvar_Get("r_volumetricAATrace", "0", 0);
}

static qboolean RB_VolumetricAAFullResComposite(FBO_t *srcFbo, ivec4_t srcBox, const vec4_t viewInfo)
{
    vec4_t upscaleParams;
    if (!srcFbo || !tr.quarterFbo[0] || !tr.screenScratchFbo || !tr.renderDepthImage ||
        !tr.volumetricLocalUpscaleShader.program)
        return qfalse;

    VectorSet4(upscaleParams,
        Com_Clamp(0.0f, 64.0f, s_rVolumetricAADepthReject ? s_rVolumetricAADepthReject->value : 10.0f),
        2.0f, 1.0f, 0.0f);
    GL_BindToTMU(tr.renderDepthImage, TB_NORMALMAP);
    GLSL_BindProgram(&tr.volumetricLocalUpscaleShader);
    GLSL_SetUniformVec4(&tr.volumetricLocalUpscaleShader, UNIFORM_VIEWINFO, viewInfo);
    FBO_Blit(tr.quarterFbo[0], NULL, NULL, tr.screenScratchFbo, srcBox,
        &tr.volumetricLocalUpscaleShader, upscaleParams, 0);
    FBO_Blit(tr.screenScratchFbo, srcBox, NULL, srcFbo, srcBox, NULL, NULL,
        GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);
    return qtrue;
}

// DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3
static void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)
{
'''
text = replace_once(text, helper_anchor, helper, 'insert VAA helpers')

sun_old = '''\ttr.volumetricSunPerfRaymarchThisFrame = 1; // DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3\n\tFBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricSunShader, params, 0);\n\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n'''
sun_new = '''\ttr.volumetricSunPerfRaymarchThisFrame = 1; // DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3\n\tFBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricSunShader, params, 0);\n\tRB_VolumetricAAEnsureCvars();\n\tif ((s_rVolumetricAAResolve->integer & 2) && RB_VolumetricAAFullResComposite(srcFbo, srcBox, viewInfo))\n\t{\n\t\ts_vaaSunReconCount++;\n\t}\n\telse\n\t{\n\t\ts_vaaSunBaselineCount++;\n\t\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t}\n'''
text = replace_once(text, sun_old, sun_new, 'Sun A/B composite')

local_blit_old = '''\tFBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricLocalShader, params, 0);\n\t{\n\t\tint reconstructionMode = 0;\n\t\tfloat reconstructionDepthReject = 10.0f;\n'''
local_blit_new = '''\tRB_VolumetricAAEnsureCvars();\n\tFBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricLocalShader, params, 0);\n\t{\n\t\tint reconstructionMode = 0;\n\t\tfloat reconstructionDepthReject = 10.0f;\n'''
text = replace_once(text, local_blit_old, local_blit_new, 'Local ensure cvars')

local_mode_anchor = '''\t\tif (reconstructionMode == 3 && tr.screenScratchFbo && tr.volumetricLocalUpscaleShader.program)\n'''
local_mode_insert = '''\t\t// DARKWOLF_VOLUMETRIC_AA_ATTEMPT1: production Local Mode 5 reaches this function as mode 3.\n\t\t// Apply the already-proven full-resolution depth-aware reconstruction only to point-lamp modes.\n\t\tif (mode >= 1 && mode <= 3)\n\t\t{\n\t\t\tif (s_rVolumetricAAResolve->integer & 1)\n\t\t\t{\n\t\t\t\treconstructionMode = 3;\n\t\t\t\treconstructionDepthReject = s_rVolumetricAADepthReject ? s_rVolumetricAADepthReject->value : 10.0f;\n\t\t\t\ts_vaaLocalReconCount++;\n\t\t\t}\n\t\t\telse\n\t\t\t{\n\t\t\t\ts_vaaLocalBaselineCount++;\n\t\t\t}\n\t\t}\n\n\t\tif (reconstructionMode == 3 && tr.screenScratchFbo && tr.volumetricLocalUpscaleShader.program)\n'''
text = replace_once(text, local_mode_anchor, local_mode_insert, 'Local production mode reconstruction')

post_anchor = '''\tdstBox[0] = backEnd.viewParms.viewportX;\n'''
post_insert = r'''	RB_VolumetricAAEnsureCvars();
	if (s_rVolumetricAATrace && s_rVolumetricAATrace->integer)
	{
		static int s_vaaLastTraceFrame = -1000000;
		if (tr.frameCount < s_vaaLastTraceFrame || tr.frameCount - s_vaaLastTraceFrame >= 10)
		{
			s_vaaLastTraceFrame = tr.frameCount;
			ri.Printf(PRINT_ALL,
				"VAA_TRACE frame=%d map=%s resolve=%d depthReject=%.2f msaaRequested=%d msaaResolveFbo=%d src=%s srcSize=%dx%d render=%dx%d quarter=%dx%d depth=%dx%d scratch=%dx%d sun=%d local=%d localMode=%d sunRecon=%u sunBase=%u localRecon=%u localBase=%u\n",
				tr.frameCount, tr.world ? tr.world->baseName : "<none>",
				s_rVolumetricAAResolve ? s_rVolumetricAAResolve->integer : 0,
				s_rVolumetricAADepthReject ? s_rVolumetricAADepthReject->value : 0.0f,
				r_ext_framebuffer_multisample ? r_ext_framebuffer_multisample->integer : 0,
				tr.msaaResolveFbo ? 1 : 0,
				srcFbo ? srcFbo->name : "<null>",
				srcFbo ? srcFbo->width : 0, srcFbo ? srcFbo->height : 0,
				tr.renderFbo ? tr.renderFbo->width : 0, tr.renderFbo ? tr.renderFbo->height : 0,
				tr.quarterFbo[0] ? tr.quarterFbo[0]->width : 0, tr.quarterFbo[0] ? tr.quarterFbo[0]->height : 0,
				tr.renderDepthImage ? tr.renderDepthImage->width : 0, tr.renderDepthImage ? tr.renderDepthImage->height : 0,
				tr.screenScratchFbo ? tr.screenScratchFbo->width : 0, tr.screenScratchFbo ? tr.screenScratchFbo->height : 0,
				r_volumetricSun ? r_volumetricSun->integer : 0,
				r_volumetricLocal ? r_volumetricLocal->integer : 0,
				r_volumetricLocalMode ? r_volumetricLocalMode->integer : -1,
				s_vaaSunReconCount, s_vaaSunBaselineCount, s_vaaLocalReconCount, s_vaaLocalBaselineCount);
		}
	}

	dstBox[0] = backEnd.viewParms.viewportX;
'''
text = replace_once(text, post_anchor, post_insert, 'postprocess telemetry')

require(text, [
    MARK,
    'r_volumetricAAResolve',
    'r_volumetricAADepthReject',
    'VAA_TRACE frame=',
    's_vaaSunReconCount++',
    's_vaaLocalReconCount++',
    'if (mode >= 1 && mode <= 3)',
    's_rVolumetricAAResolve->integer & 2',
], 'patched renderer')

if '\r' in text:
    raise SystemExit('ERROR: CR byte introduced')
BACKEND.write_text(text, encoding='utf-8', newline='\n')
print('DARKWOLF_VOLUMETRIC_AA_ATTEMPT1_PATCH_OK')
