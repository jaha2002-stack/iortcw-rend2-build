#!/usr/bin/env python3
from pathlib import Path
import argparse, json

ap=argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("--proof")
args=ap.parse_args()

sp=Path(args.source)/"SP"
root=sp/"code/rend2"

def read(rel):
    p=root/rel
    return p,p.read_text()

def replace_once(s, old, new, label):
    n=s.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {n}")
    return s.replace(old,new,1)

changed=[]

# ---------------------------------------------------------------------------
# Dedicated shaders: GPU GGX environment prefilter and split-sum BRDF LUT.
# ---------------------------------------------------------------------------
vp=r'''attribute vec3 attr_Position;
attribute vec4 attr_TexCoord0;

uniform mat4 u_ModelViewProjectionMatrix;
varying vec2 var_Tex1;

void main()
{
    gl_Position = u_ModelViewProjectionMatrix * vec4(attr_Position, 1.0);
    var_Tex1 = attr_TexCoord0.st;
}
'''

prefilter_fp=r'''uniform samplerCube u_CubeMap;
// x = cubemap face [0..5], y = destination roughness,
// z = source cubemap resolution, w = sample count.
uniform vec4 u_Color;
varying vec2 var_Tex1;

#define DW_PI 3.14159265358979323846
#define DW_MAX_PREFILTER_SAMPLES 256

vec3 DW_SRGBToLinear(vec3 c)
{
    vec3 lo = c / 12.92;
    vec3 hi = pow((c + vec3(0.055)) / 1.055, vec3(2.4));
    return mix(lo, hi, step(vec3(0.04045), c));
}

vec2 DW_R2Sequence(int i)
{
    // Generalized golden-ratio low-discrepancy sequence.
    float fi = float(i) + 0.5;
    return fract(vec2(0.5) + fi * vec2(0.7548776662466927, 0.5698402909980532));
}

vec3 DW_FaceDirection(float face, vec2 uv)
{
    vec2 p = uv * 2.0 - 1.0;
    if (face < 0.5) return normalize(vec3( 1.0, -p.y, -p.x));
    if (face < 1.5) return normalize(vec3(-1.0, -p.y,  p.x));
    if (face < 2.5) return normalize(vec3( p.x,  1.0,  p.y));
    if (face < 3.5) return normalize(vec3( p.x, -1.0, -p.y));
    if (face < 4.5) return normalize(vec3( p.x, -p.y,  1.0));
    return normalize(vec3(-p.x, -p.y, -1.0));
}

float DW_DistributionGGX(float NoH, float roughness)
{
    float a = max(roughness * roughness, 0.0025);
    float a2 = a * a;
    float d = NoH * NoH * (a2 - 1.0) + 1.0;
    return a2 / max(DW_PI * d * d, 1e-7);
}

vec3 DW_ImportanceSampleGGX(vec2 Xi, vec3 N, float roughness)
{
    float a = max(roughness * roughness, 0.0025);
    float a2 = a * a;
    float phi = 2.0 * DW_PI * Xi.x;
    float cosTheta = sqrt((1.0 - Xi.y) / max(1.0 + (a2 - 1.0) * Xi.y, 1e-7));
    float sinTheta = sqrt(max(1.0 - cosTheta * cosTheta, 0.0));

    vec3 Ht = vec3(cos(phi) * sinTheta, sin(phi) * sinTheta, cosTheta);
    vec3 up = abs(N.z) < 0.999 ? vec3(0.0,0.0,1.0) : vec3(1.0,0.0,0.0);
    vec3 tangent = normalize(cross(up, N));
    vec3 bitangent = cross(N, tangent);
    return normalize(tangent * Ht.x + bitangent * Ht.y + N * Ht.z);
}

void main()
{
    float face = floor(u_Color.x + 0.5);
    float roughness = clamp(u_Color.y, 0.0, 1.0);
    float sourceResolution = max(u_Color.z, 1.0);
    int sampleCount = int(clamp(u_Color.w, 1.0, float(DW_MAX_PREFILTER_SAMPLES)) + 0.5);

    vec3 N = DW_FaceDirection(face, var_Tex1);
    vec3 V = N;

    if (roughness < 0.0005)
    {
        vec3 c = textureCubeLod(u_CubeMap, N, 0.0).rgb;
        gl_FragColor = vec4(DW_SRGBToLinear(c), 1.0);
        return;
    }

    vec3 prefiltered = vec3(0.0);
    float totalWeight = 0.0;

    for (int i = 0; i < DW_MAX_PREFILTER_SAMPLES; ++i)
    {
        if (i >= sampleCount) break;

        vec2 Xi = DW_R2Sequence(i);
        vec3 H = DW_ImportanceSampleGGX(Xi, N, roughness);
        vec3 L = normalize(2.0 * dot(V, H) * H - V);

        float NoL = max(dot(N, L), 0.0);
        if (NoL > 0.0)
        {
            // Always sample the raw environment at LOD0. Its legacy mip chain is
            // generated in the texture's encoded/sRGB value space, so using those
            // mips would bias radiance before DW_SRGBToLinear(). Deterministic
            // 256-sample GGX integration from level 0 keeps the convolution itself
            // in linear radiance space and avoids hidden gamma-space averaging.
            vec3 c = textureCubeLod(u_CubeMap, L, 0.0).rgb;
            prefiltered += DW_SRGBToLinear(c) * NoL;
            totalWeight += NoL;
        }
    }

    gl_FragColor = vec4(prefiltered / max(totalWeight, 1e-6), 1.0);
}
'''

