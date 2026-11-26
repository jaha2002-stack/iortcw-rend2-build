#include <assert.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#define MAX_DLIGHTS 32
#define IFLC_MAX_OWNERS 1024
#define IFLC_SURFACE 3
#define DWSHADOW_SOURCE_PERSISTENT_PHYSICAL 7
#define REFENTITYNUM_WORLD 1023
#define VPF_SHADOWMAP 1
#define VPF_DEPTHSHADOW 2
#define VPF_ORTHOGRAPHIC 4
#define VPF_DLIGHT_WORLD_OCCLUSION 8
#define VPF_FIREVOL_SYNTHETIC_SHADOW 16
#define MAX(a,b) ((a) > (b) ? (a) : (b))
#define DotProduct(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1]+(a)[2]*(b)[2])
#define VectorCompare(a,b) ((a)[0] == (b)[0] && (a)[1] == (b)[1] && (a)[2] == (b)[2])
#define VectorSubtract(a,b,c) do { for (int axis = 0; axis < 3; ++axis) (c)[axis] = (a)[axis] - (b)[axis]; } while (0)

typedef enum { qfalse, qtrue } qboolean;
typedef float vec3_t[3];
typedef struct {
    vec3_t origin;
    int staticPromoteFixtureId, physicalElectricOwnerId, shadowSourceClass;
    int noDlightShadow, iflcOptIn, iflcOptInOwner, fireVolumetricSource, transientBlast;
    int autoFixture, explicitFixture, hasProfile, group, iflcDlightOwner;
} dlight_t;
typedef struct { qboolean valid; vec3_t origin; float radius; unsigned iflcFixtureKey, electricFixtureKey, brushKey; } dlightWorldCache_t;
typedef struct { qboolean valid; int flameSurface; vec3_t captureOrigin; float captureRadius; unsigned iflcFixtureKey, brushKey; } fireVolumetricSyntheticShadowCache_t;
typedef struct { qboolean valid; int flameSurface; vec3_t flameOrigin; float sampleRadius; unsigned iflcFixtureKey; } fireVolumetricSyntheticShadowHint_t;
typedef struct { int caster; } shader_t;
typedef struct { const shader_t *shader; qboolean blocks; float hit; } msurface_t;
typedef struct { int numWorldSurfaces; const msurface_t *surfaces; } world_t;
typedef struct { vec3_t origin; int kind, ambiguous, runtimeCount; } iflcOwner_t;
typedef struct { int selfShadow; } iflcProfile_t;
typedef struct { int count, surfaces[4]; unsigned key; } iflcSelfFixture_t;

static struct {
    struct { int num_dlights; dlight_t dlights[MAX_DLIGHTS]; void *entities; int num_entities; } refdef;
    const world_t *world;
    int currentEntityNum;
    struct { int flags, iflcFixture; unsigned iflcFixtureKey; } viewParms;
} tr;
static const vec3_t s_iflcViewOrigin, s_iflcViewForward;
static int s_iflcReady = 1, s_iflcCatalogOverflow, s_iflcOwnerCount = 2;
static iflcOwner_t s_iflcOwners[2];
static iflcProfile_t profiles[2];
static iflcSelfFixture_t s_iflcSelfFixtures[2];
static struct { int integer; } fireControl = {1}, *r_dwFireLightControl = &fireControl;

static float R_IFLC_DistanceSquared(const vec3_t a, const vec3_t b)
{
    vec3_t delta;
    VectorSubtract(a, b, delta);
    return DotProduct(delta, delta);
}
static qboolean R_IFLC_SurfaceBlocks(const msurface_t *surface) { return surface->blocks; }
static qboolean R_DarkWolfSupportedShadowCasterMaterial(const shader_t *shader) { return shader->caster ? qtrue : qfalse; }
static qboolean R_IFLC_RaySurface(const msurface_t *surface, const vec3_t origin,
                                 const vec3_t forward, float range, float *hit)
{
    (void)origin;
    (void)forward;
    if (surface->hit <= 0 || surface->hit > range) return qfalse;
    *hit = surface->hit;
    return qtrue;
}
static int R_IFLC_DlightOwner(const dlight_t *dl) { return dl->iflcDlightOwner; }
static const iflcProfile_t *R_IFLC_ProfileForOwner(int i, qboolean create) { assert(!create); return &profiles[i]; }
static void R_IFLC_PrepareSelfFixture(int i) { assert(i >= 0 && i < s_iflcOwnerCount); }

