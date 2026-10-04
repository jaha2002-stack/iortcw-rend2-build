#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('source')
BACKEND = ROOT / 'SP/code/rend2/tr_backend.c'
MARK = 'DARKWOLF_VOLUMETRIC_AA_DIAG_ATTEMPT1'


def fail(msg):
    raise SystemExit('Volumetric AA attempt1 patch error: ' + msg)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        fail(f'{label}: expected exactly one anchor, found {count}')
    return text.replace(old, new, 1)


text = BACKEND.read_text(encoding='utf-8')
if MARK in text:
    required = ['r_volumetricAAMode', 'r_volumetricAADepthReject', 'r_volumetricAAKernel',
                'r_volumetricAATrace', 'VAA_TRACE pass=', 'RB_VolumetricAAComposite',
                'VAA_PASS_LOCAL', 'VAA_PASS_SUN']
    missing = [x for x in required if x not in text]
    if missing:
        fail('already-applied source is incomplete: ' + ', '.join(missing))
    print('Volumetric AA attempt1 already applied')
    raise SystemExit(0)

for needle in ['DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3',
               'DARKWOLF_LOCAL_VOLUMETRIC_SPOTLIGHT_QUALITY_V0_4',
               'DARKWOLF_FIREVOL_SPATIAL_RECONSTRUCTION_EDGE_QUALITY_PC02',
               'tr.volumetricLocalUpscaleShader.program', 'tr.screenScratchFbo',
               's_rVolumetricFireDepthReject']:
    if needle not in text:
        fail('missing parent contract: ' + needle)

# Sun is earlier in this translation unit than the Local/Fire state block.
old_sun_decl = '''// DARKWOLF_SUN_VOLUMETRIC_V0_3\nstatic void RB_VolumetricSunPerfTrace(void)'''
new_sun_decl = '''// DARKWOLF_VOLUMETRIC_AA_DIAG_ATTEMPT1\n#define VAA_PASS_LOCAL 1\n#define VAA_PASS_SUN   2\nstatic void RB_VolumetricAAComposite(FBO_t *srcFbo, ivec4_t srcBox, const vec4_t viewInfo, int passBit, const char *passName);\n\n// DARKWOLF_SUN_VOLUMETRIC_V0_3\nstatic void RB_VolumetricSunPerfTrace(void)'''
text = replace_once(text, old_sun_decl, new_sun_decl, 'insert Sun-visible AA forward declaration')

