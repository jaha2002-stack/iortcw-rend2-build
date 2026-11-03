/* IFLC V1.1: geometry-proven local wall-mount self-caster policy.
 * No map, surface ordinal, material name or camera direction determines a fix.
 * Only an opt-in fire's own compact connected mount is excluded from that
 * light's TWO direct shadow captures. Architecture, other lights, brush models,
 * visible geometry and synthetic FireVol capture remain unchanged.
 * Conservative classification: any ambiguity/overflow preserves all casters.
 */
#define IFLC_FIXTURE_CAP 48

typedef struct {
    qboolean built;
    int count;
    int surfaces[IFLC_FIXTURE_CAP];
    unsigned int policyKey;
} iflcFixture_t;
static iflcFixture_t s_iflcFixtures[IFLC_MAX_OWNERS];

static void R_IFLC_ResetFixtures(void)
{
    memset(s_iflcFixtures, 0, sizeof(s_iflcFixtures));
}

static const srfBspSurface_t *R_IFLC_FixtureMesh(int index)
{
    const msurface_t *s;
    const srfBspSurface_t *b;
    if (!tr.world || index < 0 || index >= tr.world->numWorldSurfaces) return NULL;
    s = &tr.world->surfaces[index];
    if (!s->data || (*s->data != SF_FACE && *s->data != SF_TRIANGLES)) return NULL;
    b = (const srfBspSurface_t *)s->data;
    return b->verts && b->indexes && b->numVerts >= 3 && b->numIndexes >= 3 ? b : NULL;
}

static void R_IFLC_FixtureBounds(const srfBspSurface_t *b, vec3_t lo, vec3_t hi)
{
    int i;
    ClearBounds(lo, hi);
    for (i = 0; i < b->numVerts; ++i) AddPointToBounds(b->verts[i].xyz, lo, hi);
}

static qboolean R_IFLC_FixtureInside(const vec3_t a, const vec3_t b,
    const vec3_t lo, const vec3_t hi)
{
    int k;
    for (k = 0; k < 3; ++k) if (a[k] < lo[k] - .125f || b[k] > hi[k] + .125f) return qfalse;
    return qtrue;
}

static qboolean R_IFLC_FixturePlane(const srfBspSurface_t *b, vec3_t n, float *d)
{
    vec3_t u, v;
    int i;
    for (i = 0; i + 2 < b->numIndexes; i += 3) {
        unsigned int a = b->indexes[i], c = b->indexes[i + 1], e = b->indexes[i + 2];
        if (a >= (unsigned int)b->numVerts || c >= (unsigned int)b->numVerts || e >= (unsigned int)b->numVerts) return qfalse;
        VectorSubtract(b->verts[c].xyz, b->verts[a].xyz, u);
        VectorSubtract(b->verts[e].xyz, b->verts[a].xyz, v);
        CrossProduct(u, v, n);
        if (VectorNormalize(n) > .01f) {
            *d = DotProduct(n, b->verts[a].xyz);
            for (i = 0; i < b->numVerts; ++i)
                if (fabsf(DotProduct(n, b->verts[i].xyz) - *d) > .125f) return qfalse;
            return qtrue;
        }
    }
    return qfalse;
}

static qboolean R_IFLC_FixtureAdjacent(const srfBspSurface_t *a, const srfBspSurface_t *b)
{
    int i, j, matches = 0;
    /* Require a shared edge, never join two objects at a single corner. */
    for (i = 0; i < a->numVerts; ++i) {
        for (j = 0; j < b->numVerts; ++j)
            if (R_IFLC_DistanceSquared(a->verts[i].xyz, b->verts[j].xyz) < .015625f) {
                if (++matches >= 2) return qtrue;
                break;
            }
    }
    return qfalse;
}