brdf_fp=r'''// Full split-sum GGX DFG integration LUT.
// var_Tex1.x = NdotV, var_Tex1.y = perceptual roughness.
uniform vec4 u_Color; // x = sample count
varying vec2 var_Tex1;

#define DW_PI 3.14159265358979323846
#define DW_MAX_BRDF_SAMPLES 512

vec2 DW_R2Sequence(int i)
{
    float fi = float(i) + 0.5;
    return fract(vec2(0.5) + fi * vec2(0.7548776662466927, 0.5698402909980532));
}

vec3 DW_ImportanceSampleGGX(vec2 Xi, vec3 N, float roughness)
{
    float a = max(roughness * roughness, 0.0025);
    float a2 = a * a;
    float phi = 2.0 * DW_PI * Xi.x;
    float cosTheta = sqrt((1.0 - Xi.y) / max(1.0 + (a2 - 1.0) * Xi.y, 1e-7));
    float sinTheta = sqrt(max(1.0 - cosTheta * cosTheta, 0.0));

    vec3 Ht = vec3(cos(phi) * sinTheta, sin(phi) * sinTheta, cosTheta);
    vec3 up = abs(N.z) < 0.999 ? vec3(0.0,0.0,1.0) : vec3(1.0,0.0,0.0);
    vec3 tangent = normalize(cross(up, N));
    vec3 bitangent = cross(N, tangent);
    return normalize(tangent * Ht.x + bitangent * Ht.y + N * Ht.z);
}

float DW_VisibilitySmithGGXCorrelated(float NoV, float NoL, float roughness)
{
    // Match the correlated Smith visibility used by the runtime direct-light GGX
    // path. The LUT therefore integrates the same microfacet model instead of a
    // Schlick geometry approximation.
    float a = max(roughness * roughness, 0.0025);
    float a2 = a * a;
    float gv = NoL * sqrt(max(NoV * NoV * (1.0 - a2) + a2, 1e-7));
    float gl = NoV * sqrt(max(NoL * NoL * (1.0 - a2) + a2, 1e-7));
    return 0.5 / max(gv + gl, 1e-7);
}

vec2 DW_IntegrateBRDF(float NoV, float roughness, int sampleCount)
{
    vec3 V = vec3(sqrt(max(1.0 - NoV * NoV, 0.0)), 0.0, NoV);
    vec3 N = vec3(0.0,0.0,1.0);
    float A = 0.0;
    float B = 0.0;

    for (int i = 0; i < DW_MAX_BRDF_SAMPLES; ++i)
    {
        if (i >= sampleCount) break;

        vec2 Xi = DW_R2Sequence(i);
        vec3 H = DW_ImportanceSampleGGX(Xi, N, roughness);
        vec3 L = normalize(2.0 * dot(V, H) * H - V);

        float NoL = max(L.z, 0.0);
        float NoH = max(H.z, 0.0);
        float VoH = max(dot(V, H), 0.0);

        if (NoL > 0.0)
        {
            float Vis = DW_VisibilitySmithGGXCorrelated(NoV, NoL, roughness);
            // With GGX half-vector importance sampling:
            // f_s * NoL / pdf = F * (4 * Vis * NoL * VoH / NoH).
            float GVis = (4.0 * Vis * NoL * VoH) / max(NoH, 1e-6);
            float Fc = pow(1.0 - VoH, 5.0);
            A += (1.0 - Fc) * GVis;
            B += Fc * GVis;
        }
    }

    return vec2(A, B) / float(sampleCount);
}

void main()
{
    float NoV = clamp(var_Tex1.x, 0.001, 0.999);
    float roughness = clamp(var_Tex1.y, 0.001, 1.0);
    int sampleCount = int(clamp(u_Color.x, 1.0, float(DW_MAX_BRDF_SAMPLES)) + 0.5);
    vec2 integrated = DW_IntegrateBRDF(NoV, roughness, sampleCount);
    gl_FragColor = vec4(integrated, 0.0, 1.0);
}
'''

for name,data in (
    ("glsl/iblprefilter_vp.glsl",vp),
    ("glsl/iblprefilter_fp.glsl",prefilter_fp),
    ("glsl/iblbrdflut_vp.glsl",vp),
    ("glsl/iblbrdflut_fp.glsl",brdf_fp),
):
    p=root/name
    p.write_text(data)
    changed.append("SP/code/rend2/"+name)

# ---------------------------------------------------------------------------
# Makefile: stringify/link the new embedded fallback shaders.
# ---------------------------------------------------------------------------
p=sp/"Makefile"
s=p.read_text()
old='''  $(B)/rend2/glsl/lightall_fp.o \
'''
new='''  $(B)/rend2/glsl/iblprefilter_fp.o \
  $(B)/rend2/glsl/iblprefilter_vp.o \
  $(B)/rend2/glsl/iblbrdflut_fp.o \
  $(B)/rend2/glsl/iblbrdflut_vp.o \
  $(B)/rend2/glsl/lightall_fp.o \
'''
s=replace_once(s,old,new,"Makefile embedded IBL shaders")
p.write_text(s); changed.append("SP/Makefile")

# ---------------------------------------------------------------------------
# tr_local.h: sampler slot, uniform, resources, command, cubemap destination.
# ---------------------------------------------------------------------------
p,s=read("tr_local.h")
old='''	TB_CUBEMAP     = 6,
	TB_SHADOWMAP4  = 6,
	NUM_TEXTURE_BUNDLES = 7
'''
new='''	TB_CUBEMAP     = 6,
	TB_SHADOWMAP4  = 6,
	TB_BRDFLUT     = 7, // DarkWolf PBR V3.1 split-sum BRDF integration LUT
	NUM_TEXTURE_BUNDLES = 8
'''
s=replace_once(s,old,new,"texture bundle slot")

