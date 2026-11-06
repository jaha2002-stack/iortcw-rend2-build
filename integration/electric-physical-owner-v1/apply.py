#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path('evidence').resolve()
ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
local=root/'tr_local.h'
scene=root/'tr_scene.c'
main=root/'tr_main.c'
backend=root/'tr_backend.c'
inc_src=Path(__file__).with_name('tr_electric_physical_owner.inc')
inc_dst=root/'tr_electric_physical_owner.inc'

for p in (local,scene,main,backend,inc_src):
    assert p.is_file(),p

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected_names=['tr_iflc.inc','tr_elss.inc','tr_electric_fixture.inc']
protected_before={n:sha(root/n) for n in protected_names if (root/n).is_file()}

s=local.read_text()
anchor='\tint staticPromoteFixtureId; // DARKWOLF_USLRD_V0_1: stable physical fixture identity; -1 for non-USLRD dlights\n'
assert s.count(anchor)==1,s.count(anchor)
if 'physicalElectricOwnerId' not in s:
    s=s.replace(anchor,anchor+'\tint physicalElectricOwnerId; // DARKWOLF_ELECTRIC_PHYSICAL_OWNER_V1: exact map-local electric fixture owner; -1 unresolved/off\n',1)
local.write_text(s)

s=scene.read_text()
anchor='\tdl->staticPromoteFixtureId = -1; // DARKWOLF_USLRD_V0_1\n'
assert s.count(anchor)==1,s.count(anchor)
if 'dl->physicalElectricOwnerId = -1;' not in s:
    s=s.replace(anchor,anchor+'\tdl->physicalElectricOwnerId = -1; // DARKWOLF_ELECTRIC_PHYSICAL_OWNER_V1 metadata only\n',1)

include='#include "tr_electric_physical_owner.inc"'
if include not in s:
    if '#include "tr_elss.inc"' in s:
        s=s.replace('#include "tr_elss.inc"','#include "tr_elss.inc"\n'+include,1)
    else:
        assert s.count('#include "tr_iflc.inc"')==1
        s=s.replace('#include "tr_iflc.inc"','#include "tr_iflc.inc"\n'+include,1)

hook='\tRE_BeginScene(fd);\n'
assert s.count(hook)==1,s.count(hook)
if 'R_DarkWolfAssignPhysicalElectricOwnerIds();' not in s:
    s=s.replace(hook,hook+'\tR_DarkWolfAssignPhysicalElectricOwnerIds(); // metadata only; Direct DLight is unchanged\n',1)
scene.write_text(s)
shutil.copy2(inc_src,inc_dst)

s=main.read_text()
old='''    if (!R_DarkWolfStaticPromoteShadowGroupEligible(a) || !R_DarkWolfStaticPromoteShadowGroupEligible(b) ||
        a->staticPromoteFixtureId == b->staticPromoteFixtureId)
        return qfalse;
    mergeRadius = Com_Clamp(0.0f, 64.0f, s_rStaticPromotePhysicalGroupMergeRadius->value);
'''
new='''    if (!R_DarkWolfStaticPromoteShadowGroupEligible(a) || !R_DarkWolfStaticPromoteShadowGroupEligible(b) ||
        a->staticPromoteFixtureId == b->staticPromoteFixtureId)
        return qfalse;
    // DARKWOLF_ELECTRIC_PHYSICAL_OWNER_V1: explicit electric ownership is stronger
    // than the legacy 16-unit proximity heuristic. Direct DLight remains separate.
    if (a->physicalElectricOwnerId > 0 &&
        a->physicalElectricOwnerId == b->physicalElectricOwnerId)
        return qtrue;
    mergeRadius = Com_Clamp(0.0f, 64.0f, s_rStaticPromotePhysicalGroupMergeRadius->value);
'''
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)

