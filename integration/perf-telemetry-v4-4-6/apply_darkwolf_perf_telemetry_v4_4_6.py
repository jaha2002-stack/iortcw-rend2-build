#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source")
RD = ROOT / "SP/code/rend2"
MARK = "DARKWOLF_V446_FULL_PERF_TELEMETRY_V01"

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8", newline="\n")

def one(rel, old, new, label):
    s = read(rel)
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"ERROR {label}: expected 1 anchor, found {n} in {rel}")
    write(rel, s.replace(old, new, 1))

def require(rel, markers, label):
    s = read(rel)
    missing = [m for m in markers if m not in s]
    if missing:
        raise SystemExit(f"ERROR {label}: missing {missing}")

require("SP/code/rend2/tr_scene.c", [
    "DARKWOLF_FORCE_SUN_CSM_SMART_PRODUCTION_V444",
    "R_StaticPromoteFrame(fd);",
    "R_RenderDlightCubemaps(fd);",
], "v4.4.6 renderer production contract")
require("SP/code/rend2/tr_main.c", [
    "REND2_DLIGHT_FINAL_V6",
    "DARKWOLF_STAGE11_UNIFIED_ASSET_SHADOW_COVERAGE_CLEAN_PRODUCTION_V1",
    "void R_RenderDlightCubemaps(const refdef_t *fd)",
], "dlight shadow contract")
require("SP/code/rend2/tr_backend.c", [
    "RB_VolumetricSun(srcFbo, srcBox)",
    "RB_VolumetricLocal(srcFbo, srcBox)",
    "RB_VolumetricFire(srcFbo, srcBox)",
    "REND2_GI_2_V1_SCREEN_SPACE_LOCAL_INDIRECT",
], "postprocess contract")

# ---------------------------------------------------------------------------
# Shared diagnostic declarations. This build is intentionally telemetry-only.
# ---------------------------------------------------------------------------
one(
    "SP/code/rend2/tr_local.h",
    """} backEndCounters_t;

// all state modified by the back end is separated
""",
    """} backEndCounters_t;

// DARKWOLF_V446_FULL_PERF_TELEMETRY_V01
typedef enum {
    DWPERF_DLIGHT_SHADOW = 0,
    DWPERF_SUN_SHADOW,
    DWPERF_FIRE_SHADOW,
    DWPERF_OTHER_SHADOW,
    DWPERF_SHADOW_CAPTURE,
    DWPERF_DEPTH_PREPASS,
    DWPERF_MAIN_DRAW,
    DWPERF_MSAA_RESOLVE,
    DWPERF_SSAO,
    DWPERF_SSGI,
    DWPERF_VOLUMETRIC_SUN,
    DWPERF_VOLUMETRIC_LOCAL,
    DWPERF_VOLUMETRIC_FIRE,
    DWPERF_TONEMAP,
    DWPERF_SUNRAYS,
    DWPERF_BOKEH,
    DWPERF_FINAL_BLIT,
    DWPERF_POST_TOTAL,
    DWPERF_STAGE_COUNT
} dwPerfStage_t;

extern int dwPerfProbeFrame;
extern int dwPerfStageMs[DWPERF_STAGE_COUNT];
extern int dwPerfStageCalls[DWPERF_STAGE_COUNT];
extern int dwPerfViewGenMs;
extern int dwPerfViewSortMs;
extern int dwPerfStaticPromoteMs;
extern int dwPerfDlightShadowFrontMs;
extern int dwPerfRenderViewCalls;
extern int dwPerfMainViewCalls;
extern int dwPerfShadowViewCalls;
extern int dwPerfDlightShadowViewCalls;
extern int dwPerfSunShadowViewCalls;
extern int dwPerfFireShadowViewCalls;
extern int dwPerfOtherShadowViewCalls;
extern int dwPerfDlightShadowFaces;
extern int dwPerfFboBindCalls;
extern int dwPerfFboBindChanges;
extern int dwPerfBlitCalls;
extern int dwPerfFastBlitCalls;
extern frontEndCounters_t dwPerfFrontSnapshot;

void DWPerfResetFrameCounters(void);
void DWPerfStageBegin(int stage);
void DWPerfStageEnd(int stage);

// all state modified by the back end is separated
""",
    "install telemetry declarations",
)

