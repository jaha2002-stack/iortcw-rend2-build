/* DARKWOLF_SKY_MSAA_ROOT_CAUSE_MATRIX_V1
 * V3 DIAGNOSTIC CAPTURE CORRECTION OVER EXACT RUN 40294211216
 * GPL-3.0-or-later. Only active when r_skyDiagAuto=1 and user presses F8.
 * V3 fixes V2 deadlock: mandatory GPU snapshots DO NOT depend on sky stage.
 * Portal-sky views are separately probed. Non-sky pre-post fallback is tagged.
 */
#ifndef DARKWOLF_SKY_DIAG_RUNTIME_H
#define DARKWOLF_SKY_DIAG_RUNTIME_H

#ifdef USE_LOCAL_HEADERS
# include "SDL.h"
#else
# include <SDL.h>
#endif

#ifndef GL_SAMPLE_ALPHA_TO_COVERAGE
#define GL_SAMPLE_ALPHA_TO_COVERAGE 0x809E
#endif
#ifndef GL_SAMPLE_SHADING_ARB
#define GL_SAMPLE_SHADING_ARB 0x8C36
#endif
#ifndef GL_SAMPLE_MASK
#define GL_SAMPLE_MASK 0x8E51
#endif
#ifndef GL_READ_FRAMEBUFFER_BINDING
#define GL_READ_FRAMEBUFFER_BINDING 0x8CAA
#endif
#ifndef GL_DRAW_FRAMEBUFFER_BINDING
#define GL_DRAW_FRAMEBUFFER_BINDING 0x8CA6
#endif

#define DW_SKY_DIAG_MODES 5
#define DW_SKY_DIAG_CAPTURE_DELAY_MS 700
#define DW_SKY_DIAG_MODE_DURATION_MS 1800
#define DW_SKY_DIAG_MODE_TIMEOUT_MS 9500
#define DW_SKY_DIAG_TRACE_CAPACITY 65536

static cvar_t *dwSkyDiagAuto = NULL;
static cvar_t *dwSkyDiagArm = NULL;
static int dwSkyDiagArmed = 0;
static int dwSkyDiagMode = 0;
static int dwSkyDiagFrame = 0;
static int dwSkyDiagModeStartMs = 0;
static int dwSkyDiagWorldSeen = 0;
static int dwSkyDiagSkySeen = 0;
static int dwSkyDiagProbeBits = 0;
static int dwSkyDiagControlCalls = 0;
static int dwSkyDiagPreResolveCalls = 0;
static int dwSkyDiagSkyCaptureDone = 0;
static int dwSkyDiagHdrDone = 0;
static int dwSkyDiagDepthDone = 0;
static int dwSkyDiagFinalCaptureDone = 0;
static int dwSkyDiagModeLogged = 0;
static int dwSkyDiagTimeouts = 0;
static int dwSkyDiagReadErrors = 0;
static int dwSkyDiagTraceOverrun = 0;
static int dwSkyDiagSamples = -1;
static int dwSkyDiagCameraMotion = 0;
static vec3_t dwSkyDiagCameraOrigin;
static vec3_t dwSkyDiagCameraForward;
static char dwSkyDiagMap[MAX_QPATH] = "";
static char dwSkyDiagTrace[DW_SKY_DIAG_TRACE_CAPACITY] = "";
static int dwSkyDiagTraceUsed = 0;

static void DW_SkyDiagAppend(const char *line)
{
    const int size = (int)strlen(line);
    if (size <= 0) return;
    if (dwSkyDiagTraceUsed + size < (int)sizeof(dwSkyDiagTrace) - 1) {
        memcpy(dwSkyDiagTrace + dwSkyDiagTraceUsed, line, size);
        dwSkyDiagTraceUsed += size;
        dwSkyDiagTrace[dwSkyDiagTraceUsed] = '\0';
    } else if (!dwSkyDiagTraceOverrun) {
        dwSkyDiagTraceOverrun = 1;
        ri.Printf(PRINT_WARNING, "DW_SKY_DIAG_TRACE_OVERFLOW: diagnostic invalid\n");
    }
}

