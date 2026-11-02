#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source")
B = ROOT / "SP/code/rend2/tr_backend.c"
F = ROOT / "SP/code/rend2/tr_fbo.c"
S = ROOT / "SP/code/rend2/glsl/volumetriclocal_upscale_fp.glsl"
MARK = "DARKWOLF_VOLUMETRIC_EDGE_AA_V1_DIAG2"
DEPTH_MARK = "DARKWOLF_VOLUMETRIC_EDGE_AA_DEPTH_FEEDBACK_FIX_V1"


def rep(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ERROR {label}: expected 1 anchor, found {n}")
    return text.replace(old, new, 1)


b = B.read_text(encoding="utf-8")
f = F.read_text(encoding="utf-8")
s = S.read_text(encoding="utf-8")
if MARK in b:
    if DEPTH_MARK not in f:
        raise SystemExit("ERROR Attempt2 backend applied but depth-feedback fix missing")
    print("Attempt2 already applied")
    raise SystemExit(0)

required_b = [
    "DARKWOLF_SUN_VOLUMETRIC_V0_3",
    "DARKWOLF_LOCAL_VOLUMETRIC_V0_1",
    "DARKWOLF_FIREVOL_SPATIAL_RECONSTRUCTION_EDGE_QUALITY_PC02",
    "FBO_FastBlit(tr.renderFbo, NULL, tr.msaaResolveFbo, NULL, GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT, GL_NEAREST);",
]
for x in required_b:
    if x not in b:
        raise SystemExit("ERROR backend missing parent marker: " + x)
if "DARKWOLF_FIREVOL_SPATIAL_RECONSTRUCTION_EDGE_QUALITY_PC02" not in s:
    raise SystemExit("ERROR shader PC02 parent missing")

# screenScratchFbo is a full-resolution color scratch used by shadow blur/tone-map and
# volumetric reconstruction. The stock FBO also attaches tr.renderDepthImage as its
# destination depth attachment. Volumetric reconstruction samples that same depth
# texture, which creates an OpenGL framebuffer-texture feedback hazard. None of the
# accepted screenScratch users needs a writable depth attachment, so make it color-only.
fbo_old = '''	if (tr.screenScratchImage)
	{
		tr.screenScratchFbo = FBO_Create("screenScratch", tr.screenScratchImage->width, tr.screenScratchImage->height);
		FBO_AttachImage(tr.screenScratchFbo, tr.screenScratchImage, GL_COLOR_ATTACHMENT0, 0);
		FBO_AttachImage(tr.screenScratchFbo, tr.renderDepthImage, GL_DEPTH_ATTACHMENT, 0);
		R_CheckFBO(tr.screenScratchFbo);
	}
'''
fbo_new = '''	if (tr.screenScratchImage)
	{
		tr.screenScratchFbo = FBO_Create("screenScratch", tr.screenScratchImage->width, tr.screenScratchImage->height);
		FBO_AttachImage(tr.screenScratchFbo, tr.screenScratchImage, GL_COLOR_ATTACHMENT0, 0);
		// DARKWOLF_VOLUMETRIC_EDGE_AA_DEPTH_FEEDBACK_FIX_V1
		// Color-only scratch: volumetric reconstruction samples tr.renderDepthImage.
		// Do not attach the sampled depth texture to the draw framebuffer.
		R_CheckFBO(tr.screenScratchFbo);
	}
'''
f = rep(f, fbo_old, fbo_new, "detach sampled render depth from screenScratchFbo")

shader_old = ''' int kernelMode=int(floor(u_Color.y+0.5)); vec3 sum=vec3(0.0); float sumW=0.0;
 if (kernelMode >= 2)
 {
  for (int y=-2;y<=2;++y) for (int x=-2;x<=2;++x)
  {
   vec2 suv=clamp(uv+vec2(float(x)*texel.x,float(y)*texel.y),lo,hi);
   float sd=getLinearDepth(u_ScreenDepthMap,suv,u_ViewInfo.x); float r2=float(x*x+y*y);
   float w=depthWeight(cd,sd,reject)*exp(-0.22*r2); sum+=texture2D(u_DiffuseMap,suv).rgb*w; sumW+=w;
  }
 }
 else
'''

shader_new = ''' int kernelMode=int(floor(u_Color.y+0.5)); vec3 sum=vec3(0.0); float sumW=0.0;
 // DARKWOLF_VOLUMETRIC_EDGE_AA_V1_DIAG2
 // Mode 3 is an energy-preserving 2x2 joint-bilateral upsample for the exact 2x
 // quarter-buffer scale. With equal depths it reduces exactly to ordinary bilinear
 // interpolation. Depth disagreement only suppresses samples across geometry edges.
 if (kernelMode == 3)
 {
  vec2 p = uv / texel - vec2(0.5);
  vec2 base = floor(p);
  vec2 f = fract(p);
  vec2 q00=clamp((base+vec2(0.5,0.5))*texel,lo,hi);
  vec2 q10=clamp((base+vec2(1.5,0.5))*texel,lo,hi);
  vec2 q01=clamp((base+vec2(0.5,1.5))*texel,lo,hi);
  vec2 q11=clamp((base+vec2(1.5,1.5))*texel,lo,hi);
  float w00=(1.0-f.x)*(1.0-f.y)*depthWeight(cd,getLinearDepth(u_ScreenDepthMap,q00,u_ViewInfo.x),reject);
  float w10=(      f.x)*(1.0-f.y)*depthWeight(cd,getLinearDepth(u_ScreenDepthMap,q10,u_ViewInfo.x),reject);
  float w01=(1.0-f.x)*(      f.y)*depthWeight(cd,getLinearDepth(u_ScreenDepthMap,q01,u_ViewInfo.x),reject);
  float w11=(      f.x)*(      f.y)*depthWeight(cd,getLinearDepth(u_ScreenDepthMap,q11,u_ViewInfo.x),reject);
  sum = texture2D(u_DiffuseMap,q00).rgb*w00
      + texture2D(u_DiffuseMap,q10).rgb*w10
      + texture2D(u_DiffuseMap,q01).rgb*w01
      + texture2D(u_DiffuseMap,q11).rgb*w11;
  sumW = w00+w10+w01+w11;
  if (sumW < 0.0001) { sum=texture2D(u_DiffuseMap,uv).rgb; sumW=1.0; }
 }
 else if (kernelMode >= 2)
 {
  for (int y=-2;y<=2;++y) for (int x=-2;x<=2;++x)
  {
   vec2 suv=clamp(uv+vec2(float(x)*texel.x,float(y)*texel.y),lo,hi);
   float sd=getLinearDepth(u_ScreenDepthMap,suv,u_ViewInfo.x); float r2=float(x*x+y*y);
   float w=depthWeight(cd,sd,reject)*exp(-0.22*r2); sum+=texture2D(u_DiffuseMap,suv).rgb*w; sumW+=w;
  }
 }
 else
'''
s = rep(s, shader_old, shader_new, "add joint-bilateral kernel mode 3")

sun_anchor = '''// DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3
static void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)
{
'''

sun_helper = r'''// DARKWOLF_VOLUMETRIC_EDGE_AA_V1_DIAG2
// Diagnostic gate for Attempt 2. Production promotion will keep only the two user-facing
// AA controls and remove trace/counters. Existing Fire/Spot reconstruction modes are untouched.
static cvar_t *s_rVolumetricEdgeAA;
static cvar_t *s_rVolumetricEdgeAADepthReject;
static cvar_t *s_rVolumetricEdgeAATrace;
static unsigned int s_vaa2SunAA;
static unsigned int s_vaa2SunBase;
static unsigned int s_vaa2LocalAA;
static unsigned int s_vaa2LocalBase;

static void RB_VolumetricEdgeAAEnsureCvars(void)
{
	if (!s_rVolumetricEdgeAA)
		s_rVolumetricEdgeAA = ri.Cvar_Get("r_volumetricEdgeAA", "0", 0);
	if (!s_rVolumetricEdgeAADepthReject)
		s_rVolumetricEdgeAADepthReject = ri.Cvar_Get("r_volumetricEdgeAADepthReject", "16.0", 0);
	if (!s_rVolumetricEdgeAATrace)
		s_rVolumetricEdgeAATrace = ri.Cvar_Get("r_volumetricEdgeAATrace", "0", 0);
}

static qboolean RB_VolumetricEdgeAAFullRes(FBO_t *srcFbo, ivec4_t srcBox, const vec4_t viewInfo)
{
	vec4_t p;
	if (!srcFbo || !tr.quarterFbo[0] || !tr.screenScratchFbo || !tr.renderDepthImage ||
		!tr.volumetricLocalUpscaleShader.program)
		return qfalse;

	VectorSet4(p,
		Com_Clamp(0.0f, 64.0f, s_rVolumetricEdgeAADepthReject ? s_rVolumetricEdgeAADepthReject->value : 16.0f),
		3.0f, 1.0f, 0.0f);
	GL_BindToTMU(tr.renderDepthImage, TB_NORMALMAP);
	GLSL_BindProgram(&tr.volumetricLocalUpscaleShader);
	GLSL_SetUniformVec4(&tr.volumetricLocalUpscaleShader, UNIFORM_VIEWINFO, viewInfo);
	FBO_Blit(tr.quarterFbo[0], NULL, NULL, tr.screenScratchFbo, srcBox,
		&tr.volumetricLocalUpscaleShader, p, 0);
	FBO_Blit(tr.screenScratchFbo, srcBox, NULL, srcFbo, srcBox, NULL, NULL,
		GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);
	return qtrue;
}

// DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3
static void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)
{
'''
b = rep(b, sun_anchor, sun_helper, "insert EdgeAA helpers")

sun_old = '''	tr.volumetricSunPerfRaymarchThisFrame = 1; // DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3
	FBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricSunShader, params, 0);
	FBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);
'''
sun_new = '''	tr.volumetricSunPerfRaymarchThisFrame = 1; // DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3
	FBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricSunShader, params, 0);
	RB_VolumetricEdgeAAEnsureCvars();
	if (s_rVolumetricEdgeAA->integer && RB_VolumetricEdgeAAFullRes(srcFbo, srcBox, viewInfo))
		s_vaa2SunAA++;
	else
	{
		s_vaa2SunBase++;
		FBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);
	}
'''
b = rep(b, sun_old, sun_new, "Sun joint bilateral composite")

local_start_old = '''	FBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricLocalShader, params, 0);
	{
		int reconstructionMode = 0;
		float reconstructionDepthReject = 10.0f;
'''
local_start_new = '''	RB_VolumetricEdgeAAEnsureCvars();
	FBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricLocalShader, params, 0);
	{
		int reconstructionMode = 0;
		float reconstructionDepthReject = 10.0f;
'''
b = rep(b, local_start_old, local_start_new, "Local cvar gate")

local_branch_anchor = '''		if (reconstructionMode == 3 && tr.screenScratchFbo && tr.volumetricLocalUpscaleShader.program)
		{
			vec4_t upscaleParams;
			VectorSet4(upscaleParams, Com_Clamp(0.0f, 64.0f, reconstructionDepthReject), 2.0f, 1.0f, 0.0f);
'''
local_branch_new = '''		// DARKWOLF_VOLUMETRIC_EDGE_AA_V1_DIAG2: only production Local point modes 1..3.
		// Fire (5..8) and Spotlight (4) retain their accepted reconstruction policy byte-for-byte.
		if (mode >= 1 && mode <= 3)
		{
			if (s_rVolumetricEdgeAA->integer)
			{
				reconstructionMode = 4;
				reconstructionDepthReject = s_rVolumetricEdgeAADepthReject ? s_rVolumetricEdgeAADepthReject->value : 16.0f;
				s_vaa2LocalAA++;
			}
			else
				s_vaa2LocalBase++;
		}

		if ((reconstructionMode == 3 || reconstructionMode == 4) && tr.screenScratchFbo && tr.volumetricLocalUpscaleShader.program)
		{
			vec4_t upscaleParams;
			float kernelMode = (reconstructionMode == 4) ? 3.0f : 2.0f;
			VectorSet4(upscaleParams, Com_Clamp(0.0f, 64.0f, reconstructionDepthReject), kernelMode, 1.0f, 0.0f);
'''
b = rep(b, local_branch_anchor, local_branch_new, "Local point joint bilateral mode")

post_anchor = '''	dstBox[0] = backEnd.viewParms.viewportX;
'''
post_new = r'''	RB_VolumetricEdgeAAEnsureCvars();
	if (s_rVolumetricEdgeAATrace && s_rVolumetricEdgeAATrace->integer)
	{
		static int lastMode = -999;
		static int lastTraceFrame = -1000000;
		int curMode = s_rVolumetricEdgeAA ? s_rVolumetricEdgeAA->integer : 0;
		if (curMode != lastMode || tr.frameCount < lastTraceFrame || tr.frameCount - lastTraceFrame >= 30)
		{
			lastMode = curMode;
			lastTraceFrame = tr.frameCount;
			ri.Printf(PRINT_ALL,
				"VAA2_TRACE frame=%d map=%s edgeAA=%d reject=%.2f msaaRequested=%d msaaResolveFbo=%d src=%s srcSize=%dx%d quarter=%dx%d depth=%dx%d scratch=%dx%d sun=%d local=%d localMode=%d sunAA=%u sunBase=%u localAA=%u localBase=%u\n",
				tr.frameCount, tr.world ? tr.world->baseName : "<none>", curMode,
				s_rVolumetricEdgeAADepthReject ? s_rVolumetricEdgeAADepthReject->value : 0.0f,
				r_ext_framebuffer_multisample ? r_ext_framebuffer_multisample->integer : 0,
				tr.msaaResolveFbo ? 1 : 0,
				srcFbo ? srcFbo->name : "<null>", srcFbo ? srcFbo->width : 0, srcFbo ? srcFbo->height : 0,
				tr.quarterFbo[0] ? tr.quarterFbo[0]->width : 0, tr.quarterFbo[0] ? tr.quarterFbo[0]->height : 0,
				tr.renderDepthImage ? tr.renderDepthImage->width : 0, tr.renderDepthImage ? tr.renderDepthImage->height : 0,
				tr.screenScratchFbo ? tr.screenScratchFbo->width : 0, tr.screenScratchFbo ? tr.screenScratchFbo->height : 0,
				r_volumetricSun ? r_volumetricSun->integer : 0,
				r_volumetricLocal ? r_volumetricLocal->integer : 0,
				r_volumetricLocalMode ? r_volumetricLocalMode->integer : -1,
				s_vaa2SunAA, s_vaa2SunBase, s_vaa2LocalAA, s_vaa2LocalBase);
		}
	}

	dstBox[0] = backEnd.viewParms.viewportX;
'''
b = rep(b, post_anchor, post_new, "VAA2 trace")

for x in [
    MARK, "kernelMode == 3", "r_volumetricEdgeAA", "VAA2_TRACE frame=",
    "reconstructionMode = 4", "s_vaa2SunAA++", "s_vaa2LocalAA++"
]:
    if x not in b and x not in s:
        raise SystemExit("ERROR final marker missing: " + x)

if DEPTH_MARK not in f:
    raise SystemExit("ERROR final depth-feedback marker missing")

B.write_text(b, encoding="utf-8", newline="\n")
F.write_text(f, encoding="utf-8", newline="\n")
S.write_text(s, encoding="utf-8", newline="\n")
print("DARKWOLF_VOLUMETRIC_EDGE_AA_ATTEMPT2_PATCH_OK")