# ---------------------------------------------------------------------------
# Per-frame telemetry and CPU/backend counters.
# ---------------------------------------------------------------------------
one(
    "SP/code/rend2/tr_cmds.c",
    '#include "tr_local.h"\n',
    '''#include "tr_local.h"

// DARKWOLF_V446_FULL_PERF_TELEMETRY_V01
int dwPerfProbeFrame;
int dwPerfStageMs[DWPERF_STAGE_COUNT];
int dwPerfStageCalls[DWPERF_STAGE_COUNT];
int dwPerfViewGenMs;
int dwPerfViewSortMs;
int dwPerfStaticPromoteMs;
int dwPerfDlightShadowFrontMs;
int dwPerfRenderViewCalls;
int dwPerfMainViewCalls;
int dwPerfShadowViewCalls;
int dwPerfDlightShadowViewCalls;
int dwPerfSunShadowViewCalls;
int dwPerfFireShadowViewCalls;
int dwPerfOtherShadowViewCalls;
int dwPerfDlightShadowFaces;
int dwPerfFboBindCalls;
int dwPerfFboBindChanges;
int dwPerfBlitCalls;
int dwPerfFastBlitCalls;
frontEndCounters_t dwPerfFrontSnapshot;

void DWPerfResetFrameCounters(void)
{
    dwPerfProbeFrame = (tr.frameCount > 0 && (tr.frameCount % 240) == 0) ? 1 : 0;
    Com_Memset(dwPerfStageMs, 0, sizeof(dwPerfStageMs));
    Com_Memset(dwPerfStageCalls, 0, sizeof(dwPerfStageCalls));
    dwPerfViewGenMs = 0;
    dwPerfViewSortMs = 0;
    dwPerfStaticPromoteMs = 0;
    dwPerfDlightShadowFrontMs = 0;
    dwPerfRenderViewCalls = 0;
    dwPerfMainViewCalls = 0;
    dwPerfShadowViewCalls = 0;
    dwPerfDlightShadowViewCalls = 0;
    dwPerfSunShadowViewCalls = 0;
    dwPerfFireShadowViewCalls = 0;
    dwPerfOtherShadowViewCalls = 0;
    dwPerfDlightShadowFaces = 0;
    dwPerfFboBindCalls = 0;
    dwPerfFboBindChanges = 0;
    dwPerfBlitCalls = 0;
    dwPerfFastBlitCalls = 0;
}

''',
    "install telemetry globals",
)

one(
    "SP/code/rend2/tr_cmds.c",
    """void R_PerformanceCounters( void ) {
	if ( !r_speeds->integer ) {
""",
    """void R_PerformanceCounters( void ) {
	// DARKWOLF_V446_FULL_PERF_TELEMETRY_V01: preserve front-end counters before the legacy reset.
	dwPerfFrontSnapshot = tr.pc;
	if ( !r_speeds->integer ) {
""",
    "snapshot frontend counters",
)

one(
    "SP/code/rend2/tr_cmds.c",
    """	tr.frameCount++;
	tr.frameSceneNum = 0;
""",
    """	tr.frameCount++;
	tr.frameSceneNum = 0;
	DWPerfResetFrameCounters();
""",
    "reset telemetry at frame start",
)