old='''	UNIFORM_TEXTUREMAP,
	UNIFORM_LEVELSMAP,
	UNIFORM_CUBEMAP,

	UNIFORM_SCREENIMAGEMAP,
'''
new='''	UNIFORM_TEXTUREMAP,
	UNIFORM_LEVELSMAP,
	UNIFORM_CUBEMAP,
	UNIFORM_BRDFLUT,

	UNIFORM_SCREENIMAGEMAP,
'''
s=replace_once(s,old,new,"BRDF LUT uniform enum")

old='''typedef struct cubemap_s {
	char name[MAX_QPATH];
	vec3_t origin;
	float parallaxRadius;
	image_t *image;
} cubemap_t;
'''
new='''typedef struct cubemap_s {
	char name[MAX_QPATH];
	vec3_t origin;
	float parallaxRadius;
	image_t *image;             // raw/load/capture environment cubemap
	image_t *prefilteredImage;  // PBR V3.1 linear GGX prefiltered specular mip chain
} cubemap_t;
'''
s=replace_once(s,old,new,"cubemap prefiltered resource")

old='''	image_t                 *renderCubeImage;
	
	image_t					*textureDepthImage;
'''
new='''	image_t                 *renderCubeImage;
	image_t                 *pbrBrdfLutImage; // PBR V3.1 full split-sum GGX DFG integration LUT
	qboolean                pbrBrdfLutReady;
	
	image_t					*textureDepthImage;
'''
s=replace_once(s,old,new,"renderer BRDF image")

old='''	FBO_t                   *renderCubeFbo;
	FBO_t                   *dlightShadowFbo; // REND2_PRODUCTION_POLISH_V6_1
'''
new='''	FBO_t                   *renderCubeFbo;
	FBO_t                   *pbrIblFbo; // PBR V3.1 shared BRDF-LUT / cubemap prefilter FBO
	FBO_t                   *dlightShadowFbo; // REND2_PRODUCTION_POLISH_V6_1
'''
s=replace_once(s,old,new,"renderer IBL FBO")

old='''	shaderProgram_t textureColorShader;
	shaderProgram_t dlightDebugCubeShader;
'''
new='''	shaderProgram_t textureColorShader;
	shaderProgram_t pbrPrefilterShader; // PBR V3.1 GPU GGX cubemap convolution
	shaderProgram_t pbrBrdfLutShader;   // PBR V3.1 split-sum DFG integration
	shaderProgram_t dlightDebugCubeShader;
'''
s=replace_once(s,old,new,"renderer IBL programs")

old='''typedef struct {
	int commandId;
} exportCubemapsCommand_t;

typedef enum {
'''
new='''typedef struct {
	int commandId;
} exportCubemapsCommand_t;

typedef struct {
	int commandId;
} pbrIblBuildCommand_t;

typedef enum {
'''
s=replace_once(s,old,new,"IBL command struct")

old='''	RC_POSTPROCESS,
	RC_EXPORT_CUBEMAPS
} renderCommand_t;
'''
new='''	RC_POSTPROCESS,
	RC_EXPORT_CUBEMAPS,
	RC_PBR_IBL_BUILD
} renderCommand_t;
'''
s=replace_once(s,old,new,"IBL command enum")

old='''void R_AddPostProcessCmd (void);
'''
new='''void R_AddPostProcessCmd (void);
void R_AddPbrIblBuildCmd(void);
'''
s=replace_once(s,old,new,"IBL command prototype")

p.write_text(s); changed.append("SP/code/rend2/tr_local.h")

# ---------------------------------------------------------------------------
# tr_fbo: attachment at arbitrary mip level, required for GGX mip rendering.
# ---------------------------------------------------------------------------
p,s=read("tr_fbo.h")
old='''void FBO_AttachImage(FBO_t *fbo, image_t *image, GLenum attachment, GLuint cubemapside);
'''
new='''void FBO_AttachImage(FBO_t *fbo, image_t *image, GLenum attachment, GLuint cubemapside);
void FBO_AttachImageLevel(FBO_t *fbo, image_t *image, GLenum attachment, GLuint cubemapside, GLint mipLevel);
'''
s=replace_once(s,old,new,"FBO level prototype")
p.write_text(s); changed.append("SP/code/rend2/tr_fbo.h")

p,s=read("tr_fbo.c")
old='''void FBO_AttachImage(FBO_t *fbo, image_t *image, GLenum attachment, GLuint cubemapside)
{
	GLenum target = GL_TEXTURE_2D;
	int index;

	if (image->flags & IMGFLAG_CUBEMAP)
		target = GL_TEXTURE_CUBE_MAP_POSITIVE_X_ARB + cubemapside;

	qglNamedFramebufferTexture2DEXT(fbo->frameBuffer, attachment, target, image->texnum, 0);
	index = attachment - GL_COLOR_ATTACHMENT0;
	if (index >= 0 && index <= 15)
		fbo->colorImage[index] = image;
}
'''
new='''void FBO_AttachImageLevel(FBO_t *fbo, image_t *image, GLenum attachment, GLuint cubemapside, GLint mipLevel)
{
	GLenum target = GL_TEXTURE_2D;
	int index;

	if (image->flags & IMGFLAG_CUBEMAP)
		target = GL_TEXTURE_CUBE_MAP_POSITIVE_X_ARB + cubemapside;

	qglNamedFramebufferTexture2DEXT(fbo->frameBuffer, attachment, target, image->texnum, mipLevel);
	index = attachment - GL_COLOR_ATTACHMENT0;
	if (index >= 0 && index <= 15)
		fbo->colorImage[index] = image;
}

void FBO_AttachImage(FBO_t *fbo, image_t *image, GLenum attachment, GLuint cubemapside)
{
	FBO_AttachImageLevel(fbo, image, attachment, cubemapside, 0);
}
'''
s=replace_once(s,old,new,"FBO arbitrary mip attachment")
p.write_text(s); changed.append("SP/code/rend2/tr_fbo.c")