static int R_ElectricFixtureForLightAuto(const dlight_t *dl) { return dl->autoFixture; }
static qboolean R_ELSS_ElectricPolicy(const dlight_t *dl, int *fixture)
{
    *fixture = dl->explicitFixture;
    return dl->hasProfile ? qtrue : qfalse;
}
static qboolean R_DarkWolfStaticPromoteShadowGroupEligible(const dlight_t *dl) { return dl->group >= 0 ? qtrue : qfalse; }
static int R_DarkWolfStaticPromoteShadowGroupCanonicalId(int i) { return tr.refdef.dlights[i].group; }
static unsigned R_ArchitecturalBrushKey(void *entities, int count, const vec3_t origin, float radius)
{
    (void)entities;
    (void)count;
    (void)origin;
    (void)radius;
    return 7;
}

/* RENDERER_FUNCTIONS */

static void test_electric(void)
{
    dlight_t *lights = tr.refdef.dlights;
    int fixture;
    const vec3_t origin = {0};
    dlightWorldCache_t cache = {qtrue, {0}, 128, 0, 42, 7};

    assert(R_ElectricFixtureForCapture(0) == 0);
    tr.refdef.num_dlights = 2;
    lights[0] = (dlight_t){.staticPromoteFixtureId = 41, .physicalElectricOwnerId = 41,
        .shadowSourceClass = DWSHADOW_SOURCE_PERSISTENT_PHYSICAL, .autoFixture = 3, .group = 1};
    lights[1] = lights[0];
    lights[1].staticPromoteFixtureId = 1000041;
    lights[1].autoFixture = 0;
    assert(R_ElectricFixtureForCapture(0) == 3);
    lights[1].autoFixture = 4;
    assert(R_ElectricFixtureForCapture(1) == 0);
    lights[1].autoFixture = 3;
    assert(R_ElectricFixtureForCapture(0) == 3);

    lights[0].hasProfile = 1;
    lights[0].explicitFixture = -23;
    assert(R_ElectricFixtureForCapture(0) == -23);
    assert(R_ElectricFixtureForCapture(1) == -23);
    assert(R_ElectricCapturePolicy(&lights[1], &fixture) && fixture == -23);
    lights[1].physicalElectricOwnerId = 42;
    assert(!R_ElectricCapturePolicy(&lights[1], &fixture));
    assert(R_ElectricFixtureForCapture(0) == 0);
    lights[1].physicalElectricOwnerId = 41;
    lights[1].hasProfile = 1;
    lights[1].explicitFixture = -24;
    assert(R_ElectricFixtureForCapture(0) == 0);
    lights[1].explicitFixture = 0;
    assert(R_ElectricFixtureForCapture(0) == 0);
    lights[1].hasProfile = 0;
    lights[0].explicitFixture = 0;
    assert(R_ElectricCapturePolicy(&lights[1], &fixture) && fixture == 0);
    assert(R_ElectricFixtureForCapture(0) == 0);
    lights[0].explicitFixture = -23;
    lights[0].group = -1;
    assert(R_ElectricFixtureForCapture(0) == -23);
    tr.refdef.num_dlights = 0;
    assert(!R_ElectricCapturePolicy(&lights[1], &fixture));
    assert(R_DlightWorldCacheMatches(&cache, origin, 64, 0, 42, 7));
    assert(!R_DlightWorldCacheMatches(&cache, origin, 64, 0, 43, 7));
}