static void DW_SkyDiagFlush(void)
{
    char name[MAX_QPATH];
    if (!dwSkyDiagMap[0]) return;
    Com_sprintf(name, sizeof(name), "DW_SKY_%s_TRACE.csv", dwSkyDiagMap);
    ri.FS_WriteFile(name, dwSkyDiagTrace, dwSkyDiagTraceUsed);
}

static int DW_SkyDiagIsEnabled(GLenum capability)
{
    GLboolean enabled = GL_FALSE;
    qglGetBooleanv(capability, &enabled);
    return enabled == GL_TRUE ? 1 : 0;
}

typedef void (APIENTRYP DW_SkyDiagReadBufferProc)(GLenum);
typedef void (APIENTRYP DW_SkyDiagPixelStoreiProc)(GLenum, GLint);
static DW_SkyDiagReadBufferProc dwSkyDiagGLReadBuffer = NULL;
static DW_SkyDiagPixelStoreiProc dwSkyDiagGLPixelStorei = NULL;
static int dwSkyDiagReadbackProcsFailed = 0;

static qboolean DW_SkyDiagEnsureReadbackProcs(void)
{
    if (!dwSkyDiagGLReadBuffer)
        dwSkyDiagGLReadBuffer = (DW_SkyDiagReadBufferProc)SDL_GL_GetProcAddress("glReadBuffer");
    if (!dwSkyDiagGLPixelStorei)
        dwSkyDiagGLPixelStorei = (DW_SkyDiagPixelStoreiProc)SDL_GL_GetProcAddress("glPixelStorei");
    if (dwSkyDiagGLReadBuffer && dwSkyDiagGLPixelStorei) return qtrue;
    if (!dwSkyDiagReadbackProcsFailed) {
        dwSkyDiagReadbackProcsFailed = 1;
        DW_SkyDiagAppend("ERROR,GL_PROC_RESOLUTION_FAILED\n");
        ri.Printf(PRINT_WARNING,"DW_SKY_DIAG_ERROR: GL readback entry point unavailable\n");
        DW_SkyDiagFlush();
    }
    return qfalse;
}

static void DW_SkyDiagEvent(const char *event)
{
    char line[512];
    GLint read = -1, draw = -1, samples = -1, sampleBuffers = -1;
    GLint vp[4] = {0}, sc[4] = {0}, depthFunc = -1;
    int shading = -1, mask = -1;
    qglGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &read);
    qglGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &draw);
    qglGetIntegerv(GL_SAMPLES, &samples);
    qglGetIntegerv(GL_SAMPLE_BUFFERS, &sampleBuffers);
    qglGetIntegerv(GL_VIEWPORT, vp);
    qglGetIntegerv(GL_SCISSOR_BOX, sc);
    qglGetIntegerv(GL_DEPTH_FUNC, &depthFunc);
    if (QGL_VERSION_ATLEAST(4, 0) || SDL_GL_ExtensionSupported("GL_ARB_sample_shading"))
        shading = DW_SkyDiagIsEnabled(GL_SAMPLE_SHADING_ARB);
    if (QGL_VERSION_ATLEAST(3, 2) || SDL_GL_ExtensionSupported("GL_ARB_texture_multisample"))
        mask = DW_SkyDiagIsEnabled(GL_SAMPLE_MASK);
    if (glState.currentFBO == tr.renderFbo && tr.renderFbo && samples > dwSkyDiagSamples)
        dwSkyDiagSamples = samples;
    Com_sprintf(line,sizeof(line),
        "STATE,%s,%d,%d,read=%d,draw=%d,samples=%d,buffers=%d,msaa=%d,shading=%d,mask=%d,a2c=%d,blend=%d,depth=%d,scissor=%d,depthFunc=%d,vp=%d:%d:%d:%d,sc=%d:%d:%d:%d,colorfmt=%d,depthfmt=%d,requested=%d\n",
        event,dwSkyDiagMode,dwSkyDiagFrame,read,draw,samples,sampleBuffers,
        DW_SkyDiagIsEnabled(GL_MULTISAMPLE),shading,mask,
        DW_SkyDiagIsEnabled(GL_SAMPLE_ALPHA_TO_COVERAGE),
        DW_SkyDiagIsEnabled(GL_BLEND),DW_SkyDiagIsEnabled(GL_DEPTH_TEST),
        DW_SkyDiagIsEnabled(GL_SCISSOR_TEST),depthFunc,
        vp[0],vp[1],vp[2],vp[3],sc[0],sc[1],sc[2],sc[3],
        tr.renderFbo ? tr.renderFbo->colorFormat : 0,
        tr.renderFbo ? tr.renderFbo->depthFormat : 0,
        r_ext_framebuffer_multisample ? r_ext_framebuffer_multisample->integer : 0);
    DW_SkyDiagAppend(line);
}