# ---------------------------------------------------------------------------
# Builtin BRDF target and shared IBL FBO.
# ---------------------------------------------------------------------------
p,s=read("tr_image.c")
old='''		if (r_cubeMapping->integer)
		{
			tr.renderCubeImage = R_CreateImage("*renderCube", NULL, r_cubemapSize->integer, r_cubemapSize->integer, IMGTYPE_COLORALPHA, IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE | IMGFLAG_MIPMAP | IMGFLAG_CUBEMAP, rgbFormat);
		}
'''
new='''		if (r_cubeMapping->integer)
		{
			tr.renderCubeImage = R_CreateImage("*renderCube", NULL, r_cubemapSize->integer, r_cubemapSize->integer, IMGTYPE_COLORALPHA, IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE | IMGFLAG_MIPMAP | IMGFLAG_CUBEMAP, rgbFormat);
		}

		// DarkWolf PBR V3.1: small persistent float target for the split-sum DFG LUT.
		// Allocate independently of r_pbr so a vid_restart after changing r_pbr never
		// depends on stale renderer-state allocation order.
		if (glRefConfig.textureFloat && glConfig.numTextureUnits >= 8)
		{
			tr.pbrBrdfLutImage = R_CreateImage("*pbrBrdfLut", NULL, 256, 256,
				IMGTYPE_COLORALPHA, IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE, GL_RGBA16F_ARB);
			qglTextureParameterfEXT(tr.pbrBrdfLutImage->texnum, GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
			qglTextureParameterfEXT(tr.pbrBrdfLutImage->texnum, GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
		}
'''
s=replace_once(s,old,new,"BRDF LUT image allocation")
p.write_text(s); changed.append("SP/code/rend2/tr_image.c")

p,s=read("tr_fbo.c")
old='''	if (tr.renderCubeImage)
	{
		tr.renderCubeFbo = FBO_Create("_renderCubeFbo", tr.renderCubeImage->width, tr.renderCubeImage->height);
		FBO_AttachImage(tr.renderCubeFbo, tr.renderCubeImage, GL_COLOR_ATTACHMENT0, 0);
		FBO_CreateBuffer(tr.renderCubeFbo, GL_DEPTH_COMPONENT24_ARB, 0, 0);
		R_CheckFBO(tr.renderCubeFbo);
	}
'''
new='''	if (tr.renderCubeImage)
	{
		tr.renderCubeFbo = FBO_Create("_renderCubeFbo", tr.renderCubeImage->width, tr.renderCubeImage->height);
		FBO_AttachImage(tr.renderCubeFbo, tr.renderCubeImage, GL_COLOR_ATTACHMENT0, 0);
		FBO_CreateBuffer(tr.renderCubeFbo, GL_DEPTH_COMPONENT24_ARB, 0, 0);
		R_CheckFBO(tr.renderCubeFbo);
	}

	if (tr.pbrBrdfLutImage)
	{
		int iblSize = MAX(256, r_cubemapSize->integer);
		tr.pbrIblFbo = FBO_Create("_pbrIblFbo", iblSize, iblSize);
		FBO_AttachImage(tr.pbrIblFbo, tr.pbrBrdfLutImage, GL_COLOR_ATTACHMENT0, 0);
		R_CheckFBO(tr.pbrIblFbo);
	}
'''
s=replace_once(s,old,new,"IBL FBO allocation")
p.write_text(s); changed.append("SP/code/rend2/tr_fbo.c")

# ---------------------------------------------------------------------------
# GLSL program registration + V3.1 capability define + BRDF sampler uniform.
# ---------------------------------------------------------------------------
p,s=read("tr_glsl.c")
old='''extern const char *fallbackShader_generic_vp;
extern const char *fallbackShader_generic_fp;
extern const char *fallbackShader_lightall_vp;
'''
new='''extern const char *fallbackShader_generic_vp;
extern const char *fallbackShader_generic_fp;
extern const char *fallbackShader_iblprefilter_vp;
extern const char *fallbackShader_iblprefilter_fp;
extern const char *fallbackShader_iblbrdflut_vp;
extern const char *fallbackShader_iblbrdflut_fp;
extern const char *fallbackShader_lightall_vp;
'''
s=replace_once(s,old,new,"IBL fallback externs")

old='''	{ "u_TextureMap", GLSL_INT },
	{ "u_LevelsMap",  GLSL_INT },
	{ "u_CubeMap",    GLSL_INT },

	{ "u_ScreenImageMap", GLSL_INT },
'''
new='''	{ "u_TextureMap", GLSL_INT },
	{ "u_LevelsMap",  GLSL_INT },
	{ "u_CubeMap",    GLSL_INT },
	{ "u_BRDFLut",    GLSL_INT },

	{ "u_ScreenImageMap", GLSL_INT },
'''
s=replace_once(s,old,new,"IBL uniform info")

