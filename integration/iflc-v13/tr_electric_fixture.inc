/* DW_ELECTRIC_APERTURE_SELF_SHADOW_V13
 * Geometry-qualified connected housing sharing a planar emitter's boundary.
 * No map names, material names, BSP ordinals or camera-dependent classifiers.
 * Only its own physical electric source's point/world captures are trimmed.
 * IFLC fire, architecture, tripod, rods, CSM and synthetic FireVol are preserved.
 */
#define EF_MAX_FIXTURES 64
#define EF_MAX_BODIES 4
#define EF_MAX_VERTS 512
#define EF_MAX_TRIS 512
#define EF_MAX_APERTURE_VERTS 32
#define EF_MAX_APERTURE_EDGES 64

typedef struct {
    const srfBspSurface_t *mesh;
    int surfaceIndex, triangleCount, removed;
    unsigned char omit[EF_MAX_TRIS];
} efBody_t;
typedef struct {
    int apertureSurface, bodyCount;
    vec3_t origin, normal;
    float radius;
    unsigned int key;
    efBody_t body[EF_MAX_BODIES];
} efFixture_t;
static efFixture_t s_efFixtures[EF_MAX_FIXTURES];
static int s_efCount;
static qboolean s_efBuilt, s_efOverflow;

void R_ElectricFixtureReset(void)
{
    memset(s_efFixtures, 0, sizeof(s_efFixtures));
    s_efCount = 0; s_efBuilt = s_efOverflow = qfalse;
}
static const srfBspSurface_t *EF_Mesh(const msurface_t *s)
{
    const srfBspSurface_t *b;
    if (!s || !s->data || !s->shader || s->shader->numDeforms || s->shader->isSky || s->shader->polygonOffset ||
        (*s->data != SF_TRIANGLES && *s->data != SF_FACE)) return NULL;
    b = (const srfBspSurface_t *)s->data;
    if (!b->verts || !b->indexes || b->numVerts < 3 || b->numVerts > EF_MAX_VERTS ||
        b->numIndexes < 3 || b->numIndexes > EF_MAX_TRIS * 3 || b->numIndexes % 3) return NULL;
    return b;
}
static float EF_Dist2(const vec3_t a, const vec3_t b)
{
    vec3_t d; VectorSubtract(a, b, d); return DotProduct(d, d);
}
static qboolean EF_VertexEqual(const vec3_t a, const vec3_t b)
{
    return EF_Dist2(a, b) <= 0.0004f;
}
static qboolean EF_ValidIndexes(const srfBspSurface_t *b)
{
    int i;
    for (i = 0; i < b->numIndexes; ++i)
        if ((unsigned int)b->indexes[i] >= (unsigned int)b->numVerts) return qfalse;
    return qtrue;
}
static qboolean EF_EdgeEqual(const vec3_t a, const vec3_t b, const vec3_t c, const vec3_t d)
{
    return (EF_VertexEqual(a,c) && EF_VertexEqual(b,d)) || (EF_VertexEqual(a,d) && EF_VertexEqual(b,c));
}
static qboolean EF_Aperture(const msurface_t *s, efFixture_t *f, int edges[][2], int *edgeCount)
{
    const srfBspSurface_t *b = EF_Mesh(s);
    vec3_t lo, hi, u, v;
    float area = 0.0f, radius2 = 0.0f;
    int i, j, n = 0;
    if (!b || !s->shader->ssgiEmitter || b->numVerts < 5 || b->numVerts > EF_MAX_APERTURE_VERTS ||
        b->numIndexes < 9 || b->numIndexes > 90 || !EF_ValidIndexes(b) || s->shader->cullType == CT_TWO_SIDED)
        return qfalse;
    VectorClear(f->origin); ClearBounds(lo,hi);
    for (i = 0; i < b->numVerts; ++i) {
        VectorAdd(f->origin, b->verts[i].xyz, f->origin);
        AddPointToBounds(b->verts[i].xyz,lo,hi);
    }
    VectorScale(f->origin, 1.0f / b->numVerts, f->origin);
    VectorSubtract(b->verts[b->indexes[1]].xyz,b->verts[b->indexes[0]].xyz,u);
    VectorSubtract(b->verts[b->indexes[2]].xyz,b->verts[b->indexes[0]].xyz,v);
    CrossProduct(u,v,f->normal);
    if (VectorNormalize(f->normal) < .01f || fabsf(f->normal[2]) > .65f) return qfalse;
    for (i = 0; i < b->numVerts; ++i) {
        VectorSubtract(b->verts[i].xyz,f->origin,u);
        if (fabsf(DotProduct(u,f->normal)) > .08f) return qfalse;
        radius2 = MAX(radius2,DotProduct(u,u));
    }
    f->radius = sqrtf(radius2);
    if (f->radius < 6.0f || f->radius > 32.0f) return qfalse;
    for (i = 0; i < b->numIndexes; i += 3) {
        VectorSubtract(b->verts[b->indexes[i+1]].xyz,b->verts[b->indexes[i]].xyz,u);
        VectorSubtract(b->verts[b->indexes[i+2]].xyz,b->verts[b->indexes[i]].xyz,v);
        { vec3_t cross; CrossProduct(u,v,cross); area += .5f * VectorLength(cross); }
        for (j = 0; j < 3; ++j) {
            int a = b->indexes[i+j], c = b->indexes[i+(j+1)%3], k, occurrences = 0;
            if (EF_VertexEqual(b->verts[a].xyz,b->verts[c].xyz)) return qfalse;
            for (k = 0; k < b->numIndexes; ++k) {
                int x = b->indexes[k], y = b->indexes[k/3*3+(k+1)%3];
                if (EF_EdgeEqual(b->verts[a].xyz,b->verts[c].xyz,b->verts[x].xyz,b->verts[y].xyz)) ++occurrences;
            }
            if (occurrences == 1) {
                if (n == EF_MAX_APERTURE_EDGES) return qfalse;
                edges[n][0] = a; edges[n++][1] = c;
            } else if (occurrences != 2) return qfalse;
        }
    }
    if (n < 5 || n > 16 || area < radius2 * 1.2f || area > radius2 * 3.4f) return qfalse;
    *edgeCount = n; return qtrue;
}
static qboolean EF_TrianglesAdjacent(const srfBspSurface_t *b, int a, int c)
{
    int i, j, matches = 0;
    for (i = 0; i < 3; ++i)
        for (j = 0; j < 3; ++j)
            if (EF_VertexEqual(b->verts[b->indexes[a*3+i]].xyz,b->verts[b->indexes[c*3+j]].xyz)) {
                ++matches; break;
            }
    return matches >= 2;
}
static qboolean EF_Housing(const efFixture_t *f, const srfBspSurface_t *aperture,
                          int edges[][2], int edgeCount, const msurface_t *surface, efBody_t *out)
{
    const srfBspSurface_t *b = EF_Mesh(surface);
    int i, j, k, n, head = 0, tail = 0, queue[EF_MAX_TRIS];
    float low = 1e30f, high = -1e30f, radial = 0.0f;
    vec3_t lo,hi;
    if (!b || surface->shader->ssgiEmitter || R_DarkWolfClassifyShadowMaterial(surface->shader) != DWSHADOW_MATERIAL_OPAQUE_SOLID ||
        !EF_ValidIndexes(b)) return qfalse;
    ClearBounds(lo,hi);
    for (i = 0; i < b->numVerts; ++i) AddPointToBounds(b->verts[i].xyz,lo,hi);
    for (k = 0; k < 3; ++k) if (f->origin[k] < lo[k] - 2*f->radius || f->origin[k] > hi[k] + 2*f->radius) return qfalse;
    memset(out,0,sizeof(*out)); out->mesh = b; out->triangleCount = n = b->numIndexes/3;
    for (i = 0; i < n; ++i) {
        qboolean matched = qfalse;
        for (j = 0; j < 3 && !matched; ++j)
            for (k = 0; k < edgeCount; ++k)
                if (EF_EdgeEqual(b->verts[b->indexes[i*3+j]].xyz,b->verts[b->indexes[i*3+(j+1)%3]].xyz,
                     aperture->verts[edges[k][0]].xyz,aperture->verts[edges[k][1]].xyz)) { matched=qtrue; break; }
        if (matched) { out->omit[i] = 1; queue[tail++] = i; }
    }
    while (head < tail) {
        int current = queue[head++];
        for (i = 0; i < n; ++i) if (!out->omit[i] && EF_TrianglesAdjacent(b,current,i)) {
            out->omit[i] = 1; queue[tail++] = i;
        }
    }
    if (tail < 8 || tail > 128) return qfalse;
    for (i = 0; i < n; ++i) if (out->omit[i]) {
        ++out->removed;
        for (j = 0; j < 3; ++j) {
            vec3_t d; float depth,r2;
            VectorSubtract(b->verts[b->indexes[i*3+j]].xyz,f->origin,d);
            depth = DotProduct(d,f->normal); r2 = DotProduct(d,d)-depth*depth;
            low=MIN(low,depth); high=MAX(high,depth); radial=MAX(radial,r2);
        }
    }
    if (high-low < 3 || high-low > 3*f->radius || low > .15f || high < -.15f ||
        (low < -1.0f && high > 1.0f) || radial > (1.7f*f->radius+1)*(1.7f*f->radius+1)) return qfalse;
    return qtrue;
}
static unsigned int EF_Hash(unsigned int h, const void *data, int n)
{
    const unsigned char *p = (const unsigned char *)data;
    while (n-- > 0) { h ^= *p++; h *= 16777619u; }
    return h;
}
static void EF_Build(void)
{
    int i,j;
    if (s_efBuilt || !tr.world || !tr.world->surfaces) return;
    s_efBuilt=qtrue;
    for (i = 0; i < tr.world->numWorldSurfaces; ++i) {
        efFixture_t temp;
        int edges[EF_MAX_APERTURE_EDGES][2], ne;
        const srfBspSurface_t *aperture;
        memset(&temp,0,sizeof(temp));
        if (!EF_Aperture(&tr.world->surfaces[i],&temp,edges,&ne)) continue;
        aperture=EF_Mesh(&tr.world->surfaces[i]); temp.apertureSurface=i;
        for (j = 0; j < tr.world->numWorldSurfaces; ++j) {
            efBody_t body;
            if (j == i || !EF_Housing(&temp,aperture,edges,ne,&tr.world->surfaces[j],&body)) continue;
            if (temp.bodyCount == EF_MAX_BODIES) { temp.bodyCount=0; break; }
            body.surfaceIndex=j; temp.body[temp.bodyCount++]=body;
        }
        if (!temp.bodyCount) continue;
        if (s_efCount == EF_MAX_FIXTURES) { s_efCount=0; s_efOverflow=qtrue; return; }
        temp.key=EF_Hash(2166136261u,&i,sizeof(i));
        for (j=0;j<temp.bodyCount;++j) {
            temp.key=EF_Hash(temp.key,&temp.body[j].surfaceIndex,sizeof(int));
            temp.key=EF_Hash(temp.key,temp.body[j].omit,temp.body[j].triangleCount);
        }
        if (!temp.key) temp.key=1;
        s_efFixtures[s_efCount++]=temp;
    }
}
int R_ElectricFixtureForLight(const dlight_t *dl)
{
    int i, best=-1; float best2=1e30f, second2=1e30f;
    if (!dl || dl->iflcOptIn || dl->fireVolumetricSource || dl->transientBlast ||
        dl->shadowSourceClass != DWSHADOW_SOURCE_PERSISTENT_PHYSICAL ||
        !(dl->staticPromoteFixtureId >= 0 || dl->nativeAuthoredDlight || dl->localVolumetricLamp)) return 0;
    EF_Build(); if (s_efOverflow) return 0;
    for (i=0;i<s_efCount;++i) {
        vec3_t d; float distance2,depth,radial;
        const efFixture_t *f=&s_efFixtures[i];
        VectorSubtract(dl->origin,f->origin,d); distance2=DotProduct(d,d);
        depth=DotProduct(d,f->normal);radial=distance2-depth*depth;
        if (fabsf(depth)>48 || radial>(f->radius+12)*(f->radius+12)) continue;
        if (distance2<best2) { second2=best2;best2=distance2;best=i; }
        else if (distance2<second2) second2=distance2;
    }
    if (best<0 || second2<best2*1.5f+16.0f) return 0;
    return best+1;
}
unsigned int R_ElectricFixtureKey(int fixture)
{
    return fixture>0 && fixture<=s_efCount ? s_efFixtures[fixture-1].key : 0;
}
static void RB_ElectricFixtureSurface(const drawSurf_t *ds)
{
    int i,entity,fixture=backEnd.viewParms.electricFixture;
    if (!s_efBuilt || fixture<=0 || fixture>s_efCount || !tr.world ||
        R_ElectricFixtureKey(fixture)!=backEnd.viewParms.electricFixtureKey ||
        (backEnd.viewParms.flags & (VPF_SHADOWMAP|VPF_DEPTHSHADOW)) != (VPF_SHADOWMAP|VPF_DEPTHSHADOW) ||
        (backEnd.viewParms.flags & (VPF_ORTHOGRAPHIC|VPF_FIREVOL_SYNTHETIC_SHADOW))) goto original;
    entity=(ds->sort>>QSORT_REFENTITYNUM_SHIFT)&REFENTITYNUM_MASK;
    if (entity!=REFENTITYNUM_WORLD) goto original;
    for (i=0;i<s_efFixtures[fixture-1].bodyCount;++i) {
        const efBody_t *body=&s_efFixtures[fixture-1].body[i];
        if (ds->surface==(const surfaceType_t *)body->mesh) {
            RB_SurfaceElectricTrim((srfBspSurface_t *)ds->surface,body->omit,body->triangleCount);
            return;
        }
    }
original:
    rb_surfaceTable[*ds->surface](ds->surface);
}