static void DW_SkyDiagResetModeFlags(void)
{
    dwSkyDiagSkySeen = dwSkyDiagSkyCaptureDone = 0;
    dwSkyDiagProbeBits = dwSkyDiagControlCalls = dwSkyDiagPreResolveCalls = 0;
    dwSkyDiagHdrDone = dwSkyDiagDepthDone = dwSkyDiagFinalCaptureDone = 0;
    dwSkyDiagModeLogged = 0;
    dwSkyDiagWorldSeen = 0;
    dwSkyDiagFrame = 0;
}

static void DW_SkyDiagNewTrace(void)
{
    dwSkyDiagTraceUsed = dwSkyDiagTraceOverrun = dwSkyDiagReadErrors = 0;
    dwSkyDiagTrace[0] = 0;
    DW_SkyDiagAppend("DW_SKY_DIAG_V3,mode,frame,details\n");
}

/* RGBA readback is more portable than GL_RGB/GL_FLOAT on HDR attachments.
 * Convert to 3-channel PFM/PPM only after GL has written the complete RGBA buffer.
 * Return true ONLY for an actual file write after an error-free readback.
 */
static qboolean DW_SkyDiagRead(FBO_t *fbo,const char *stage,int depth,int screen)
{
    GLint oldRead = 0, oldBuffer = GL_BACK, oldPack = 4;
    const int width = screen ? glConfig.vidWidth : (fbo ? fbo->width : 0);
    const int height = screen ? glConfig.vidHeight : (fbo ? fbo->height : 0);
    const int components = depth ? 1 : 3;
    const int bytes = screen ? 1 : 4;
    int pixCount, pixBytes, headerBytes, i;
    unsigned char *out, *rgba = NULL;
    char name[MAX_QPATH], header[96], line[300];
    GLenum err, before = GL_NO_ERROR;
    if (width <= 0 || height <= 0 || width > 4096 || height > 4096 || (!screen && !fbo)) {
        DW_SkyDiagAppend("ERROR,INVALID_CAPTURE_DIMENSIONS\n");
        return qfalse;
    }
    if (!DW_SkyDiagEnsureReadbackProcs()) return qfalse;
    pixCount = width * height;
    pixBytes = pixCount * components * bytes;
    Com_sprintf(header,sizeof(header),screen ? "P6\n%d %d\n255\n" : (depth ? "Pf\n%d %d\n-1.0\n" : "PF\n%d %d\n-1.0\n"),width,height);
    headerBytes = (int)strlen(header);
    out = ri.Hunk_AllocateTempMemory(pixBytes+headerBytes);
    if (!out) { DW_SkyDiagAppend("ERROR,ALLOC_OUTPUT_FAILED\n"); return qfalse; }
    if (!depth) rgba = ri.Hunk_AllocateTempMemory(pixCount * 4 * bytes);
    if (!depth && !rgba) {
        ri.Hunk_FreeTempMemory(out);
        DW_SkyDiagAppend("ERROR,ALLOC_RGBA_FAILED\n");
        return qfalse;
    }
    memcpy(out,header,headerBytes);
    qglGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&oldRead);
    qglGetIntegerv(GL_READ_BUFFER,&oldBuffer);
    qglGetIntegerv(GL_PACK_ALIGNMENT,&oldPack);
    /* Prevent stale GL errors from unrelated renderer passes from invalidating a capture. */
    for (i=0;i<8;++i) {
        GLenum e=qglGetError();
        if (e==GL_NO_ERROR) break;
        before=e;
    }
    if (before!=GL_NO_ERROR && dwSkyDiagReadErrors<16) {
        Com_sprintf(line,sizeof(line),"GL_PREEXISTING_ERROR,%d,%s,0x%x\n",dwSkyDiagMode,stage,before);
        DW_SkyDiagAppend(line);
    }
    GL_BindFramebuffer(GL_READ_FRAMEBUFFER,screen ? 0 : fbo->frameBuffer);
    dwSkyDiagGLReadBuffer(screen ? GL_BACK : GL_COLOR_ATTACHMENT0);
    dwSkyDiagGLPixelStorei(GL_PACK_ALIGNMENT,1);
    if (depth)
        qglReadPixels(0,0,width,height,GL_DEPTH_COMPONENT,GL_FLOAT,out+headerBytes);
    else
        qglReadPixels(0,0,width,height,GL_RGBA,screen ? GL_UNSIGNED_BYTE : GL_FLOAT,rgba);
    err=qglGetError();
    if (err==GL_NO_ERROR && rgba) {
        if (screen) {
            for (i=0;i<pixCount;++i) {
                out[headerBytes+i*3] = rgba[i*4];
                out[headerBytes+i*3+1] = rgba[i*4+1];
                out[headerBytes+i*3+2] = rgba[i*4+2];
            }
        } else {
            for (i=0;i<pixCount;++i)
                memcpy(out+headerBytes+i*12,rgba+i*16,12);
        }
    }
    if (err==GL_NO_ERROR) {
        Com_sprintf(name,sizeof(name),"DW_SKY_%s_M%d_%s.%s",dwSkyDiagMap,
            dwSkyDiagMode,stage,screen ? "ppm" : "pfm");
        ri.FS_WriteFile(name,out,headerBytes+pixBytes);
        Com_sprintf(line,sizeof(line),"CAPTURE_OK,%d,%s,%s,%dx%d,bytes=%d\n",
            dwSkyDiagMode,stage,name,width,height,pixBytes);
        DW_SkyDiagAppend(line);
        ri.Printf(PRINT_ALL,"DW_SKY_DIAG_SAVED %s\n",name);
    } else {
        ++dwSkyDiagReadErrors;
        if (dwSkyDiagReadErrors < 25) {
            Com_sprintf(line,sizeof(line),"READBACK_ERROR,%d,%s,0x%x,readfb=%d\n",
                dwSkyDiagMode,stage,err,(int)(screen ? 0 : fbo->frameBuffer));
            DW_SkyDiagAppend(line);
            ri.Printf(PRINT_WARNING,"DW_SKY_DIAG_READBACK_FAILED %s GL=0x%x\n",stage,err);
        }
    }
    dwSkyDiagGLPixelStorei(GL_PACK_ALIGNMENT,oldPack);
    GL_BindFramebuffer(GL_READ_FRAMEBUFFER,oldRead);
    dwSkyDiagGLReadBuffer(oldBuffer);
    if (rgba) ri.Hunk_FreeTempMemory(rgba);
    ri.Hunk_FreeTempMemory(out);
    return err==GL_NO_ERROR ? qtrue : qfalse;
}