old='''	if (r_pbr->integer >= 3)
	{
		Q_strcat(dest, size, "#define USE_PBR2_IBL_V3\\n");
		Q_strcat(dest, size, "#define USE_PBR2_BSP_RELIGHT_V4\\n");
	}
'''
new='''	if (r_pbr->integer >= 3)
	{
		if (glRefConfig.framebufferObject && glRefConfig.textureFloat && glConfig.numTextureUnits >= 8)
			Q_strcat(dest, size, "#define USE_PBR2_IBL_V31\\n");
		else
			Q_strcat(dest, size, "#define USE_PBR2_IBL_V3\\n");
		Q_strcat(dest, size, "#define USE_PBR2_BSP_RELIGHT_V4\\n");
	}
'''
s=replace_once(s,old,new,"V3.1 capability define")

# Programs after textureColor.
old='''	GLSL_FinishGPUShader(&tr.textureColorShader);

	numEtcShaders++;
'''
new='''	GLSL_FinishGPUShader(&tr.textureColorShader);

	numEtcShaders++;

	// DarkWolf PBR V3.1 true split-sum IBL preprocessing programs.
	if (glRefConfig.framebufferObject && glRefConfig.textureFloat && glConfig.numTextureUnits >= 8)
	{
		attribs = ATTR_POSITION | ATTR_TEXCOORD;
		extradefines[0] = '\\0';

		if (!GLSL_InitGPUShader(&tr.pbrPrefilterShader, "iblprefilter", attribs, qtrue, extradefines, qtrue,
			fallbackShader_iblprefilter_vp, fallbackShader_iblprefilter_fp))
		{
			ri.Error(ERR_FATAL, "Could not load PBR V3.1 GGX prefilter shader!");
		}
		GLSL_InitUniforms(&tr.pbrPrefilterShader);
		GLSL_SetUniformInt(&tr.pbrPrefilterShader, UNIFORM_CUBEMAP, TB_CUBEMAP);
		GLSL_FinishGPUShader(&tr.pbrPrefilterShader);
		numEtcShaders++;

		if (!GLSL_InitGPUShader(&tr.pbrBrdfLutShader, "iblbrdflut", attribs, qtrue, extradefines, qtrue,
			fallbackShader_iblbrdflut_vp, fallbackShader_iblbrdflut_fp))
		{
			ri.Error(ERR_FATAL, "Could not load PBR V3.1 BRDF integration shader!");
		}
		GLSL_InitUniforms(&tr.pbrBrdfLutShader);
		GLSL_FinishGPUShader(&tr.pbrBrdfLutShader);
		numEtcShaders++;
	}

'''
s=replace_once(s,old,new,"IBL shader program initialization")

old='''		GLSL_SetUniformInt(&tr.lightallShader[i], UNIFORM_CUBEMAP,     TB_CUBEMAP);
'''
new='''		GLSL_SetUniformInt(&tr.lightallShader[i], UNIFORM_CUBEMAP,     TB_CUBEMAP);
		GLSL_SetUniformInt(&tr.lightallShader[i], UNIFORM_BRDFLUT,     TB_BRDFLUT);
'''
s=replace_once(s,old,new,"lightall BRDF sampler")

old='''	GLSL_DeleteGPUShader(&tr.textureColorShader);
	GLSL_DeleteGPUShader(&tr.dlightDebugCubeShader);
'''
new='''	GLSL_DeleteGPUShader(&tr.textureColorShader);
	GLSL_DeleteGPUShader(&tr.pbrPrefilterShader);
	GLSL_DeleteGPUShader(&tr.pbrBrdfLutShader);
	GLSL_DeleteGPUShader(&tr.dlightDebugCubeShader);
'''
s=replace_once(s,old,new,"IBL shader shutdown")

p.write_text(s); changed.append("SP/code/rend2/tr_glsl.c")

# ---------------------------------------------------------------------------
# Lightall: use integrated LUT + GGX-preconvolved linear environment.
# ---------------------------------------------------------------------------
p,s=read("glsl/lightall_fp.glsl")
old='''#if defined(USE_CUBEMAP)
uniform samplerCube u_CubeMap;
#endif
'''
new='''#if defined(USE_CUBEMAP)
uniform samplerCube u_CubeMap;
  #if defined(USE_PBR2_IBL_V31)
uniform sampler2D u_BRDFLut;
  #endif
#endif
'''
s=replace_once(s,old,new,"BRDF LUT sampler declaration")

old='''  #if defined(USE_PBR2_IBL_V3)
	reflectance = DW_EnvironmentBRDFApprox(specular.rgb, roughness, NE);
  #else
	reflectance = EnvironmentBRDF(roughness, NE, specular.rgb);
  #endif
'''
new='''  #if defined(USE_PBR2_IBL_V31)
	// Full split-sum DFG integration: preintegrated visibility/Fresnel response.
	vec2 dwBrdf = texture2D(u_BRDFLut, vec2(clamp(NE, 0.001, 0.999), roughness)).rg;
	reflectance = specular.rgb * dwBrdf.x + vec3(dwBrdf.y);
  #elif defined(USE_PBR2_IBL_V3)
	reflectance = DW_EnvironmentBRDFApprox(specular.rgb, roughness, NE);
  #else
	reflectance = EnvironmentBRDF(roughness, NE, specular.rgb);
  #endif
'''
s=replace_once(s,old,new,"split-sum BRDF LUT sampling")