one(
    "SP/code/rend2/tr_cmds.c",
    """	R_IssueRenderCommands( qtrue );

	R_InitNextFrame();

	if ( frontEndMsec ) {
""",
    """	R_IssueRenderCommands( qtrue );

	// DARKWOLF_V446_FULL_PERF_TELEMETRY_V01
	{
		static int dwLastEndMs;
		static int dwLastCfgFrame = -1000000;
		int nowMs = ri.Milliseconds();
		int wallMs = dwLastEndMs ? nowMs - dwLastEndMs : 0;
		const char *mapName = (tr.world && tr.world->baseName[0]) ? tr.world->baseName : "none";
		dwLastEndMs = nowMs;

		if ((tr.frameCount & 7) == 0 || dwPerfProbeFrame)
		{
			ri.Printf(PRINT_ALL,
			"DWPERF_FRAME frame=%d map=%s probe=%d wall_ms=%d frontend_ms=%d backend_ms=%d "
			"views=%d main_views=%d shadow_views=%d dshadow_views=%d sunshadow_views=%d fireshadow_views=%d othershadow_views=%d "
			"viewgen_ms=%d sort_ms=%d staticpromote_ms=%d dshadow_front_ms=%d dshadow_faces=%d "
			"entities=%d dlights=%d drawsurfs=%d leafs=%d dlight_surfs=%d dlight_culled=%d "
			"be_surfs=%d batches=%d verts=%d indexes=%d vao_binds=%d static_draws=%d dynamic_draws=%d "
			"glsl_binds=%d generic=%d lightall=%d fog=%d dlightdraw=%d "
			"fbo_calls=%d fbo_changes=%d blits=%d fastblits=%d\\n",
			tr.frameCount, mapName, dwPerfProbeFrame, wallMs, tr.frontEndMsec, backEnd.pc.msec,
			dwPerfRenderViewCalls, dwPerfMainViewCalls, dwPerfShadowViewCalls,
			dwPerfDlightShadowViewCalls, dwPerfSunShadowViewCalls, dwPerfFireShadowViewCalls, dwPerfOtherShadowViewCalls,
			dwPerfViewGenMs, dwPerfViewSortMs, dwPerfStaticPromoteMs, dwPerfDlightShadowFrontMs, dwPerfDlightShadowFaces,
			tr.refdef.num_entities, tr.refdef.num_dlights, tr.refdef.numDrawSurfs,
			dwPerfFrontSnapshot.c_leafs, dwPerfFrontSnapshot.c_dlightSurfaces, dwPerfFrontSnapshot.c_dlightSurfacesCulled,
			backEnd.pc.c_surfaces, backEnd.pc.c_surfBatches, backEnd.pc.c_vertexes, backEnd.pc.c_indexes,
			backEnd.pc.c_vaoBinds, backEnd.pc.c_staticVaoDraws, backEnd.pc.c_dynamicVaoDraws,
			backEnd.pc.c_glslShaderBinds, backEnd.pc.c_genericDraws, backEnd.pc.c_lightallDraws,
			backEnd.pc.c_fogDraws, backEnd.pc.c_dlightDraws,
			dwPerfFboBindCalls, dwPerfFboBindChanges, dwPerfBlitCalls, dwPerfFastBlitCalls);
		}

		if (dwPerfProbeFrame)
		{
			ri.Printf(PRINT_ALL,
				"DWPERF_PROBE frame=%d map=%s "
				"dshadow_ms=%d dshadow_calls=%d sunshadow_ms=%d sunshadow_calls=%d fireshadow_ms=%d fireshadow_calls=%d "
				"othershadow_ms=%d othershadow_calls=%d shadowcapture_ms=%d shadowcapture_calls=%d "
				"depth_ms=%d depth_calls=%d main_ms=%d main_calls=%d msaa_ms=%d msaa_calls=%d "
				"ssao_ms=%d ssao_calls=%d ssgi_ms=%d ssgi_calls=%d volsun_ms=%d volsun_calls=%d "
				"vollocal_ms=%d vollocal_calls=%d volfire_ms=%d volfire_calls=%d "
				"tonemap_ms=%d tonemap_calls=%d sunrays_ms=%d sunrays_calls=%d bokeh_ms=%d bokeh_calls=%d "
				"finalblit_ms=%d finalblit_calls=%d post_ms=%d post_calls=%d\\n",
				tr.frameCount, mapName,
				dwPerfStageMs[DWPERF_DLIGHT_SHADOW], dwPerfStageCalls[DWPERF_DLIGHT_SHADOW],
				dwPerfStageMs[DWPERF_SUN_SHADOW], dwPerfStageCalls[DWPERF_SUN_SHADOW],
				dwPerfStageMs[DWPERF_FIRE_SHADOW], dwPerfStageCalls[DWPERF_FIRE_SHADOW],
				dwPerfStageMs[DWPERF_OTHER_SHADOW], dwPerfStageCalls[DWPERF_OTHER_SHADOW],
				dwPerfStageMs[DWPERF_SHADOW_CAPTURE], dwPerfStageCalls[DWPERF_SHADOW_CAPTURE],
				dwPerfStageMs[DWPERF_DEPTH_PREPASS], dwPerfStageCalls[DWPERF_DEPTH_PREPASS],
				dwPerfStageMs[DWPERF_MAIN_DRAW], dwPerfStageCalls[DWPERF_MAIN_DRAW],
				dwPerfStageMs[DWPERF_MSAA_RESOLVE], dwPerfStageCalls[DWPERF_MSAA_RESOLVE],
				dwPerfStageMs[DWPERF_SSAO], dwPerfStageCalls[DWPERF_SSAO],
				dwPerfStageMs[DWPERF_SSGI], dwPerfStageCalls[DWPERF_SSGI],
				dwPerfStageMs[DWPERF_VOLUMETRIC_SUN], dwPerfStageCalls[DWPERF_VOLUMETRIC_SUN],
				dwPerfStageMs[DWPERF_VOLUMETRIC_LOCAL], dwPerfStageCalls[DWPERF_VOLUMETRIC_LOCAL],
				dwPerfStageMs[DWPERF_VOLUMETRIC_FIRE], dwPerfStageCalls[DWPERF_VOLUMETRIC_FIRE],
				dwPerfStageMs[DWPERF_TONEMAP], dwPerfStageCalls[DWPERF_TONEMAP],
				dwPerfStageMs[DWPERF_SUNRAYS], dwPerfStageCalls[DWPERF_SUNRAYS],
				dwPerfStageMs[DWPERF_BOKEH], dwPerfStageCalls[DWPERF_BOKEH],
				dwPerfStageMs[DWPERF_FINAL_BLIT], dwPerfStageCalls[DWPERF_FINAL_BLIT],
				dwPerfStageMs[DWPERF_POST_TOTAL], dwPerfStageCalls[DWPERF_POST_TOTAL]);
		}

		if (tr.frameCount < dwLastCfgFrame || tr.frameCount - dwLastCfgFrame >= 300)
		{
			dwLastCfgFrame = tr.frameCount;
			ri.Printf(PRINT_ALL,
				"DWPERF_CFG frame=%d map=%s size=%dx%d hdr=%d msaa=%d depthpre=%d post=%d "
				"forcesun=%d sunlight=%d shadowmap=%d shadowfilter=%d dlightmode=%d dlightmapsize=%d "
				"volsun=%d vollocal=%d vollocalmode=%d ssgi=%d ssao=%d sunrays=%d "
				"staticmax=%d dshadowmax=%d pbr=%d swap=%d maxfps=%d\\n",
				tr.frameCount, mapName, glConfig.vidWidth, glConfig.vidHeight,
				ri.Cvar_VariableIntegerValue("r_hdr"),
				ri.Cvar_VariableIntegerValue("r_ext_framebuffer_multisample"),
				ri.Cvar_VariableIntegerValue("r_depthPrepass"),
				ri.Cvar_VariableIntegerValue("r_postProcess"),
				ri.Cvar_VariableIntegerValue("r_forceSun"),
				ri.Cvar_VariableIntegerValue("r_sunlightMode"),
				ri.Cvar_VariableIntegerValue("r_shadowMapSize"),
				ri.Cvar_VariableIntegerValue("r_shadowFilter"),
				ri.Cvar_VariableIntegerValue("r_dlightMode"),
				ri.Cvar_VariableIntegerValue("r_dlightShadowMapSize"),
				ri.Cvar_VariableIntegerValue("r_volumetricSun"),
				ri.Cvar_VariableIntegerValue("r_volumetricLocal"),
				ri.Cvar_VariableIntegerValue("r_volumetricLocalMode"),
				ri.Cvar_VariableIntegerValue("r_ssgi"),
				ri.Cvar_VariableIntegerValue("r_ssao"),
				ri.Cvar_VariableIntegerValue("r_drawSunRays"),
				ri.Cvar_VariableIntegerValue("r_staticPromoteMaxLights"),
				ri.Cvar_VariableIntegerValue("r_dlightShadowMaxLights"),
				ri.Cvar_VariableIntegerValue("r_pbr"),
				ri.Cvar_VariableIntegerValue("r_swapInterval"),
				ri.Cvar_VariableIntegerValue("com_maxfps"));
		}
	}

	R_InitNextFrame();

	if ( frontEndMsec ) {
""",
    "emit telemetry at frame end",
)

