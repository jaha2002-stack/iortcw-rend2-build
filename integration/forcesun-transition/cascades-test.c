#include "tr_local.h"
#include <assert.h>

trGlobals_t tr;
glRefConfig_t glRefConfig;

static cvar_t forceSun, sunlightMode, volumetricSun, producer, smart, interval;
static cvar_t cascadeFar, cascadeNear, cascadeBias, shadowFilter, depthPrepass;
cvar_t *r_forceSun = &forceSun;
cvar_t *r_sunlightMode = &sunlightMode;
cvar_t *r_volumetricSun = &volumetricSun;
cvar_t *r_volumetricSunCsmProducer = &producer;
cvar_t *r_volumetricSunCsmSmart = &smart;
cvar_t *r_volumetricSunCsmBaseInterval = &interval;
cvar_t *r_shadowCascadeZFar = &cascadeFar;
cvar_t *r_shadowCascadeZNear = &cascadeNear;
cvar_t *r_shadowCascadeZBias = &cascadeBias;
cvar_t *r_shadowFilter = &shadowFilter;
cvar_t *r_depthPrepass = &depthPrepass;

static unsigned captures;
static float textureGeneration[4];

void Mat4Zero(mat4_t out)
{
    memset(out, 0, sizeof(mat4_t));
}

void Mat4Copy(const mat4_t in, mat4_t out)
{
    memcpy(out, in, sizeof(mat4_t));
}

void R_RenderSunShadowMaps(const refdef_t *fd, int cascade)
{
    (void)fd;
    assert(!(captures & (1u << cascade)));
    captures |= 1u << cascade;
    textureGeneration[cascade] = (float)tr.frameCount;
    tr.refdef.sunShadowMvp[cascade][0] = textureGeneration[cascade];
}

/* SUN_CASCADE_FUNCTIONS */

static void check_view(refdef_t *fd, int frame, int rdflags, viewParmFlags_t flags, unsigned expectedCaptures)
{
    int cascade;
    fd->rdflags = rdflags;
    fd->time = 16 * frame;
    tr.frameCount = frame;
    captures = 0;
    assert(R_PrepareSunCascades(fd) == flags);
    assert(captures == expectedCaptures);
    if (flags & VPF_USESUNCSM)
    {
        for (cascade = cascadeFar.integer ? 0 : 3; cascade < 4; ++cascade)
        {
            assert(textureGeneration[cascade] > 0.0f);
            assert(tr.refdef.sunShadowMvp[cascade][0] == textureGeneration[cascade]);
        }
    }
}

int main(void)
{
    refdef_t fd = {0};
    const viewParmFlags_t direct = VPF_USESUNLIGHT | VPF_USESUNCSM;

    glRefConfig.framebufferObject = qtrue;
    sunlightMode.integer = depthPrepass.integer = volumetricSun.integer = producer.integer = 1;
    smart.integer = 1;
    interval.integer = 4;
    cascadeFar.integer = 1024;
    fd.viewaxis[0][0] = 1.0f;
    tr.refdef.sunDir[2] = tr.refdef.sunCol[0] = 1.0f;

    forceSun.integer = 1;
    check_view(&fd, 1, RDF_SKYBOXPORTAL | RDF_DRAWSKYBOX, VPF_NONE, 0);
    check_view(&fd, 1, 0, direct, 15);
    check_view(&fd, 2, RDF_NOWORLDMODEL, VPF_NONE, 0);
    check_view(&fd, 2, RDF_SKYBOXPORTAL, VPF_NONE, 0);
    check_view(&fd, 2, 0, direct, 3);

    forceSun.integer = 0;
    check_view(&fd, 3, 0, VPF_USESUNCSM, 15);
    check_view(&fd, 4, 0, VPF_USESUNCSM, 1);
    producer.integer = 0;
    check_view(&fd, 5, 0, VPF_USESUNCSM, 0);
    forceSun.integer = 1;
    check_view(&fd, 6, 0, direct, 15);
    forceSun.integer = 0;
    check_view(&fd, 7, 0, VPF_NONE, 0);
    producer.integer = 1;
    check_view(&fd, 8, 0, VPF_USESUNCSM, 15);

    forceSun.integer = 2;
    check_view(&fd, 9, 0, direct, 15);
    check_view(&fd, 10, 0, direct, 15);
    forceSun.integer = 0;
    check_view(&fd, 11, 0, VPF_USESUNCSM, 15);

    tr.sunShadows = qtrue;
    check_view(&fd, 12, 0, direct, 15);
    check_view(&fd, 13, 0, direct, 7);
    forceSun.integer = 1;
    check_view(&fd, 14, 0, direct, 15);
    forceSun.integer = 0;
    check_view(&fd, 15, 0, direct, 15);
    check_view(&fd, 16, 0, direct, 7);

    tr.sunShadows = qfalse;
    tr.refdef.sunCol[0] = 0.0f;
    check_view(&fd, 17, 0, VPF_NONE, 0);
    tr.refdef.sunCol[0] = 1.0f;
    cascadeFar.integer = 0;
    check_view(&fd, 18, 0, VPF_USESUNCSM, 8);
    check_view(&fd, 19, 0, VPF_USESUNCSM, 0);
    depthPrepass.integer = 0;
    check_view(&fd, 20, 0, VPF_NONE, 0);
    depthPrepass.integer = 1;
    sunlightMode.integer = 0;
    check_view(&fd, 21, 0, VPF_NONE, 0);
    sunlightMode.integer = 1;
    check_view(&fd, 22, 0, VPF_USESUNCSM, 8);

    puts("PASS sun-source transitions, cascade pairing, pause/resume, and auxiliary views");
    return 0;
}