static int DW_SkyDiagCaptureNow(void)
{
    return dwSkyDiagAuto && dwSkyDiagAuto->integer && dwSkyDiagArmed &&
        dwSkyDiagMode<DW_SKY_DIAG_MODES &&
        ri.Milliseconds()-dwSkyDiagModeStartMs>=DW_SKY_DIAG_CAPTURE_DELAY_MS &&
        dwSkyDiagWorldSeen;
}

int DW_SkyDiagMode(void)
{
    if (!dwSkyDiagAuto || !dwSkyDiagAuto->integer || !dwSkyDiagArmed ||
        dwSkyDiagMode>=DW_SKY_DIAG_MODES ||
        (backEnd.viewParms.flags & (VPF_SHADOWMAP|VPF_DEPTHSHADOW)) ||
        backEnd.depthFill) return -1;
    return dwSkyDiagMode;
}

/* Sky may be rendered in an RDF_SKYBOXPORTAL auxiliary view rather than
 * the main view. Log both views even when main-view's worldSeen is false.
 * Never emit a line per-frame; one line per phase per mode. */
void DW_SkyDiagSkyProbe(int phase)
{
    char line[384];
    unsigned bit;
    if (!dwSkyDiagAuto || !dwSkyDiagAuto->integer || !dwSkyDiagArmed ||
        dwSkyDiagMode>=DW_SKY_DIAG_MODES || phase<0 || phase>6) return;
    bit=1u<<(unsigned)phase;
    if (dwSkyDiagProbeBits & bit) return;
    dwSkyDiagProbeBits |= bit;
    Com_sprintf(line,sizeof(line),
      "SKY_PROBE,mode=%d,phase=%d,portalSky=%d,rdflags=%d,viewPortal=%d,depthFill=%d,target=%s,worldSeen=%d\n",
      dwSkyDiagMode,phase,skyboxportal,backEnd.refdef.rdflags,
      backEnd.viewParms.isPortal,backEnd.depthFill,
      glState.currentFBO ? glState.currentFBO->name : "screen",dwSkyDiagWorldSeen);
    DW_SkyDiagAppend(line);
    DW_SkyDiagFlush();
}