# ---------------------------------------------------------------------------
# Front-end view generation/sorting and shadow-view classification.
# ---------------------------------------------------------------------------
one(
    "SP/code/rend2/tr_main.c",
    """void R_RenderView( viewParms_t *parms ) {
	int firstDrawSurf;
	int numDrawSurfs;
""",
    """void R_RenderView( viewParms_t *parms ) {
	int firstDrawSurf;
	int numDrawSurfs;
	int dwPerfStart;

	// DARKWOLF_V446_FULL_PERF_TELEMETRY_V01
	dwPerfRenderViewCalls++;
	if (parms->flags & VPF_DEPTHSHADOW)
	{
		int c, classified = 0;
		dwPerfShadowViewCalls++;
		if (parms->targetFbo == tr.dlightShadowFbo)
		{
			dwPerfDlightShadowViewCalls++;
			classified = 1;
		}
		if (parms->targetFbo == tr.fireVolumetricSyntheticShadowFbo)
		{
			dwPerfFireShadowViewCalls++;
			classified = 1;
		}
		for (c = 0; c < 4; ++c)
		{
			if (parms->targetFbo == tr.sunShadowFbo[c])
			{
				dwPerfSunShadowViewCalls++;
				classified = 1;
				break;
			}
		}
		if (!classified)
			dwPerfOtherShadowViewCalls++;
	}
	else
	{
		dwPerfMainViewCalls++;
	}
""",
    "instrument R_RenderView header",
)

one(
    "SP/code/rend2/tr_main.c",
    """	R_GenerateDrawSurfs();

	// if we overflowed MAX_DRAWSURFS""",
    """	dwPerfStart = ri.Milliseconds();
	R_GenerateDrawSurfs();
	dwPerfViewGenMs += ri.Milliseconds() - dwPerfStart;

	// if we overflowed MAX_DRAWSURFS""",
    "measure draw-surface generation",
)

one(
    "SP/code/rend2/tr_main.c",
    """	R_SortDrawSurfs( tr.refdef.drawSurfs + firstDrawSurf, numDrawSurfs - firstDrawSurf );

	// draw main system development information""",
    """	dwPerfStart = ri.Milliseconds();
	R_SortDrawSurfs( tr.refdef.drawSurfs + firstDrawSurf, numDrawSurfs - firstDrawSurf );
	dwPerfViewSortMs += ri.Milliseconds() - dwPerfStart;

	// draw main system development information""",
    "measure draw-surface sorting",
)

