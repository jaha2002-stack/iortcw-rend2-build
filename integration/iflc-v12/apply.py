#!/usr/bin/env python3
"""Narrow wall-torch shaft fallback; preserve successful V1.1 classifications."""
from pathlib import Path
import argparse,hashlib,json,difflib
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('evidence',type=Path);a=p.parse_args()
a.evidence.mkdir(parents=True,exist_ok=True)
f=a.source/'SP/code/rend2/tr_iflc_fixture.inc';before=f.read_text();t=before
def replace(old,new):
 global t
 assert t.count(old)==1,(old,t.count(old))
 t=t.replace(old,new)
replace('static void R_IFLC_PrepareFixture(int ownerIndex)\n{','''/* Try the accepted compact mount first, then only a connected narrow shaft. */
static void R_IFLC_PrepareFixtureMode(int ownerIndex, qboolean slender)
{''')
replace('    if (result->built) return;','    if (result->built && !slender) return;')
replace('    margin = Com_Clamp(8, 16, height * .25f);','''    if (slender && (height < 16 || height > 64 ||
        flameHi[0] - flameLo[0] > height * .75f ||
        flameHi[1] - flameLo[1] > height * .75f)) return;
    margin = slender ? 16.0f : Com_Clamp(8, 16, height * .25f);''')
replace('    hi[2] = flameHi[2] + 4;','''    hi[2] = flameHi[2] + 4;
    if (slender) {
        /* Shafts end below the flame. Structural-plane/ownership gates remain. */
        lo[2] = flameLo[2] - Com_Clamp(24, 64, height * 1.25f);
        hi[2] = flameLo[2] + 4;
    }''')
replace('    if (seed < 0 || seedDistance > height * height * .25f) return;',
'    if (seed < 0 || seedDistance > height * height * (slender ? .5625f : .25f)) return;')
replace('''    if (groups < 3 || minDepth > 1 || maxDepth < 4 || groupLo[2] > flameLo[2] + 1 ||
        groupHi[2] < flameLo[2] + 8) return;''','''    if (groups < 3 || minDepth > 1 || maxDepth < 4 || groupLo[2] > flameLo[2] + 1) return;
    if (!slender && groupHi[2] < flameLo[2] + 8) return;
    if (slender) {
        vec3_t tangent;
        float tMin = 1e30f, tMax = -1e30f, center, span = groupHi[2] - groupLo[2];
        /* Narrow in wall-tangent space, tall, top directly below flame base. */
        if (span < height * .6f || span > height * 1.75f ||
            groupHi[2] < flameLo[2] - 4 || groupHi[2] > flameLo[2] + 4) return;
        VectorSet(tangent, -wallNormal[1], wallNormal[0], 0);
        if (VectorNormalize(tangent) < .9f) return;
        for (i = 0; i < n; ++i) if (included[i]) {
            const srfBspSurface_t *b = R_IFLC_FixtureMesh(candidates[i]);
            for (j = 0; j < b->numVerts; ++j) {
                float v = DotProduct(tangent, b->verts[j].xyz);
                tMin = MIN(tMin, v); tMax = MAX(tMax, v);
            }
        }
        center = DotProduct(tangent, owner->origin);
        if (tMax - tMin > MIN(12.0f, height * .5f) ||
            center < tMin - 4 || center > tMax + 4) return;
    }''')
replace('int R_IFLC_ShadowFixture(const dlight_t *dl)','''static void R_IFLC_PrepareFixture(int ownerIndex)
{
    if (ownerIndex < 0 || ownerIndex >= s_iflcOwnerCount || s_iflcFixtures[ownerIndex].built) return;
    R_IFLC_PrepareFixtureMode(ownerIndex, qfalse);
    if (!s_iflcFixtures[ownerIndex].count) R_IFLC_PrepareFixtureMode(ownerIndex, qtrue);
}

int R_IFLC_ShadowFixture(const dlight_t *dl)''')
f.write_text(t)
assert not any(x in t.lower() for x in ('crypt1','crypt2','castle','2933','2992','textures/'))
report={'base_run':41758201175,'base_renderer_run':41710067608,'changed_files':['SP/code/rend2/tr_iflc_fixture.inc'],
'before_sha256':hashlib.sha256(before.encode()).hexdigest(),'after_sha256':hashlib.sha256(t.encode()).hexdigest(),
'algorithm':'accepted compact mount first; connected slender wall-torch fallback; own opt-in Direct only',
'new_production_cvars':[],'positions_changed':False,'shadow_budgets_changed':False,'native_lanterns_changed':False,'visual_status':'NOT_VERIFIED_BY_APPLY_SCRIPT'}
(a.evidence/'IFLC12_SOURCE_PROOF.json').write_text(json.dumps(report,indent=2)+'\n')
(a.evidence/'IFLC12.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),t.splitlines(True),fromfile='a/SP/code/rend2/tr_iflc_fixture.inc',tofile='b/SP/code/rend2/tr_iflc_fixture.inc')))
print('IFLC12_SCOPED_GEOMETRY_PATCH_APPLIED',report['after_sha256'])