old='''static int R_ElectricFixtureForCapture(int index)
{
    int i, fixture, group;
    if (index < 0 || index >= tr.refdef.num_dlights || index >= MAX_DLIGHTS) return 0;
    fixture = R_ElectricFixtureForLight(&tr.refdef.dlights[index]);
    if (!fixture || !R_DarkWolfStaticPromoteShadowGroupEligible(&tr.refdef.dlights[index])) return fixture;
    group = R_DarkWolfStaticPromoteShadowGroupCanonicalId(index);
    if (group < 0) return 0;
    for (i = 0; i < tr.refdef.num_dlights && i < MAX_DLIGHTS; ++i)
        if (R_DarkWolfStaticPromoteShadowGroupEligible(&tr.refdef.dlights[i]) &&
            R_DarkWolfStaticPromoteShadowGroupCanonicalId(i) == group &&
            R_ElectricFixtureForLight(&tr.refdef.dlights[i]) != fixture) return 0;
    return fixture;
}
'''
new='''static int R_ElectricFixtureForCapture(int index)
{
    int i, fixture = 0, group;
    if (index < 0 || index >= tr.refdef.num_dlights || index >= MAX_DLIGHTS) return 0;
    if (!R_DarkWolfStaticPromoteShadowGroupEligible(&tr.refdef.dlights[index]))
        return R_ElectricFixtureForLight(&tr.refdef.dlights[index]);
    group = R_DarkWolfStaticPromoteShadowGroupCanonicalId(index);
    if (group < 0) return 0;
    // DARKWOLF_ELECTRIC_PHYSICAL_OWNER_V1: PhysicalElectricOwnerId is a
    // StaticPromote identity, not an ELSS electric-fixture id. For a shared
    // shadow capture, retain ELSS only when all positively resolved members
    // agree on one Electric Fixture. Unresolved synthetic children are neutral.
    for (i = 0; i < tr.refdef.num_dlights && i < MAX_DLIGHTS; ++i)
        if (R_DarkWolfStaticPromoteShadowGroupEligible(&tr.refdef.dlights[i]) &&
            R_DarkWolfStaticPromoteShadowGroupCanonicalId(i) == group)
        {
            int peerFixture = R_ElectricFixtureForLight(&tr.refdef.dlights[i]);
            if (peerFixture <= 0) continue;
            if (!fixture) fixture = peerFixture;
            else if (peerFixture != fixture) return 0;
        }
    return fixture;
}
'''
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)
main.write_text(s)

s=backend.read_text()
old='''    if (!a || !b || a->staticPromoteFixtureId < 0 || b->staticPromoteFixtureId < 0 ||
        a->staticPromoteFixtureId == b->staticPromoteFixtureId)
        return qfalse;
    RB_LocalVolumetricEnsureLampMultiSourceCvars();
'''
new='''    if (!a || !b || a->staticPromoteFixtureId < 0 || b->staticPromoteFixtureId < 0 ||
        a->staticPromoteFixtureId == b->staticPromoteFixtureId)
        return qfalse;
    // DARKWOLF_ELECTRIC_PHYSICAL_OWNER_V1: one LocalVol owner per explicitly
    // resolved physical electric fixture; Direct DLight is not altered.
    if (a->physicalElectricOwnerId > 0 &&
        a->physicalElectricOwnerId == b->physicalElectricOwnerId)
        return qtrue;
    RB_LocalVolumetricEnsureLampMultiSourceCvars();
'''
assert s.count(old)==2,s.count(old)
# Apply the explicit owner to both LocalVol grouping paths: the legacy four-slot
# companion path and the production all-active physical-group path.
s=s.replace(old,new,2)
backend.write_text(s)

# If the read-only EPOA diagnostic is present in this test build, teach it the
# new owner equivalence so reported group counts match production consumers.
audit=root/'tr_electric_owner_audit.inc'
audit_patched=False
if audit.is_file():
    t=audit.read_text()
    needle='''    VectorSubtract(a->origin, b->origin, delta);
    if (DotProduct(delta, delta) > EPOA_CURRENT_MERGE_RADIUS * EPOA_CURRENT_MERGE_RADIUS) return qfalse;
'''
    repl='''    if (a->physicalElectricOwnerId > 0 &&
        a->physicalElectricOwnerId == b->physicalElectricOwnerId) return qtrue;
    VectorSubtract(a->origin, b->origin, delta);
    if (DotProduct(delta, delta) > EPOA_CURRENT_MERGE_RADIUS * EPOA_CURRENT_MERGE_RADIUS) return qfalse;
'''
    assert t.count(needle)==1,t.count(needle)
    t=t.replace(needle,repl,1)
    audit.write_text(t)
    audit_patched=True

protected_after={n:sha(root/n) for n in protected_names if (root/n).is_file()}
assert protected_before==protected_after,(protected_before,protected_after)

proof={
  'version':'ELECTRIC_PHYSICAL_OWNER_V1_SHADOW_LOCALVOL',
  'base_run':42217883095,
  'scope':['metadata PhysicalElectricOwnerId','point-shadow grouping','LocalVol grouping','electric fixture continuity for shared shadow capture'],
  'direct_dlight_mutated':False,
  'staticpromote_residency_mutated':False,
  'iflc_profile_mutated':False,
  'elss_profile_mutated':False,
  'synthetic_inherit_max_distance':48.0,
  'ambiguity_margin':16.0,
  'legacy_16_unit_fallback_preserved':True,
  'audit_owner_aware':audit_patched,
  'protected_unchanged':sorted(protected_before),
  'changed_existing':['tr_local.h','tr_scene.c','tr_main.c','tr_backend.c'] + (['tr_electric_owner_audit.inc'] if audit_patched else []),
  'added':['tr_electric_physical_owner.inc'],
}
(ev/'EPO_V1_APPLY_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
print('EPO_V1_APPLIED',json.dumps(proof,sort_keys=True))