# Diagnostic CVar storage: renderer-only. Mode=0 is byte-behavior-equivalent to v4.4.2.
old_decl = '''static cvar_t *s_rVolumetricFireUpscale;\nstatic cvar_t *s_rVolumetricFireDepthReject;\n\nstatic void RB_LocalVolumetricRenderEx'''
new_decl = '''static cvar_t *s_rVolumetricFireUpscale;\nstatic cvar_t *s_rVolumetricFireDepthReject;\n\n// DARKWOLF_VOLUMETRIC_AA_DIAG_ATTEMPT1\n// Bit 0 = Local point volumes (modes 1..3), bit 1 = Sun. Default 0 is exact v4.4.2 behavior.\nstatic cvar_t *s_rVolumetricAAMode;\nstatic cvar_t *s_rVolumetricAADepthReject;\nstatic cvar_t *s_rVolumetricAAKernel;\nstatic cvar_t *s_rVolumetricAATrace;\n\nstatic void RB_VolumetricAAEnsureCvars(void)\n{\n\tif (!s_rVolumetricAAMode)\n\t\ts_rVolumetricAAMode = ri.Cvar_Get("r_volumetricAAMode", "0", 0);\n\tif (!s_rVolumetricAADepthReject)\n\t\ts_rVolumetricAADepthReject = ri.Cvar_Get("r_volumetricAADepthReject", "4.0", 0);\n\tif (!s_rVolumetricAAKernel)\n\t\ts_rVolumetricAAKernel = ri.Cvar_Get("r_volumetricAAKernel", "2", 0);\n\tif (!s_rVolumetricAATrace)\n\t\ts_rVolumetricAATrace = ri.Cvar_Get("r_volumetricAATrace", "0", 0);\n}\n\nstatic qboolean RB_VolumetricAAEnabled(int passBit)\n{\n\tRB_VolumetricAAEnsureCvars();\n\treturn (s_rVolumetricAAMode && (s_rVolumetricAAMode->integer & passBit)) ? qtrue : qfalse;\n}\n\nstatic void RB_VolumetricAAComposite(FBO_t *srcFbo, ivec4_t srcBox, const vec4_t viewInfo, int passBit, const char *passName)\n{\n\tstatic int lastLocalTraceTime = -1000000;\n\tstatic int lastSunTraceTime = -1000000;\n\tint startMs, elapsedMs, now, *lastTraceTime;\n\tint kernelMode;\n\tfloat depthReject;\n\tqboolean enabled, reconstructReady, resolvedSource;\n\tconst char *pathName;\n\n\tRB_VolumetricAAEnsureCvars();\n\tenabled = RB_VolumetricAAEnabled(passBit);\n\tkernelMode = s_rVolumetricAAKernel ? (int)Com_Clamp(1.0f, 2.0f, (float)s_rVolumetricAAKernel->integer) : 2;\n\tdepthReject = s_rVolumetricAADepthReject ? Com_Clamp(0.0f, 64.0f, s_rVolumetricAADepthReject->value) : 4.0f;\n\treconstructReady = (enabled && tr.screenScratchFbo && tr.volumetricLocalUpscaleShader.program && tr.renderDepthImage) ? qtrue : qfalse;\n\tresolvedSource = (tr.msaaResolveFbo && srcFbo == tr.msaaResolveFbo) ? qtrue : qfalse;\n\tstartMs = ri.Milliseconds();\n\n\tif (reconstructReady)\n\t{\n\t\tvec4_t upscaleParams;\n\t\tVectorSet4(upscaleParams, depthReject, (float)kernelMode, 1.0f, (float)passBit);\n\t\tGL_BindToTMU(tr.renderDepthImage, TB_NORMALMAP);\n\t\tGLSL_BindProgram(&tr.volumetricLocalUpscaleShader);\n\t\tGLSL_SetUniformVec4(&tr.volumetricLocalUpscaleShader, UNIFORM_VIEWINFO, viewInfo);\n\t\t// Full-resolution, depth-guided reconstruction. Raymarch/shadow/energy remain byte-identical.\n\t\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, tr.screenScratchFbo, srcBox, &tr.volumetricLocalUpscaleShader, upscaleParams, 0);\n\t\tFBO_Blit(tr.screenScratchFbo, srcBox, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t\tpathName = "fullres-depth-aware";\n\t}\n\telse\n\t{\n\t\t// Exact accepted v4.4.2 composite path.\n\t\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n\t\tpathName = "baseline-quarter-direct";\n\t}\n\n\telapsedMs = ri.Milliseconds() - startMs;\n\tif (!s_rVolumetricAATrace || !s_rVolumetricAATrace->integer)\n\t\treturn;\n\tnow = backEnd.refdef.time;\n\tlastTraceTime = (passBit == VAA_PASS_SUN) ? &lastSunTraceTime : &lastLocalTraceTime;\n\tif (now - *lastTraceTime < 500)\n\t\treturn;\n\t*lastTraceTime = now;\n\n\tri.Printf(PRINT_ALL,\n\t\t"VAA_TRACE pass=%s bit=%d mode=%d enabled=%d ready=%d path=%s src=%s srcSize=%dx%d quarter=%dx%d scratch=%dx%d depth=%dx%d msaa=%d resolvedSource=%d kernel=%d depthReject=%.2f compositeMs=%d\\n",\n\t\tpassName ? passName : "unknown", passBit, s_rVolumetricAAMode ? s_rVolumetricAAMode->integer : 0,\n\t\tenabled ? 1 : 0, reconstructReady ? 1 : 0, pathName,\n\t\t(srcFbo && srcFbo->name) ? srcFbo->name : "<null>",\n\t\tsrcFbo ? srcFbo->width : 0, srcFbo ? srcFbo->height : 0,\n\t\ttr.quarterFbo[0] ? tr.quarterFbo[0]->width : 0, tr.quarterFbo[0] ? tr.quarterFbo[0]->height : 0,\n\t\ttr.screenScratchFbo ? tr.screenScratchFbo->width : 0, tr.screenScratchFbo ? tr.screenScratchFbo->height : 0,\n\t\ttr.renderDepthImage ? tr.renderDepthImage->width : 0, tr.renderDepthImage ? tr.renderDepthImage->height : 0,\n\t\tr_ext_framebuffer_multisample ? r_ext_framebuffer_multisample->integer : 0,\n\t\tresolvedSource ? 1 : 0, kernelMode, depthReject, elapsedMs);\n}\n\nstatic void RB_LocalVolumetricRenderEx'''
text = replace_once(text, old_decl, new_decl, 'insert AA diagnostics and composite helper')

# Sun raymarch stays identical; only quarter->full composite is switchable.
old_sun = '''\ttr.volumetricSunPerfRaymarchThisFrame = 1; // DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3\n\tFBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricSunShader, params, 0);\n\tFBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);\n}'''
new_sun = '''\ttr.volumetricSunPerfRaymarchThisFrame = 1; // DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3\n\tFBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricSunShader, params, 0);\n\tRB_VolumetricAAComposite(srcFbo, srcBox, viewInfo, VAA_PASS_SUN, "sun"); // DARKWOLF_VOLUMETRIC_AA_DIAG_ATTEMPT1\n}'''
text = replace_once(text, old_sun, new_sun, 'switchable Sun reconstruction')

# Local point modes 1..3 previously always used direct quarter composite. Spotlight/fire paths stay untouched.
old_local = '''\tFBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricLocalShader, params, 0);\n\t{\n\t\tint reconstructionMode = 0;'''
new_local = '''\tFBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricLocalShader, params, 0);\n\tif (mode >= 1 && mode <= 3)\n\t{\n\t\tRB_VolumetricAAComposite(srcFbo, srcBox, viewInfo, VAA_PASS_LOCAL, "local"); // DARKWOLF_VOLUMETRIC_AA_DIAG_ATTEMPT1\n\t\treturn;\n\t}\n\t{\n\t\tint reconstructionMode = 0;'''
text = replace_once(text, old_local, new_local, 'switchable Local point reconstruction')

for needle in ['DARKWOLF_FIREVOL_SPATIAL_RECONSTRUCTION_EDGE_QUALITY_PC02',
               'mode == 4 && r_volumetricLocalSpotUpscale && r_volumetricLocalSpotUpscale->integer',
               'mode >= 5 && mode <= 8 && s_rVolumetricFireUpscale',
               'DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3',
               'DARKWOLF_USLRD_PHYSICAL_SHADOW_GROUP_CONTINUITY_FIX_V2']:
    if nedle not in text:
        fail('accepted parent behavior lost: ' + needle)

BACKEND.write_text(text, encoding='utf-8', newline='\n')
print('DARKWOLF_VOLUMETRIC_AA_DIAG_ATTEMPT1_PATCH_OK')