void DW_SkyDiagControlUsed(int mode)
{
    char line[180];
    if (!dwSkyDiagArmed || dwSkyDiagMode!=mode) return;
    ++dwSkyDiagControlCalls;
    if (dwSkyDiagControlCalls!=1) return;
    Com_sprintf(line,sizeof(line),"SKY_CONTROL_APPLIED,mode=%d,portalSky=%d,rdflags=%d\n",
                dwSkyDiagMode,skyboxportal,backEnd.refdef.rdflags);
    DW_SkyDiagAppend(line);
    DW_SkyDiagFlush();
}

static void DW_SkyDiagBeginView(void)
{
    const char *src;
    char line[512];
    int i;
    if (!dwSkyDiagAuto) dwSkyDiagAuto=ri.Cvar_Get("r_skyDiagAuto","0",CVAR_ARCHIVE);
    if (!dwSkyDiagArm) dwSkyDiagArm=ri.Cvar_Get("r_skyDiagArm","0",0);
    if (!dwSkyDiagAuto->integer || !tr.world ||
        (backEnd.viewParms.flags & (VPF_SHADOWMAP|VPF_DEPTHSHADOW)) ||
        backEnd.viewParms.isPortal ||
        (backEnd.refdef.rdflags & (RDF_NOWORLDMODEL|RDF_SKYBOXPORTAL))) return;
    src=tr.world->baseName;
    if (!src || !src[0]) return;
    if (Q_stricmp(dwSkyDiagMap,src)) {
        if (dwSkyDiagMap[0]) DW_SkyDiagFlush();
        Q_strncpyz(dwSkyDiagMap,src,sizeof(dwSkyDiagMap));
        for (i=0;dwSkyDiagMap[i];++i)
            if (!((dwSkyDiagMap[i]>='a' && dwSkyDiagMap[i]<='z') ||
                  (dwSkyDiagMap[i]>='A' && dwSkyDiagMap[i]<='Z') ||
                  (dwSkyDiagMap[i]>='0' && dwSkyDiagMap[i]<='9'))) dwSkyDiagMap[i]='_';
        dwSkyDiagArmed=0;
        dwSkyDiagMode=dwSkyDiagTimeouts=dwSkyDiagCameraMotion=0;
        DW_SkyDiagResetModeFlags();
        DW_SkyDiagNewTrace();
        Com_sprintf(line,sizeof(line),"MAP_READY,%s,press_F8_when_sky_dash_is_visible\n",dwSkyDiagMap);
        DW_SkyDiagAppend(line);
        DW_SkyDiagFlush();
        ri.Printf(PRINT_ALL,"DW_SKY_DIAG_READY map=%s: look at defect and press F8\n",dwSkyDiagMap);
        ri.Cvar_Set("r_skyDiagArm","0");
        return;
    }
    if (dwSkyDiagArm->integer) {
        dwSkyDiagArmed=1;
        dwSkyDiagMode=dwSkyDiagTimeouts=dwSkyDiagCameraMotion=0;
        DW_SkyDiagResetModeFlags();
        DW_SkyDiagNewTrace();
        dwSkyDiagModeStartMs=ri.Milliseconds();
        VectorCopy(backEnd.viewParms.or.origin,dwSkyDiagCameraOrigin);
        VectorCopy(backEnd.viewParms.or.axis[0],dwSkyDiagCameraForward);
        Com_sprintf(line,sizeof(line),"RUN_STARTED,map=%s,origin=%.3f:%.3f:%.3f,forward=%.6f:%.6f:%.6f\n",
            dwSkyDiagMap,dwSkyDiagCameraOrigin[0],dwSkyDiagCameraOrigin[1],dwSkyDiagCameraOrigin[2],
            dwSkyDiagCameraForward[0],dwSkyDiagCameraForward[1],dwSkyDiagCameraForward[2]);
        DW_SkyDiagAppend(line);
        ri.Cvar_Set("r_skyDiagArm","0");
        ri.Printf(PRINT_ALL,"DW_SKY_DIAG_ARMED map=%s: keep camera still for 12s\n",dwSkyDiagMap);
    }
    if (!dwSkyDiagArmed || dwSkyDiagMode>=DW_SKY_DIAG_MODES) return;
    dwSkyDiagWorldSeen=1;
    if (!dwSkyDiagModeLogged) {
        dwSkyDiagModeLogged=1;
        Com_sprintf(line,sizeof(line),"MODE_START,%d,%d,map=%s,screen=%dx%d,hdr=%d,post=%d,requestedMsaa=%d,clear=%d\n",
            dwSkyDiagMode,dwSkyDiagFrame,dwSkyDiagMap,glConfig.vidWidth,glConfig.vidHeight,
            r_hdr->integer,r_postProcess->integer,r_ext_framebuffer_multisample->integer,r_clear->integer);
        DW_SkyDiagAppend(line);
        DW_SkyDiagEvent("MAIN_VIEW_START");
        DW_SkyDiagFlush();
    }
    if (dwSkyDiagCameraMotion < 3) {
        vec3_t delta;
        float dot;
        VectorSubtract(backEnd.viewParms.or.origin,dwSkyDiagCameraOrigin,delta);
        dot=DotProduct(backEnd.viewParms.or.axis[0],dwSkyDiagCameraForward);
        if (DotProduct(delta,delta)>256.0f || dot<0.998f) {
            ++dwSkyDiagCameraMotion;
            Com_sprintf(line,sizeof(line),"CAMERA_MOTION,%d,frame=%d,dist2=%.2f,cos=%.5f\n",
                dwSkyDiagMode,dwSkyDiagFrame,DotProduct(delta,delta),dot);
            DW_SkyDiagAppend(line);
        }
    }
    if (dwSkyDiagMode==1 && tr.renderFbo && glState.currentFBO==tr.renderFbo) {
        qglClearColor(1.0f,0.0f,0.5f,1.0f);
        qglClear(GL_COLOR_BUFFER_BIT);
        qglClearColor(0.0f,0.0f,0.0f,1.0f);
    }
}