old='''  #if defined(USE_PBR2_IBL_V3)
	float dwCubeLod = ROUGHNESS_MIPS * roughness * roughness;
  #else
	float dwCubeLod = ROUGHNESS_MIPS * roughness;
  #endif
'''
new='''  #if defined(USE_PBR2_IBL_V31)
	// Destination mip i was explicitly convolved for roughness i/ROUGHNESS_MIPS.
	float dwCubeLod = ROUGHNESS_MIPS * roughness;
  #elif defined(USE_PBR2_IBL_V3)
	float dwCubeLod = ROUGHNESS_MIPS * roughness * roughness;
  #else
	float dwCubeLod = ROUGHNESS_MIPS * roughness;
  #endif
'''
s=replace_once(s,old,new,"prefilter roughness LOD")

old='''    #if defined(USE_PBR2)
	cubeLightColor = DW_SRGBToLinear(cubeLightColor);
    #elif defined(USE_PBR)
	cubeLightColor *= cubeLightColor;
    #endif
'''
new='''    #if defined(USE_PBR2_IBL_V31)
	// V3.1 prefiltered cubemap is RGBA16F and already stores linear radiance.
    #elif defined(USE_PBR2)
	cubeLightColor = DW_SRGBToLinear(cubeLightColor);
    #elif defined(USE_PBR)
	cubeLightColor *= cubeLightColor;
    #endif
'''
s=replace_once(s,old,new,"linear prefiltered cube sampling")

# V4.2 low-frequency directional guide uses the same prefiltered linear environment.
old='''		vec3 dwEnvN = DW_SRGBToLinear(textureCubeLod(u_CubeMap, N, ROUGHNESS_MIPS * 0.75).rgb);
		vec3 dwEnvMacro = DW_SRGBToLinear(textureCubeLod(u_CubeMap, surfNormal, ROUGHNESS_MIPS * 0.75).rgb);
'''
new='''  #if defined(USE_PBR2_IBL_V31)
		vec3 dwEnvN = textureCubeLod(u_CubeMap, N, ROUGHNESS_MIPS * 0.75).rgb;
		vec3 dwEnvMacro = textureCubeLod(u_CubeMap, surfNormal, ROUGHNESS_MIPS * 0.75).rgb;
  #else
		vec3 dwEnvN = DW_SRGBToLinear(textureCubeLod(u_CubeMap, N, ROUGHNESS_MIPS * 0.75).rgb);
		vec3 dwEnvMacro = DW_SRGBToLinear(textureCubeLod(u_CubeMap, surfNormal, ROUGHNESS_MIPS * 0.75).rgb);
  #endif
'''
s=replace_once(s,old,new,"V4.2 linear environment guide")

# GI-1 optional roughest-mip fill: V3.1 cubemap is already linear.
old='''    #if defined(USE_PBR)
		indirectSample *= indirectSample;
    #endif
'''
new='''    #if defined(USE_PBR2_IBL_V31)
		// already linear
    #elif defined(USE_PBR2)
		indirectSample = DW_SRGBToLinear(indirectSample);
    #elif defined(USE_PBR)
		indirectSample *= indirectSample;
    #endif
'''
s=replace_once(s,old,new,"GI1 V3.1 linear sampling")

p.write_text(s); changed.append("SP/code/rend2/glsl/lightall_fp.glsl")

# ---------------------------------------------------------------------------
# Bind prefiltered cube + BRDF LUT in normal lightall draws.
# ---------------------------------------------------------------------------
p,s=read("tr_shade.c")
old='''		if (!(tr.viewParms.flags & VPF_NOCUBEMAPS) && input->cubemapIndex && r_cubeMapping->integer)
		{
			vec4_t vec;
			cubemap_t *cubemap = &tr.cubemaps[input->cubemapIndex - 1];

			// FIXME: cubemap image could be NULL if cubemap isn't renderer or loaded
			if (cubemap->image)
				GL_BindToTMU( cubemap->image, TB_CUBEMAP);

			VectorSubtract(cubemap->origin, backEnd.viewParms.or.origin, vec);
'''
new='''		if (!(tr.viewParms.flags & VPF_NOCUBEMAPS) && input->cubemapIndex && r_cubeMapping->integer)
		{
			vec4_t vec;
			cubemap_t *cubemap = &tr.cubemaps[input->cubemapIndex - 1];
			image_t *environmentImage = cubemap->image;

			// PBR V3.1 uses the independently convolved linear radiance cubemap.
			// r_pbr 0/1/2 retain the original raw/ordinary-mip cubemap.
			if (r_pbr->integer >= 3 && cubemap->prefilteredImage && tr.pbrBrdfLutReady)
				environmentImage = cubemap->prefilteredImage;

			if (environmentImage)
				GL_BindToTMU(environmentImage, TB_CUBEMAP);

			if (r_pbr->integer >= 3 && tr.pbrBrdfLutReady && tr.pbrBrdfLutImage)
				GL_BindToTMU(tr.pbrBrdfLutImage, TB_BRDFLUT);

			VectorSubtract(cubemap->origin, backEnd.viewParms.or.origin, vec);
'''
s=replace_once(s,old,new,"prefiltered cube and LUT binding")
p.write_text(s); changed.append("SP/code/rend2/tr_shade.c")