one(
    "SP/code/rend2/tr_main.c",
    """		tr.refdef.dlightDiagFacesIssued += 6;
""",
    """		tr.refdef.dlightDiagFacesIssued += 6;
		dwPerfDlightShadowFaces += 6; // DARKWOLF_V446_FULL_PERF_TELEMETRY_V01
""",
    "count point-light shadow faces",
)

# ---------------------------------------------------------------------------
# Measure the two production front-end systems most likely to dominate CPU.
# ---------------------------------------------------------------------------
one(
    "SP/code/rend2/tr_scene.c",
    """	R_StaticPromoteFrame(fd);

	RE_BeginScene(fd);""",
    """	// DARKWOLF_V446_FULL_PERF_TELEMETRY_V01
	{
		int dwPerfStart = ri.Milliseconds();
		R_StaticPromoteFrame(fd);
		dwPerfStaticPromoteMs += ri.Milliseconds() - dwPerfStart;
	}

	RE_BeginScene(fd);""",
    "measure StaticPromote",
)

one(
    "SP/code/rend2/tr_scene.c",
    """	{
		R_RenderDlightCubemaps(fd);
	}
	// DARKWOLF_FIREVOL_OCCLUSION_PRODUCTION_V1""",
    """	{
		int dwPerfStart = ri.Milliseconds();
		R_RenderDlightCubemaps(fd);
		dwPerfDlightShadowFrontMs += ri.Milliseconds() - dwPerfStart;
	}
	// DARKWOLF_FIREVOL_OCCLUSION_PRODUCTION_V1""",
    "measure dlight shadow frontend",
)

# ---------------------------------------------------------------------------
# Count framebuffer traffic.
# ---------------------------------------------------------------------------
one(
    "SP/code/rend2/tr_fbo.c",
    """void FBO_BlitFromTexture(struct image_s *src, vec4_t inSrcTexCorners, vec2_t inSrcTexScale, FBO_t *dst, ivec4_t inDstBox, struct shaderProgram_s *shaderProgram, vec4_t inColor, int blend)
{
	ivec4_t dstBox;""",
    """void FBO_BlitFromTexture(struct image_s *src, vec4_t inSrcTexCorners, vec2_t inSrcTexScale, FBO_t *dst, ivec4_t inDstBox, struct shaderProgram_s *shaderProgram, vec4_t inColor, int blend)
{
	ivec4_t dstBox;
	dwPerfBlitCalls++; // DARKWOLF_V446_FULL_PERF_TELEMETRY_V01""",
    "count texture blits",
)

one(
    "SP/code/rend2/tr_fbo.c",
    """void FBO_FastBlit(FBO_t *src, ivec4_t srcBox, FBO_t *dst, ivec4_t dstBox, int buffers, int filter)
{
	ivec4_t srcBoxFinal, dstBoxFinal;""",
    """void FBO_FastBlit(FBO_t *src, ivec4_t srcBox, FBO_t *dst, ivec4_t dstBox, int buffers, int filter)
{
	ivec4_t srcBoxFinal, dstBoxFinal;
	dwPerfFastBlitCalls++; // DARKWOLF_V446_FULL_PERF_TELEMETRY_V01""",
    "count fast blits",
)

one(
    "SP/code/rend2/tr_fbo.c",
    """void FBO_Bind(FBO_t * fbo)
{
	if (!glRefConfig.framebufferObject)""",
    """void FBO_Bind(FBO_t * fbo)
{
	dwPerfFboBindCalls++; // DARKWOLF_V446_FULL_PERF_TELEMETRY_V01
	if (!glRefConfig.framebufferObject)""",
    "count FBO bind calls",
)

one(
    "SP/code/rend2/tr_fbo.c",
    """	if (glState.currentFBO == fbo)
		return;
		
	if (r_logFile->integer)""",
    """	if (glState.currentFBO == fbo)
		return;

	dwPerfFboBindChanges++; // DARKWOLF_V446_FULL_PERF_TELEMETRY_V01
		
	if (r_logFile->integer)""",
    "count actual FBO changes",
)

# ---------------------------------------------------------------------------
# Sparse serialized GPU probes. Probe frames are explicitly marked and must
# never be mixed with normal-frame FPS statistics.
# ---------------------------------------------------------------------------
one(
    "SP/code/rend2/tr_backend.c",
    '#include "tr_local.h"\n',
    '''#include "tr_local.h"

// DARKWOLF_V446_FULL_PERF_TELEMETRY_V01
static int s_dwPerfStageStart[DWPERF_STAGE_COUNT];

void DWPerfStageBegin(int stage)
{
	if (!dwPerfProbeFrame || stage < 0 || stage >= DWPERF_STAGE_COUNT)
		return;
	qglFinish();
	s_dwPerfStageStart[stage] = ri.Milliseconds();
}

void DWPerfStageEnd(int stage)
{
	int now;
	if (!dwPerfProbeFrame || stage < 0 || stage >= DWPERF_STAGE_COUNT)
		return;
	qglFinish();
	now = ri.Milliseconds();
	dwPerfStageMs[stage] += now - s_dwPerfStageStart[stage];
	dwPerfStageCalls[stage]++;
}

''',
    "install serialized probe helpers",
)

