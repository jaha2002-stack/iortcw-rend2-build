/* CPU-only renderer ABI/GL stubs. Real tested functions are extracted at run time. */

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
typedef float vec3_t[3];typedef float vec4_t[4];typedef int ivec4_t[4];
typedef int qboolean;
#define qtrue 1
#define qfalse 0
#define MAX(a,b) ((a)>(b)?(a):(b))
#define VectorCopy(a,b) do{(b)[0]=(a)[0];(b)[1]=(a)[1];(b)[2]=(a)[2];}while(0)
#define VectorCopy4(a,b) do{VectorCopy(a,b);(b)[3]=(a)[3];}while(0)
#define VectorSet4(v,a,b,c,d) do{(v)[0]=(a);(v)[1]=(b);(v)[2]=(c);(v)[3]=(d);}while(0)
#define VectorScale(a,s,b) do{(b)[0]=(a)[0]*(s);(b)[1]=(a)[1]*(s);(b)[2]=(a)[2]*(s);}while(0)
#define VectorSubtract(a,b,c) do{(c)[0]=(a)[0]-(b)[0];(c)[1]=(a)[1]-(b)[1];(c)[2]=(a)[2]-(b)[2];}while(0)
#define DotProduct(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1]+(a)[2]*(b)[2])
#define MAX_DLIGHT_SHADOWS 3
#define DLIGHT_WORLD_CACHE_MAX 32
#define M_PI 3.14159265358979323846
static float Com_Clamp(float lo,float hi,float v){return v<lo?lo:v>hi?hi:v;}
typedef struct{vec3_t origin,color;float radius;qboolean iflcActive,iflcOptIn;vec3_t iflcBaseColor;float iflcBaseRadius,iflcVolumeGain;int localVolumetricLamp;}dlight_t;
typedef struct{vec3_t origin,direction,color;float range,fov;}localVolumetricSpot_t;
typedef struct{int width;}image_t;
typedef struct{int id;}FBO_t;
typedef struct{int program;}program_t;
typedef struct{float value;int integer;}cvar_t;
static struct{FBO_t *quarterFbo[2],*volumetricFullresFbo,*screenScratchFbo;image_t *renderDepthImage,*shadowCubemaps[3],*dlightWorldCubemaps[32];program_t volumetricLocalShader,volumetricLocalUpscaleShader;}tr;
static struct{struct{float zFar,fovX,fovY;}viewParms;struct{vec3_t vieworg,viewaxis[3];int time;int dlightWorldSlot[32];vec4_t dlightWorldOrigin[32];}refdef;}backEnd;
static vec4_t values[100];static vec4_t capturedParams;
enum{GLS_DSTBLEND_ONE,GLS_SRCBLEND_ONE,TB_CUBEMAP,TB_LIGHTMAP,TB_NORMALMAP,UNIFORM_BASECOLOR,UNIFORM_CUBEMAPINFO,UNIFORM_DLIGHTINFO,UNIFORM_DLIGHTSHADOWPARAMS,UNIFORM_DLIGHTWORLDMAP,UNIFORM_DLIGHTWORLDORIGIN,UNIFORM_ENABLETEXTURES,UNIFORM_PRIMARYLIGHTCOLOR,UNIFORM_PRIMARYLIGHTORIGIN,UNIFORM_VIEWFORWARD,UNIFORM_VIEWINFO,UNIFORM_VIEWLEFT,UNIFORM_VIEWORIGIN,UNIFORM_VIEWUP};
static cvar_t r_dlightShadowBias_storage={1,1};static cvar_t *r_dlightShadowBias=&r_dlightShadowBias_storage;
static cvar_t r_dlightShadowSoftness_storage={1,1};static cvar_t *r_dlightShadowSoftness=&r_dlightShadowSoftness_storage;
static cvar_t r_dlightShadowStrength_storage={1,1};static cvar_t *r_dlightShadowStrength=&r_dlightShadowStrength_storage;
static cvar_t r_volumetricLocalAnisotropy_storage={1,1};static cvar_t *r_volumetricLocalAnisotropy=&r_volumetricLocalAnisotropy_storage;
static cvar_t r_volumetricLocalDensity_storage={1,1};static cvar_t *r_volumetricLocalDensity=&r_volumetricLocalDensity_storage;
static cvar_t r_volumetricLocalGain_storage={1,1};static cvar_t *r_volumetricLocalGain=&r_volumetricLocalGain_storage;
static cvar_t r_volumetricLocalJitter_storage={1,1};static cvar_t *r_volumetricLocalJitter=&r_volumetricLocalJitter_storage;
static cvar_t r_volumetricLocalKnee_storage={1,1};static cvar_t *r_volumetricLocalKnee=&r_volumetricLocalKnee_storage;
static cvar_t r_volumetricLocalMaxDistance_storage={1,1};static cvar_t *r_volumetricLocalMaxDistance=&r_volumetricLocalMaxDistance_storage;
static cvar_t r_volumetricLocalSamples_storage={1,1};static cvar_t *r_volumetricLocalSamples=&r_volumetricLocalSamples_storage;
static cvar_t r_volumetricLocalShadowPcf_storage={1,1};static cvar_t *r_volumetricLocalShadowPcf=&r_volumetricLocalShadowPcf_storage;
static cvar_t r_volumetricLocalSpotDepthReject_storage={1,1};static cvar_t *r_volumetricLocalSpotDepthReject=&r_volumetricLocalSpotDepthReject_storage;
static cvar_t r_volumetricLocalSpotEdgeSoftness_storage={1,1};static cvar_t *r_volumetricLocalSpotEdgeSoftness=&r_volumetricLocalSpotEdgeSoftness_storage;
static cvar_t r_volumetricLocalSpotJitter_storage={1,1};static cvar_t *r_volumetricLocalSpotJitter=&r_volumetricLocalSpotJitter_storage;
static cvar_t r_volumetricLocalSpotSamples_storage={1,1};static cvar_t *r_volumetricLocalSpotSamples=&r_volumetricLocalSpotSamples_storage;
static cvar_t r_volumetricLocalSpotUpscale_storage={1,1};static cvar_t *r_volumetricLocalSpotUpscale=&r_volumetricLocalSpotUpscale_storage;
static cvar_t r_volumetricLocalStrength_storage={1,1};static cvar_t *r_volumetricLocalStrength=&r_volumetricLocalStrength_storage;
static cvar_t r_znear_storage={1,1};static cvar_t *r_znear=&r_znear_storage;
static cvar_t s_rVolumetricFireDensity_storage={1,1};static cvar_t *s_rVolumetricFireDensity=&s_rVolumetricFireDensity_storage;
static cvar_t s_rVolumetricFireDepthReject_storage={1,1};static cvar_t *s_rVolumetricFireDepthReject=&s_rVolumetricFireDepthReject_storage;
static cvar_t s_rVolumetricFirePlumeHeight_storage={1,1};static cvar_t *s_rVolumetricFirePlumeHeight=&s_rVolumetricFirePlumeHeight_storage;
static cvar_t s_rVolumetricFirePlumeRadius_storage={1,1};static cvar_t *s_rVolumetricFirePlumeRadius=&s_rVolumetricFirePlumeRadius_storage;
static cvar_t s_rVolumetricFireSamples_storage={1,1};static cvar_t *s_rVolumetricFireSamples=&s_rVolumetricFireSamples_storage;
static cvar_t s_rVolumetricFireSpeed_storage={1,1};static cvar_t *s_rVolumetricFireSpeed=&s_rVolumetricFireSpeed_storage;
static cvar_t s_rVolumetricFireStrength_storage={1,1};static cvar_t *s_rVolumetricFireStrength=&s_rVolumetricFireStrength_storage;
static cvar_t s_rVolumetricFireTurbulence_storage={1,1};static cvar_t *s_rVolumetricFireTurbulence=&s_rVolumetricFireTurbulence_storage;
static cvar_t s_rVolumetricFireUpscale_storage={1,1};static cvar_t *s_rVolumetricFireUpscale=&s_rVolumetricFireUpscale_storage;