void DW_SkyDiagSkyStage(void)
{
    GLint sc[4]={0};
    if (!dwSkyDiagAuto || !dwSkyDiagAuto->integer || !dwSkyDiagArmed ||
        dwSkyDiagMode>=DW_SKY_DIAG_MODES) return;
    if (!dwSkyDiagSkySeen) {
        dwSkyDiagSkySeen=1;
        DW_SkyDiagEvent("SKY_STAGE_PRESENT");
        DW_SkyDiagFlush();
    }
    /* Portal sky can be drawn before main world (worldSeen=0).
     * Capture it when possible; downstream mandatory captures have NO
     * dependency on the sky stage event. */
    if (ri.Milliseconds()-dwSkyDiagModeStartMs < DW_SKY_DIAG_CAPTURE_DELAY_MS ||
        dwSkyDiagSkyCaptureDone || !tr.msaaResolveFbo || !tr.renderFbo ||
        glState.currentFBO!=tr.renderFbo) return;
    qglGetIntegerv(GL_SCISSOR_BOX,sc);
    DW_SkyDiagEvent("SKY_BEFORE_RESOLVE");
    FBO_FastBlit(tr.renderFbo,NULL,tr.msaaResolveFbo,NULL,GL_COLOR_BUFFER_BIT,GL_NEAREST);
    if (DW_SkyDiagRead(tr.msaaResolveFbo,"sky_early",0,0)) {
        dwSkyDiagSkyCaptureDone=1;
        DW_SkyDiagAppend("SKY_EARLY_SOURCE,TRUE_SKY_ITERATOR\n");
    }
    FBO_Bind(tr.renderFbo);
    qglScissor(sc[0],sc[1],sc[2],sc[3]);
    DW_SkyDiagFlush();
}