one(
    "SP/code/rend2/tr_backend.c",
    """	const drawSurfsCommand_t	*cmd;
	qboolean isShadowView;
""",
    """	const drawSurfsCommand_t	*cmd;
	qboolean isShadowView;
	int dwPerfShadowStage = -1;
""",
    "shadow stage local",
)

one(
    "SP/code/rend2/tr_backend.c",
    """	isShadowView = !!(backEnd.viewParms.flags & VPF_DEPTHSHADOW);

	// clear the z buffer, set the modelview, etc""",
    """	isShadowView = !!(backEnd.viewParms.flags & VPF_DEPTHSHADOW);

	if (isShadowView)
	{
		int c;
		if (backEnd.viewParms.targetFbo == tr.dlightShadowFbo)
			dwPerfShadowStage = DWPERF_DLIGHT_SHADOW;
		else if (backEnd.viewParms.targetFbo == tr.fireVolumetricSyntheticShadowFbo)
			dwPerfShadowStage = DWPERF_FIRE_SHADOW;
		else
		{
			for (c = 0; c < 4; ++c)
				if (backEnd.viewParms.targetFbo == tr.sunShadowFbo[c])
				{
					dwPerfShadowStage = DWPERF_SUN_SHADOW;
					break;
				}
			if (dwPerfShadowStage < 0)
				dwPerfShadowStage = DWPERF_OTHER_SHADOW;
		}
		DWPerfStageBegin(dwPerfShadowStage);
	}

	// clear the z buffer, set the modelview, etc""",
    "classify backend shadow views",
)

one(
    "SP/code/rend2/tr_backend.c",
    """		backEnd.depthFill = qtrue;
		qglColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE);
		RB_RenderDrawSurfList( cmd->drawSurfs, cmd->numDrawSurfs );
		qglColorMask(!backEnd.colorMask[0], !backEnd.colorMask[1], !backEnd.colorMask[2], !backEnd.colorMask[3]);""",
    """		backEnd.depthFill = qtrue;
		qglColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE);
		if (!isShadowView) DWPerfStageBegin(DWPERF_DEPTH_PREPASS);
		RB_RenderDrawSurfList( cmd->drawSurfs, cmd->numDrawSurfs );
		if (!isShadowView) DWPerfStageEnd(DWPERF_DEPTH_PREPASS);
		qglColorMask(!backEnd.colorMask[0], !backEnd.colorMask[1], !backEnd.colorMask[2], !backEnd.colorMask[3]);""",
    "probe depth prepass",
)

one(
    "SP/code/rend2/tr_backend.c",
    """	if (!isShadowView)
	{
		RB_RenderDrawSurfList( cmd->drawSurfs, cmd->numDrawSurfs );

		if (r_drawSun->integer)""",
    """	if (!isShadowView)
	{
		DWPerfStageBegin(DWPERF_MAIN_DRAW);
		RB_RenderDrawSurfList( cmd->drawSurfs, cmd->numDrawSurfs );
		DWPerfStageEnd(DWPERF_MAIN_DRAW);

		if (r_drawSun->integer)""",
    "probe main draw",
)

one(
    "SP/code/rend2/tr_backend.c",
    """	backEnd.viewParms.isMirror = qfalse;
	backEnd.viewParms.flags = 0;

	return (const void *)(cmd + 1);
}


/*
=============
RB_DrawBuffer""",
    """	backEnd.viewParms.isMirror = qfalse;
	backEnd.viewParms.flags = 0;

	if (dwPerfShadowStage >= 0)
		DWPerfStageEnd(dwPerfShadowStage);

	return (const void *)(cmd + 1);
}


/*
=============
RB_DrawBuffer""",
    "close shadow stage",
)

# Shadow-map copy/capture command.
one(
    "SP/code/rend2/tr_backend.c",
    """const void *RB_CapShadowMap(const void *data)
{
	const capShadowmapCommand_t *cmd = data;
""",
    """const void *RB_CapShadowMap(const void *data)
{
	const capShadowmapCommand_t *cmd = data;
	DWPerfStageBegin(DWPERF_SHADOW_CAPTURE);
""",
    "begin shadow capture probe",
)

one(
    "SP/code/rend2/tr_backend.c",
    """	return (const void *)(cmd + 1);
}


/*
=============
RB_PostProcess""",
    """	DWPerfStageEnd(DWPERF_SHADOW_CAPTURE);
	return (const void *)(cmd + 1);
}


/*
=============
RB_PostProcess""",
    "end shadow capture probe",
)