# ---------------------------------------------------------------------------
# Allocate per-probe destination cubemaps and enqueue backend preprocessing.
# ---------------------------------------------------------------------------
p,s=read("tr_bsp.c")
old='''void R_RenderMissingCubemaps(void)
{
	int i, j;
'''
new='''static qboolean R_PbrV31IblAvailable(void)
{
	return r_pbr->integer >= 3 &&
		r_cubeMapping->integer &&
		glRefConfig.framebufferObject &&
		glRefConfig.textureFloat &&
		glConfig.numTextureUnits >= 8 &&
		tr.pbrBrdfLutImage &&
		tr.pbrIblFbo;
}

static void R_PreparePbrV31Cubemaps(void)
{
	int i;
	imgFlags_t flags = IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE |
		IMGFLAG_MIPMAP | IMGFLAG_NOLIGHTSCALE | IMGFLAG_CUBEMAP;

	if (!R_PbrV31IblAvailable())
		return;

	for (i = 0; i < tr.numCubemaps; ++i)
	{
		cubemap_t *cubemap = &tr.cubemaps[i];
		if (!cubemap->image || cubemap->prefilteredImage)
			continue;

		cubemap->prefilteredImage = R_CreateImage(va("*pbrV31Prefilter%d", i), NULL,
			r_cubemapSize->integer, r_cubemapSize->integer,
			IMGTYPE_COLORALPHA, flags, GL_RGBA16F_ARB);
		qglTextureParameterfEXT(cubemap->prefilteredImage->texnum, GL_TEXTURE_CUBE_MAP,
			GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
		qglTextureParameterfEXT(cubemap->prefilteredImage->texnum, GL_TEXTURE_CUBE_MAP,
			GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	}
}

void R_RenderMissingCubemaps(void)
{
	int i, j;
'''
s=replace_once(s,old,new,"PBR V3.1 cubemap resource preparation")

old='''		R_LoadCubemaps();
		R_RenderMissingCubemaps();
	}

    ri.FS_FreeFile( buffer.v );
'''
new='''		R_LoadCubemaps();
		R_RenderMissingCubemaps();

		// DarkWolf PBR V3.1: source cubemaps are now complete. Allocate a separate
		// float GGX mip chain for each probe and build all convolution resources on
		// the renderer backend before the first main-view draw.
		R_PreparePbrV31Cubemaps();
		if (R_PbrV31IblAvailable())
		{
			R_AddPbrIblBuildCmd();
			R_IssuePendingRenderCommands();
		}
	}

    ri.FS_FreeFile( buffer.v );
'''
s=replace_once(s,old,new,"enqueue IBL preprocessing")
p.write_text(s); changed.append("SP/code/rend2/tr_bsp.c")

# ---------------------------------------------------------------------------
# Front-end command enqueue.
# ---------------------------------------------------------------------------
p,s=read("tr_cmds.c")
anchor='''/*
=============
RE_SetColor
'''
insert='''/*
=============
R_AddPbrIblBuildCmd
=============
*/
void R_AddPbrIblBuildCmd(void)
{
	pbrIblBuildCommand_t *cmd = R_GetCommandBuffer(sizeof(*cmd));
	if (!cmd)
		return;
	cmd->commandId = RC_PBR_IBL_BUILD;
}


'''
if anchor not in s:
    raise SystemExit("tr_cmds command insertion anchor missing")
s=s.replace(anchor,insert+anchor,1)
p.write_text(s); changed.append("SP/code/rend2/tr_cmds.c")