/* Guaranteed independent fallback for early scene color at RB_PostProcess:
 * samples are resolved for CPU readback, not raw individual MSAA samples.
 * This stage is pre-postprocess, NOT necessarily a sky-only frame. */
static void DW_SkyDiagPreResolve(void)
{
    GLint sc[4]={0};
    FBO_t *saved;
    if (!DW_SkyDiagCaptureNow()) return;
    if (dwSkyDiagPreResolveCalls++==0) {
        DW_SkyDiagEvent("PRE_RESOLVE_ENTER");
        DW_SkyDiagFlush();
    }
    if (dwSkyDiagSkyCaptureDone) return;
    if (!tr.renderFbo || !tr.msaaResolveFbo) {
        DW_SkyDiagAppend("ERROR,PRE_RESOLVE_NO_MSAA_FBO\n");
        DW_SkyDiagFlush();
        return;
    }
    saved=glState.currentFBO;
    qglGetIntegerv(GL_SCISSOR_BOX,sc);
    FBO_FastBlit(tr.renderFbo,NULL,tr.msaaResolveFbo,NULL,GL_COLOR_BUFFER_BIT,GL_NEAREST);
    if (DW_SkyDiagRead(tr.msaaResolveFbo,"sky_early",0,0)) {
        dwSkyDiagSkyCaptureDone=1;
        DW_SkyDiagAppend("SKY_EARLY_SOURCE,FALLBACK_PRE_POST_SCENE_NOT_SKY_ONLY\n");
    }
    FBO_Bind(saved);
    qglScissor(sc[0],sc[1],sc[2],sc[3]);
    DW_SkyDiagFlush();
}

static void DW_SkyDiagAfterResolve(FBO_t *resolved)
{
    char line[400];
    if (!DW_SkyDiagCaptureNow() || !resolved) return;
    if (!dwSkyDiagHdrDone || !dwSkyDiagDepthDone) {
        DW_SkyDiagEvent("POST_MSAA_RESOLVE");
        if (!dwSkyDiagHdrDone)
            dwSkyDiagHdrDone=DW_SkyDiagRead(resolved,"resolved_hdr",0,0);
        if (!dwSkyDiagDepthDone)
            dwSkyDiagDepthDone=DW_SkyDiagRead(resolved,"resolved_depth",1,0);
        Com_sprintf(line,sizeof(line),"CAMERA,%d,%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,skySeen=%d\n",
            dwSkyDiagMode,dwSkyDiagFrame,backEnd.viewParms.or.origin[0],backEnd.viewParms.or.origin[1],backEnd.viewParms.or.origin[2],
            backEnd.viewParms.or.axis[0][0],backEnd.viewParms.or.axis[0][1],backEnd.viewParms.or.axis[0][2],dwSkyDiagSkySeen);
        DW_SkyDiagAppend(line);
        DW_SkyDiagFlush();
    }
}