# Whole postprocess probe after the early disabled return.
one(
    "SP/code/rend2/tr_backend.c",
    """	if (!glRefConfig.framebufferObject || !r_postProcess->integer)
	{
		// do nothing
		return (const void *)(cmd + 1);
	}

	if (cmd)""",
    """	if (!glRefConfig.framebufferObject || !r_postProcess->integer)
	{
		// do nothing
		return (const void *)(cmd + 1);
	}

	DWPerfStageBegin(DWPERF_POST_TOTAL);

	if (cmd)""",
    "begin postprocess total probe",
)

one(
    "SP/code/rend2/tr_backend.c",
    """		FBO_FastBlit(tr.renderFbo, NULL, tr.msaaResolveFbo, NULL, GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT, GL_NEAREST);
		srcFbo = tr.msaaResolveFbo;""",
    """		DWPerfStageBegin(DWPERF_MSAA_RESOLVE);
		FBO_FastBlit(tr.renderFbo, NULL, tr.msaaResolveFbo, NULL, GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT, GL_NEAREST);
		DWPerfStageEnd(DWPERF_MSAA_RESOLVE);
		srcFbo = tr.msaaResolveFbo;""",
    "probe post MSAA resolve",
)

one(
    "SP/code/rend2/tr_backend.c",
    """		FBO_Blit(tr.screenSsaoFbo, srcBox, NULL, srcFbo, dstBox, NULL, NULL, GLS_SRCBLEND_DST_COLOR | GLS_DSTBLEND_ZERO);
	}

	RB_USLRDRootCauseSampleStage(srcFbo, dstBox, s_uslrdRcHdrAfterSsao);""",
    """		DWPerfStageBegin(DWPERF_SSAO);
		FBO_Blit(tr.screenSsaoFbo, srcBox, NULL, srcFbo, dstBox, NULL, NULL, GLS_SRCBLEND_DST_COLOR | GLS_DSTBLEND_ZERO);
		DWPerfStageEnd(DWPERF_SSAO);
	}

	RB_USLRDRootCauseSampleStage(srcFbo, dstBox, s_uslrdRcHdrAfterSsao);""",
    "probe SSAO composite",
)

one(
    "SP/code/rend2/tr_backend.c",
    """				GL_BindToTMU(tr.hdrDepthImage, TB_LIGHTMAP);
				GL_BindToTMU(tr.ssgiEntityDepthImage, TB_NORMALMAP); // REND2_GI_2_V1_5_SCENE_ENTITY_WORLD_MASK
				GLSL_BindProgram(&tr.ssgiShader);""",
    """				DWPerfStageBegin(DWPERF_SSGI);
				GL_BindToTMU(tr.hdrDepthImage, TB_LIGHTMAP);
				GL_BindToTMU(tr.ssgiEntityDepthImage, TB_NORMALMAP); // REND2_GI_2_V1_5_SCENE_ENTITY_WORLD_MASK
				GLSL_BindProgram(&tr.ssgiShader);""",
    "begin SSGI probe",
)

one(
    "SP/code/rend2/tr_backend.c",
    """					qglTextureParameterfEXT(tr.quarterImage[0]->texnum, GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
					qglTextureParameterfEXT(tr.quarterImage[0]->texnum, GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
				}				ssgiActive = qtrue;""",
    """					qglTextureParameterfEXT(tr.quarterImage[0]->texnum, GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
					qglTextureParameterfEXT(tr.quarterImage[0]->texnum, GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
				}
				DWPerfStageEnd(DWPERF_SSGI);
				ssgiActive = qtrue;""",
    "end SSGI probe",
)

one(
    "SP/code/rend2/tr_backend.c",
    """		if (r_volumetricSun->integer)
			RB_VolumetricSun(srcFbo, srcBox);
		RB_VolumetricSunPerfTrace();""",
    """		if (r_volumetricSun->integer)
		{
			DWPerfStageBegin(DWPERF_VOLUMETRIC_SUN);
			RB_VolumetricSun(srcFbo, srcBox);
			DWPerfStageEnd(DWPERF_VOLUMETRIC_SUN);
		}
		RB_VolumetricSunPerfTrace();""",
    "probe volumetric sun",
)

one(
    "SP/code/rend2/tr_backend.c",
    """		if (r_volumetricLocal->integer)
			RB_VolumetricLocal(srcFbo, srcBox);
		RB_USLRDRootCauseAfterLocal(srcFbo, srcBox);""",
    """		if (r_volumetricLocal->integer)
		{
			DWPerfStageBegin(DWPERF_VOLUMETRIC_LOCAL);
			RB_VolumetricLocal(srcFbo, srcBox);
			DWPerfStageEnd(DWPERF_VOLUMETRIC_LOCAL);
		}
		RB_USLRDRootCauseAfterLocal(srcFbo, srcBox);""",
    "probe local volumetrics",
)