static void R_IFLC_PrepareFixture(int ownerIndex)
{
    iflcFixture_t *result;
    const iflcOwner_t *owner;
    vec3_t flameLo, flameHi, lo, hi, wallNormal, groupLo, groupHi;
    float height, margin, wallDistance = 1e30f, wallD = 0, seedDistance = 1e30f;
    int i, j, k, n = 0, seed = -1, groups = 0, flameCount = 0;
    int candidates[IFLC_FIXTURE_CAP];
    qboolean included[IFLC_FIXTURE_CAP], changed, supportAmbiguous = qfalse;
    float minDepth = 1e30f, maxDepth = -1e30f;
    if (ownerIndex < 0 || ownerIndex >= s_iflcOwnerCount) return;
    result = &s_iflcFixtures[ownerIndex];
    if (result->built) return;
    result->built = qtrue;
    owner = &s_iflcOwners[ownerIndex];
    if (owner->kind != IFLC_SURFACE || owner->ambiguous || !tr.world) return;
    ClearBounds(flameLo, flameHi);
    for (i = 0; i < s_iflcSurfaceCount; ++i) if (s_iflcSurfaces[i].owner == ownerIndex) {
        const srfBspSurface_t *b = R_IFLC_FixtureMesh(s_iflcSurfaces[i].surfaceIndex);
        if (!b || ++flameCount > 8) return;
        for (j = 0; j < b->numVerts; ++j) AddPointToBounds(b->verts[j].xyz, flameLo, flameHi);
    }
    if (!flameCount) return;
    height = flameHi[2] - flameLo[2];
    if (height < 12 || height > 128 || flameHi[0] - flameLo[0] > 64 || flameHi[1] - flameLo[1] > 64) return;
    margin = Com_Clamp(8, 16, height * .25f);
    for (k = 0; k < 3; ++k) { lo[k] = flameLo[k] - margin; hi[k] = flameHi[k] + margin; }
    /* A crossed flame can collapse to a narrow AABB axis after rotation.
     * Use its horizontal span symmetrically; do not depend on wall orientation. */
    for (k = 0; k < 2; ++k) {
        float halfSpan = .5f * MAX(flameHi[0] - flameLo[0], flameHi[1] - flameLo[1]);
        lo[k] = owner->origin[k] - halfSpan - margin;
        hi[k] = owner->origin[k] + halfSpan + margin;
    }
    lo[2] = flameLo[2] - Com_Clamp(12, 32, height * .5f);
    hi[2] = flameHi[2] + 4;
    /* Find a large planar mounting wall intersected by the source normal ray.
     * Small co-planar wall fragments are protected by this same plane below.
     * Floors, ceilings, floating braziers and ambiguous corners fail closed. */
    for (i = 0; i < tr.world->numWorldSurfaces; ++i) {
        const srfBspSurface_t *b = R_IFLC_FixtureMesh(i);
        vec3_t a, c, normal, ray;
        float d, distance, hit;
        if (!b || !R_IFLC_SurfaceBlocks(&tr.world->surfaces[i]) || tr.world->surfaces[i].shader->numDeforms) continue;
        R_IFLC_FixtureBounds(b, a, c);
        if (R_IFLC_FixtureInside(a, c, lo, hi) || !R_IFLC_FixturePlane(b, normal, &d) || fabsf(normal[2]) > .25f) continue;
        distance = DotProduct(normal, owner->origin) - d;
        if (distance < 0) { VectorNegate(normal, normal); d = -d; distance = -distance; }
        if (distance < 1 || distance > 32 || distance > wallDistance + 1) continue;
        VectorNegate(normal, ray);
        if (!R_IFLC_RaySurface(&tr.world->surfaces[i], owner->origin, ray, distance + .25f, &hit)) continue;
        if (wallDistance < 1e29f && fabsf(distance - wallDistance) <= 1 && DotProduct(normal, wallNormal) < .95f) {
            supportAmbiguous = qtrue; continue;
        }
        if (distance < wallDistance) {
            if (distance < wallDistance - 1) supportAmbiguous = qfalse;
            wallDistance = distance; wallD = d; VectorCopy(normal, wallNormal);
        }
    }
    if (wallDistance > 32 || supportAmbiguous) return;
    for (i = 0; i < tr.world->numWorldSurfaces; ++i) {
        const srfBspSurface_t *b = R_IFLC_FixtureMesh(i);
        vec3_t a, c;
        float least = 1e30f, greatest = -1e30f, distance = 0;
        if (!b || b->numVerts > 32 || !R_IFLC_SurfaceBlocks(&tr.world->surfaces[i]) ||
            tr.world->surfaces[i].shader->numDeforms || tr.world->surfaces[i].shader->polygonOffset) continue;
        R_IFLC_FixtureBounds(b, a, c);
        if (!R_IFLC_FixtureInside(a, c, lo, hi)) continue;
        for (j = 0; j < b->numVerts; ++j) {
            float depth = DotProduct(wallNormal, b->verts[j].xyz) - wallD;
            least = MIN(least, depth); greatest = MAX(greatest, depth);
        }
        if (least < -.25f || greatest < .5f) continue;
        if (n >= IFLC_FIXTURE_CAP) return;
        candidates[n] = i;
        for (k = 0; k < 3; ++k) {
            float v = owner->origin[k] < a[k] ? a[k] - owner->origin[k] : owner->origin[k] > c[k] ? owner->origin[k] - c[k] : 0;
            distance += v * v;
        }
        if (distance < seedDistance) { seedDistance = distance; seed = n; }
        ++n;
    }
    if (seed < 0 || seedDistance > height * height * .25f) return;
    memset(included, 0, sizeof(included)); included[seed] = qtrue;
    do {
        changed = qfalse;
        for (i = 0; i < n; ++i) if (!included[i])
            for (j = 0; j < n; ++j) if (included[j] &&
                R_IFLC_FixtureAdjacent(R_IFLC_FixtureMesh(candidates[i]), R_IFLC_FixtureMesh(candidates[j]))) {
                included[i] = qtrue; changed = qtrue; break;
            }
    } while (changed);
    ClearBounds(groupLo, groupHi);
    for (i = 0; i < n; ++i) if (included[i]) {
        const srfBspSurface_t *b = R_IFLC_FixtureMesh(candidates[i]);
        ++groups;
        for (j = 0; j < b->numVerts; ++j) {
            float depth = DotProduct(wallNormal, b->verts[j].xyz) - wallD;
            minDepth = MIN(minDepth, depth); maxDepth = MAX(maxDepth, depth);
            AddPointToBounds(b->verts[j].xyz, groupLo, groupHi);
        }
    }
    /* Require a three-dimensional mount actually touching the wall and the
     * flame base. A loose nearby object or a thin single wall tile is not enough. */
    if (groups < 3 || minDepth > 1 || maxDepth < 4 || groupLo[2] > flameLo[2] + 1 ||
        groupHi[2] < flameLo[2] + 8) return;
    for (k = 0; k < 3; ++k) if (groupHi[k] - groupLo[k] < 2) return;
    if (owner->origin[0] < groupLo[0] - margin || owner->origin[0] > groupHi[0] + margin ||
        owner->origin[1] < groupLo[1] - margin || owner->origin[1] > groupHi[1] + margin) return;
    for (i = 0; i < n; ++i) if (included[i]) result->surfaces[result->count++] = candidates[i];
    result->policyKey = R_IFLC_Hash(result->surfaces, result->count * sizeof(int)) ^ s_iflcFingerprint ^
        R_IFLC_Hash(owner->key, (int)strlen(owner->key));
    if (!result->policyKey) result->policyKey = 1;
}

