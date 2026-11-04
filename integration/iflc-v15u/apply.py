#!/usr/bin/env python3
"""IFLC V1.5 Universal: MANUAL self_pick is owner-anchored, AUTO remains flame-anchored."""
from pathlib import Path
import hashlib,json,sys
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
before={p.relative_to(src).as_posix():p.read_bytes() for p in (src/'SP/code').rglob('*') if p.is_file()}

p=src/'SP/code/rend2/tr_iflc_self.inc'
s=p.read_text()
old='''    vec3_t flameLo,flameHi,anchor,seedLo,seedHi,groupLo,groupHi;int vertices=0;
    vec3_t planes[64];float planeD[64];int planesN=0;
    if(!profile || profile->selfSeedCount<=0 || !R_IFLC_SelfBounds(ownerIndex,flameLo,flameHi,anchor))return qfalse;
'''
new='''    vec3_t anchor,seedLo,seedHi,groupLo,groupHi;int vertices=0;
    vec3_t planes[64];float planeD[64];int planesN=0;
    if(ownerIndex<0 || ownerIndex>=s_iflcOwnerCount || s_iflcOwners[ownerIndex].ambiguous ||
       !profile || profile->selfSeedCount<=0)return qfalse;
    /* UNIVERSAL MANUAL mode is intentionally independent of flame bounds.
     * dw_fl_select has already established a unique stable owner.  Its light
     * origin is the anchor; the user-picked solid BSP part is the geometric
     * seed. AUTO remains unchanged below and still requires R_IFLC_SelfBounds. */
    VectorCopy(s_iflcOwners[ownerIndex].origin,anchor);
'''
assert s.count(old)==1,'manual builder anchor block changed unexpectedly'
s=s.replace(old,new)
old='''    if(!R_IFLC_FixtureOpaque(s) || s->shader->numDeforms || s->shader->polygonOffset || R_IFLC_SelfIsFlameSurface(ownerIndex,index))return qfalse;
'''
new='''    if(!R_IFLC_FixtureOpaque(s) || s->shader->numDeforms || s->shader->polygonOffset ||
       R_IFLC_SelfIsFlameSurface(ownerIndex,index) || R_IFLC_FlameShader(s->shader))return qfalse;
'''
assert s.count(old)==1,'manual surface flame guard changed unexpectedly'
s=s.replace(old,new)
p.write_text(s)

p=src/'SP/code/rend2/tr_iflc.inc'
s=p.read_text()
old='''    vec3_t lo, hi, anchor; float nearest = 512.0f, hit; int i, selected = -1;
    if (!R_IFLC_SelectedEditable() || !s_iflcViewValid) return;
    if (!R_IFLC_SelfBounds(s_iflcSelected, lo, hi, anchor)) {
        ri.Printf(PRINT_WARNING, "IFLC: ambiguous or missing flame geometry; own-body binding refused.\\n"); return;
    }
'''
new='''    float nearest = 512.0f, hit; int i, selected = -1;
    if (!R_IFLC_SelectedEditable() || !s_iflcViewValid) return;
    /* V1.5 Universal: manual body selection trusts the already selected
     * unambiguous owner, not compact flame BSP bounds. This is what allows
     * native/promoted/VOLUME_ONLY fire fixtures whose visual flame geometry is
     * split, missing or shared to use the same safe manual workflow. */
'''
assert s.count(old)==1,'self_pick flame-bounds gate changed unexpectedly'
s=s.replace(old,new)
old='''    ri.Printf(PRINT_ALL,"IFLC: bound exact body surface %d; safe local group=%d surfaces, manualSeeds=%d. Use dw_fl_set selfshadow 0 and dw_fl_save.\\n",selected,test.count,candidate.selfSeedCount);
'''
new='''    ri.Printf(PRINT_ALL,"IFLC V1.5 Universal: bound exact body surface %d; owner=%s route=%s safeLocalGroup=%d surfaces manualSeeds=%d. Use dw_fl_set selfshadow 0 and dw_fl_save.\\n",
        selected,s_iflcOwners[s_iflcSelected].key,R_IFLC_Route(&s_iflcOwners[s_iflcSelected]),test.count,candidate.selfSeedCount);
'''
assert s.count(old)==1
s=s.replace(old,new)
p.write_text(s)

after={p.relative_to(src).as_posix():p.read_bytes() for p in (src/'SP/code').rglob('*') if p.is_file()}
changed=sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p))
assert changed==['SP/code/rend2/tr_iflc.inc','SP/code/rend2/tr_iflc_self.inc'],changed
assert all(before[x]==after[x] for x in before if '/glsl/' in x)
assert before['SP/code/rend2/tr_electric_fixture.inc']==after['SP/code/rend2/tr_electric_fixture.inc']
proof={
 'base':'IFLC V1.5 exact-body commit 5934ff7ec8e2193d5f805db25983e4c3a40819e5',
 'base_run':41827953550,
 'changed':changed,
 'manual_anchor':'selected stable owner origin',
 'manual_requires_flame_bounds':False,
 'auto_requires_flame_bounds':True,
 'supported_owner_kinds':['NATIVE_FIRE','PROMOTED_FIRE','VOLUME_ONLY'],
 'architecture_guards_preserved':True,
 'global_flame_shader_guard_added':True,
 'glsl_unchanged':True,
 'electric_fixture_unchanged':True,
}
(ev/'IFLC15U_SOURCE_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
(ev/'IFLC15U_SOURCE_SHA256.json').write_text(json.dumps({p:sha(b) for p,b in after.items()},indent=2)+'\n')
print('IFLC15U_PATCH_APPLIED',changed)