static void DW_SkyDiagOnSwap(void)
{
    char line[400];
    int elapsed,all;
    if (!dwSkyDiagAuto || !dwSkyDiagAuto->integer || !dwSkyDiagArmed ||
        !dwSkyDiagWorldSeen || dwSkyDiagMode>=DW_SKY_DIAG_MODES) return;
    if (DW_SkyDiagCaptureNow() && !dwSkyDiagFinalCaptureDone) {
        DW_SkyDiagEvent("FINAL_SCREEN");
        dwSkyDiagFinalCaptureDone=DW_SkyDiagRead(NULL,"final",0,1);
    }
    ++dwSkyDiagFrame;
    elapsed=ri.Milliseconds()-dwSkyDiagModeStartMs;
    all=dwSkyDiagSkyCaptureDone && dwSkyDiagHdrDone && dwSkyDiagDepthDone && dwSkyDiagFinalCaptureDone;
    if ((all && elapsed>=DW_SKY_DIAG_MODE_DURATION_MS) || elapsed>=DW_SKY_DIAG_MODE_TIMEOUT_MS) {
        Com_sprintf(line,sizeof(line),
            "MODE_FINISHED,%d,frames=%d,elapsedMs=%d,sky=%d,early=%d,hdr=%d,depth=%d,final=%d,complete=%d,cameraMotion=%d\n",
            dwSkyDiagMode,dwSkyDiagFrame,elapsed,dwSkyDiagSkySeen,
            dwSkyDiagSkyCaptureDone,dwSkyDiagHdrDone,dwSkyDiagDepthDone,dwSkyDiagFinalCaptureDone,all,dwSkyDiagCameraMotion);
        DW_SkyDiagAppend(line);
        if (!dwSkyDiagSkySeen) {
            Com_sprintf(line,sizeof(line),"SKY_STAGE_NOT_OBSERVED,mode=%d,portalSky=%d,skyProbes=%d\n",
                        dwSkyDiagMode,skyboxportal,dwSkyDiagProbeBits);
            DW_SkyDiagAppend(line);
        }
        if (!all) {++dwSkyDiagTimeouts; ri.Printf(PRINT_WARNING,"DW_SKY_DIAG_CAPTURE_INCOMPLETE mode=%d\n",dwSkyDiagMode);}
        ++dwSkyDiagMode;
        DW_SkyDiagResetModeFlags();
        dwSkyDiagModeStartMs=ri.Milliseconds();
        if (dwSkyDiagMode>=DW_SKY_DIAG_MODES) {
            Com_sprintf(line,sizeof(line),"RUN_COMPLETE,5,failures=%d,glErrors=%d,maxRealSamples=%d,cameraMotion=%d,traceOverflow=%d\n",
                dwSkyDiagTimeouts,dwSkyDiagReadErrors,dwSkyDiagSamples,dwSkyDiagCameraMotion,dwSkyDiagTraceOverrun);
            DW_SkyDiagAppend(line);
            DW_SkyDiagFlush();
            ri.Printf(PRINT_ALL,"DW_SKY_DIAG_COMPLETE map=%s failures=%d. Change map or exit game.\n",dwSkyDiagMap,dwSkyDiagTimeouts);
        } else {
            DW_SkyDiagFlush();
            ri.Printf(PRINT_ALL,"DW_SKY_DIAG_MODE map=%s mode=%d\n",dwSkyDiagMap,dwSkyDiagMode);
        }
    }
    dwSkyDiagWorldSeen=0;
}
#endif /* DARKWOLF_SKY_DIAG_RUNTIME_H */