int R_IFLC_ShadowFixture(const dlight_t *dl)
{
    int i;
    if (!dl || !dl->iflcOptIn || !s_iflcReady || s_iflcCatalogOverflow) return 0;
    for (i = 0; i < s_iflcOwnerCount; ++i) {
        if (s_iflcOwners[i].kind != IFLC_SURFACE || s_iflcOwners[i].ambiguous ||
            R_IFLC_DistanceSquared(dl->origin, s_iflcOwners[i].origin) > .0001f) continue;
        R_IFLC_PrepareFixture(i);
        return s_iflcFixtures[i].count ? i + 1 : 0;
    }
    return 0;
}

unsigned int R_IFLC_FixturePolicyKey(int fixture)
{
    return fixture > 0 && fixture <= s_iflcOwnerCount ? s_iflcFixtures[fixture - 1].policyKey : 0;
}

qboolean R_IFLC_SuppressSelfCaster(const msurface_t *surface)
{
    const iflcFixture_t *f;
    int left, right, index, fixture = tr.viewParms.iflcFixture;
    if (!s_iflcReady || fixture <= 0 || fixture > s_iflcOwnerCount ||
        tr.currentEntityNum != REFENTITYNUM_WORLD || !tr.world ||
        (tr.viewParms.flags & (VPF_SHADOWMAP | VPF_DEPTHSHADOW)) != (VPF_SHADOWMAP | VPF_DEPTHSHADOW) ||
        (tr.viewParms.flags & (VPF_ORTHOGRAPHIC | VPF_FIREVOL_SYNTHETIC_SHADOW))) return qfalse;
    f = &s_iflcFixtures[fixture - 1];
    if (!f->count || !f->policyKey || f->policyKey != tr.viewParms.iflcFixtureKey ||
        surface < tr.world->surfaces || surface >= tr.world->surfaces + tr.world->numWorldSurfaces) return qfalse;
    index = (int)(surface - tr.world->surfaces);
    left = 0; right = f->count - 1;
    while (left <= right) {
        int mid = (left + right) / 2;
        if (index == f->surfaces[mid]) return qtrue;
        if (index < f->surfaces[mid]) right = mid - 1; else left = mid + 1;
    }
    return qfalse;
}