# ---------------------------------------------------------------------------
# Backend: generate LUT and every GGX cubemap face/mip on the GL thread.
# ---------------------------------------------------------------------------
p,s=read("tr_backend.c")
anchor='''/*
====================
RB_ExecuteRenderCommands
====================
*/
'''
backend_code=r'''// ---------------------------------------------------------------------------
// DarkWolf PBR V3.1 true split-sum IBL preprocessing.
// ---------------------------------------------------------------------------
static void RB_PbrV31FullscreenPass(shaderProgram_t *program, int width, int height, const vec4_t params)
{
    vec4_t quadVerts[4];
    vec2_t texCoords[4];
    mat4_t projection;

    FBO_Bind(tr.pbrIblFbo);
    GL_Viewport(0, 0, width, height);
    GL_Scissor(0, 0, width, height);
    Mat4Ortho(0, width, height, 0, 0, 1, projection);

    GL_Cull(CT_TWO_SIDED);
    GL_State(GLS_DEPTHTEST_DISABLE);

    VectorSet4(quadVerts[0], 0,     height, 0.0f, 1.0f);
    VectorSet4(quadVerts[1], width, height, 0.0f, 1.0f);
    VectorSet4(quadVerts[2], width, 0,      0.0f, 1.0f);
    VectorSet4(quadVerts[3], 0,     0,      0.0f, 1.0f);

    VectorSet2(texCoords[0], 0.0f, 1.0f);
    VectorSet2(texCoords[1], 1.0f, 1.0f);
    VectorSet2(texCoords[2], 1.0f, 0.0f);
    VectorSet2(texCoords[3], 0.0f, 0.0f);

    GLSL_BindProgram(program);
    GLSL_SetUniformMat4(program, UNIFORM_MODELVIEWPROJECTIONMATRIX, projection);
    GLSL_SetUniformVec4(program, UNIFORM_COLOR, params);
    RB_InstantQuad2(quadVerts, texCoords);
}

static int RB_PbrV31MaxRoughnessMip(int size)
{
    int fullMax = 0;
    while (size > 1)
    {
        size >>= 1;
        fullMax++;
    }
    // Preserve Rend2's ROUGHNESS_MIPS convention: avoid the final 1x1 level.
    return MAX(1, fullMax - 1);
}

static void RB_PbrV31BuildBrdfLut(void)
{
    vec4_t params;

    if (!tr.pbrBrdfLutImage || !tr.pbrIblFbo || !tr.pbrBrdfLutShader.program)
        return;

    FBO_AttachImageLevel(tr.pbrIblFbo, tr.pbrBrdfLutImage, GL_COLOR_ATTACHMENT0, 0, 0);
    VectorSet4(params, 512.0f, 0.0f, 0.0f, 0.0f);
    RB_PbrV31FullscreenPass(&tr.pbrBrdfLutShader, 256, 256, params);
    tr.pbrBrdfLutReady = qtrue;
}

static void RB_PbrV31PrefilterCubemap(cubemap_t *cubemap)
{
    int face, mip;
    int size = r_cubemapSize->integer;
    int maxMip = RB_PbrV31MaxRoughnessMip(size);
    float sourceResolution;

    if (!cubemap || !cubemap->image || !cubemap->prefilteredImage)
        return;

    // Convolve directly from raw level 0. Legacy generated mips are intentionally
    // not sampled here because they were averaged in encoded color space.
    GL_BindToTMU(cubemap->image, TB_CUBEMAP);

    sourceResolution = (float)MAX(1, cubemap->image->uploadWidth);

    for (mip = 0; mip <= maxMip; ++mip)
    {
        int mipSize = MAX(1, size >> mip);
        float roughness = maxMip > 0 ? (float)mip / (float)maxMip : 0.0f;
        float samples = (mip == 0) ? 1.0f : 256.0f;

        for (face = 0; face < 6; ++face)
        {
            vec4_t params;
            FBO_AttachImageLevel(tr.pbrIblFbo, cubemap->prefilteredImage,
                GL_COLOR_ATTACHMENT0, face, mip);
            VectorSet4(params, (float)face, roughness, sourceResolution, samples);
            RB_PbrV31FullscreenPass(&tr.pbrPrefilterShader, mipSize, mipSize, params);
        }
    }

    qglTextureParameterfEXT(cubemap->prefilteredImage->texnum, GL_TEXTURE_CUBE_MAP,
        GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
    qglTextureParameterfEXT(cubemap->prefilteredImage->texnum, GL_TEXTURE_CUBE_MAP,
        GL_TEXTURE_MAG_FILTER, GL_LINEAR);
}

static const void *RB_PbrIblBuild(const void *data)
{
    const pbrIblBuildCommand_t *cmd = (const pbrIblBuildCommand_t *)data;
    int i;

    if (r_pbr->integer < 3 || !r_cubeMapping->integer ||
        !glRefConfig.framebufferObject || !glRefConfig.textureFloat ||
        glConfig.numTextureUnits < 8 || !tr.pbrIblFbo)
        return (const void *)(cmd + 1);

    tr.pbrBrdfLutReady = qfalse;
    RB_PbrV31BuildBrdfLut();

    for (i = 0; i < tr.numCubemaps; ++i)
        RB_PbrV31PrefilterCubemap(&tr.cubemaps[i]);

    FBO_Bind(NULL);
    GL_BindNullProgram();
    GL_CheckErrors();

    ri.Printf(PRINT_ALL,
        "DarkWolf PBR V3.1 IBL ready: probes=%d prefilterSamples=256 brdfLut=256x256 brdfSamples=512\n",
        tr.numCubemaps);

    return (const void *)(cmd + 1);
}


'''
if anchor not in s:
    raise SystemExit("backend command insertion anchor missing")
s=s.replace(anchor,backend_code+anchor,1)

old='''		case RC_EXPORT_CUBEMAPS:
			data = RB_ExportCubemaps(data);
			break;
		case RC_END_OF_LIST:
'''
new='''		case RC_EXPORT_CUBEMAPS:
			data = RB_ExportCubemaps(data);
			break;
		case RC_PBR_IBL_BUILD:
			data = RB_PbrIblBuild(data);
			break;
		case RC_END_OF_LIST:
'''
s=replace_once(s,old,new,"backend IBL command dispatch")
p.write_text(s); changed.append("SP/code/rend2/tr_backend.c")

proof={
    "base_run":42594561766,
    "base_sha":"957c425b3c3a8f521c72d5dd2bca9dba9b825938",
    "feature":"PBR V3.1 true GGX split-sum IBL",
    "ggx_prefilter":{
        "destination":"separate RGBA16F cubemap",
        "samples_per_nonzero_mip":256,
        "importance_sampling":"GGX",
        "source_sampling":"raw cubemap LOD0 only; avoids gamma-space legacy mip averaging",
        "roughness_mapping":"mip/maxRoughnessMip",
        "source_color_space":"each source sample is converted from sRGB to linear before accumulation"
    },
    "brdf_lut":{
        "size":"256x256 RGBA16F",
        "samples":512,
        "integration":"split-sum GGX DFG with correlated Smith visibility matching direct GGX",
        "axes":"NdotV x perceptual roughness"
    },
    "fallback":"existing analytical PBR V3 IBL when FBO/float/8-TMU requirements are unavailable",
    "legacy_modes_preserved":["r_pbr 0","r_pbr 1","r_pbr 2"],
    "changed_files":sorted(set(changed))
}
if args.proof:
    q=Path(args.proof); q.parent.mkdir(parents=True,exist_ok=True); q.write_text(json.dumps(proof,indent=2)+"\n")
print(json.dumps(proof,indent=2))