static int RB_DWAlarmWorldLight(const dlight_t *lamp,int mode){(void)lamp;(void)mode;return -1;}
static void GLSL_BindProgram(program_t*p){(void)p;}
static void GL_BindToTMU(image_t*i,int t){(void)i;(void)t;}
static void GLSL_SetUniformInt(program_t*p,int id,int v){(void)p;values[id][0]=v;}
static void GLSL_SetUniformVec3(program_t*p,int id,const vec3_t v){(void)p;VectorCopy(v,values[id]);}
static void GLSL_SetUniformVec4(program_t*p,int id,const vec4_t v){(void)p;VectorCopy4(v,values[id]);}
static void RB_FarPlaneExtents(float z,float fx,float fy,float*x,float*y){(void)fx;(void)fy;*x=z;*y=z;}
static void RB_VolumetricUpscaleInputs(FBO_t*f,ivec4_t b,vec4_t v){(void)f;(void)b;(void)v;}
static void FBO_Blit(FBO_t*a,ivec4_t b,void*c,FBO_t*d,ivec4_t e,program_t*p,const vec4_t v,int flags){(void)a;(void)b;(void)c;(void)e;(void)p;(void)flags;if(d==tr.quarterFbo[0]&&v)VectorCopy4(v,capturedParams);}