one(
    "SP/code/rend2/tr_backend.c",
    """		RB_VolumetricFire(srcFbo, srcBox);
		RB_USLRDRootCauseSampleStage(srcFbo, srcBox, s_uslrdRcHdrAfterFire);""",
    """		DWPerfStageBegin(DWPERF_VOLUMETRIC_FIRE);
		RB_VolumetricFire(srcFbo, srcBox);
		DWPerfStageEnd(DWPERF_VOLUMETRIC_FIRE);
		RB_USLRDRootCauseSampleStage(srcFbo, srcBox, s_uslrdRcHdrAfterFire);""",
    "probe fire volumetrics",
)

one(
    "SP/code/rend2/tr_backend.c",
    """			RB_ToneMap(srcFbo, srcBox, tr.screenScratchFbo, srcBox, autoExposure);
			FBO_FastBlit(tr.screenScratchFbo, srcBox, srcFbo, srcBox, GL_COLOR_BUFFER_BIT, GL_NEAREST);""",
    """			DWPerfStageBegin(DWPERF_TONEMAP);
			RB_ToneMap(srcFbo, srcBox, tr.screenScratchFbo, srcBox, autoExposure);
			FBO_FastBlit(tr.screenScratchFbo, srcBox, srcFbo, srcBox, GL_COLOR_BUFFER_BIT, GL_NEAREST);
			DWPerfStageEnd(DWPERF_TONEMAP);""",
    "probe tonemap",
)

one(
    "SP/code/rend2/tr_backend.c",
    """	if (r_drawSunRays->integer)
		RB_SunRays(srcFbo, srcBox, srcFbo, srcBox);
	RB_USLRDRootCauseSampleStage(srcFbo, srcBox, s_uslrdRcAfterSunRays);""",
    """	if (r_drawSunRays->integer)
	{
		DWPerfStageBegin(DWPERF_SUNRAYS);
		RB_SunRays(srcFbo, srcBox, srcFbo, srcBox);
		DWPerfStageEnd(DWPERF_SUNRAYS);
	}
	RB_USLRDRootCauseSampleStage(srcFbo, srcBox, s_uslrdRcAfterSunRays);""",
    "probe sun rays",
)

one(
    "SP/code/rend2/tr_backend.c",
    """	if (1)
		RB_BokehBlur(srcFbo, srcBox, srcFbo, srcBox, backEnd.refdef.blurFactor);
	else
		RB_GaussianBlur(srcFbo, srcFbo, backEnd.refdef.blurFactor);
	RB_USLRDRootCauseSampleStage(srcFbo, srcBox, s_uslrdRcAfterBokeh);""",
    """	if (1)
	{
		DWPerfStageBegin(DWPERF_BOKEH);
		RB_BokehBlur(srcFbo, srcBox, srcFbo, srcBox, backEnd.refdef.blurFactor);
		DWPerfStageEnd(DWPERF_BOKEH);
	}
	else
		RB_GaussianBlur(srcFbo, srcFbo, backEnd.refdef.blurFactor);
	RB_USLRDRootCauseSampleStage(srcFbo, srcBox, s_uslrdRcAfterBokeh);""",
    "probe bokeh",
)

one(
    "SP/code/rend2/tr_backend.c",
    """	if (srcFbo != dstFbo)
		FBO_FastBlit(srcFbo, srcBox, dstFbo, dstBox, GL_COLOR_BUFFER_BIT, GL_NEAREST);

	RB_DlightMaterialAutoTestStep();""",
    """	if (srcFbo != dstFbo)
	{
		DWPerfStageBegin(DWPERF_FINAL_BLIT);
		FBO_FastBlit(srcFbo, srcBox, dstFbo, dstBox, GL_COLOR_BUFFER_BIT, GL_NEAREST);
		DWPerfStageEnd(DWPERF_FINAL_BLIT);
	}

	RB_DlightMaterialAutoTestStep();""",
    "probe final post blit",
)

# End the whole postprocess probe at the function's final return. Anchor includes
# the following command function to avoid touching unrelated returns.
one(
    "SP/code/rend2/tr_backend.c",
    """	return (const void *)(cmd + 1);
}


/*
=============
RB_ExportCubemaps""",
    """	DWPerfStageEnd(DWPERF_POST_TOTAL);
	return (const void *)(cmd + 1);
}


/*
=============
RB_ExportCubemaps""",
    "end postprocess total probe",
)

for rel in [
    "SP/code/rend2/tr_local.h",
    "SP/code/rend2/tr_cmds.c",
    "SP/code/rend2/tr_main.c",
    "SP/code/rend2/tr_scene.c",
    "SP/code/rend2/tr_fbo.c",
    "SP/code/rend2/tr_backend.c",
]:
    require(rel, [MARK], "telemetry marker propagation" if rel == "SP/code/rend2/tr_local.h" else rel)

print("DARKWOLF_V446_FULL_PERF_TELEMETRY_V01_PATCH_OK")