static void test_fire(void)
{
    const shader_t flame = {0}, solid = {1};
    msurface_t surface[] = {{&flame, qfalse, 4}, {&solid, qtrue, 16},
                            {&solid, qtrue, 32}, {&solid, qfalse, 0}};
    world_t world = {4, surface};
    dlight_t light = {.iflcOptIn = 1, .iflcOptInOwner = 1, .iflcDlightOwner = -1};
    float distance = -1;
    const int custom = IFLC_MAX_OWNERS + 1;
    fireVolumetricSyntheticShadowCache_t cache = {qtrue, 8, {0}, 128, 51, 7};
    fireVolumetricSyntheticShadowHint_t hint = {qtrue, 8, {0}, 128, 51};

    tr.world = &world;
    assert(R_IFLC_PickBodySurface(&distance) == 1 && distance == 16);
    surface[2].hit = 8;
    assert(R_IFLC_PickBodySurface(&distance) == 2 && distance == 8);
    surface[3].hit = 6;
    assert(R_IFLC_PickBodySurface(&distance) == 3 && distance == 6); /* cutout */
    surface[3].hit = surface[2].hit = surface[1].hit = 0;
    assert(R_IFLC_PickBodySurface(&distance) == -1);

    s_iflcOwners[0] = s_iflcOwners[1] = (iflcOwner_t){{0}, IFLC_SURFACE, 0, 1};
    profiles[0].selfShadow = 1;
    s_iflcSelfFixtures[0] = (iflcSelfFixture_t){1, {1}, 51};
    assert(R_IFLC_CustomFixture(&light) == custom);
    light.iflcOptInOwner = 2;
    assert(R_IFLC_CustomFixture(&light) == -1);
    light.iflcOptInOwner = 0;
    assert(R_IFLC_CustomFixture(&light) == 0);
    light.iflcOptInOwner = 1;
    light.origin[0] = 1;
    assert(R_IFLC_CustomFixture(&light) == 0);
    light.origin[0] = 0;
    s_iflcOwners[0].ambiguous = 1;
    assert(R_IFLC_CustomFixture(&light) == -1);
    s_iflcOwners[0].ambiguous = 0;
    profiles[0].selfShadow = 2;
    assert(R_IFLC_CustomFixture(&light) == 0);
    profiles[0].selfShadow = 0;
    assert(R_IFLC_CustomFixture(&light) == -1);
    profiles[0].selfShadow = 1;
    fireControl.integer = 0;
    assert(R_IFLC_CustomFixture(&light) == -1);
    fireControl.integer = 1;

    tr.currentEntityNum = REFENTITYNUM_WORLD;
    tr.viewParms.iflcFixture = custom;
    tr.viewParms.iflcFixtureKey = 51;
    tr.viewParms.flags = VPF_SHADOWMAP | VPF_DEPTHSHADOW;
    assert(R_IFLC_SuppressCustom(&surface[1]));
    assert(!R_IFLC_SuppressCustom(&surface[2]));
    tr.viewParms.flags |= VPF_DLIGHT_WORLD_OCCLUSION;
    assert(R_IFLC_SuppressCustom(&surface[1]));
    tr.viewParms.flags = VPF_SHADOWMAP | VPF_DEPTHSHADOW | VPF_FIREVOL_SYNTHETIC_SHADOW;
    assert(R_IFLC_SuppressCustom(&surface[1]));
    tr.viewParms.flags = VPF_SHADOWMAP | VPF_DEPTHSHADOW | VPF_ORTHOGRAPHIC;
    assert(!R_IFLC_SuppressCustom(&surface[1]));
    tr.viewParms.flags = 0;
    assert(!R_IFLC_SuppressCustom(&surface[1]));
    tr.viewParms.flags = VPF_SHADOWMAP | VPF_DEPTHSHADOW;
    tr.currentEntityNum = 0;
    assert(!R_IFLC_SuppressCustom(&surface[1]));
    tr.currentEntityNum = REFENTITYNUM_WORLD;
    tr.viewParms.iflcFixtureKey = 52;
    assert(!R_IFLC_SuppressCustom(&surface[1]));

    assert(R_FireVolProductionCacheMatchesHint(&cache, &hint));
    hint.iflcFixtureKey = 52;
    assert(!R_FireVolProductionCacheMatchesHint(&cache, &hint));
}

int main(void)
{
    test_electric();
    test_fire();
    puts("PASS actual C: signed ELSS policy, owner guards, IFLC casing hit/owner/pass and cache isolation");
    return 0;
}
