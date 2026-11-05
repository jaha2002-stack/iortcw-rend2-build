#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
p=src/'SP/code/rend2/tr_elss.inc'
s=p.read_text()
before=s

old='''static void R_ELSS_PrepareProfileFixture(int slot)
{
    int oi;if(slot<0||slot>=ELSS_MAX_PROFILES||s_elssFixtures[slot].built)return;s_elssFixtures[slot].built=qtrue;if(!s_elssProfiles[slot].used||s_elssProfiles[slot].selfShadow!=1||s_elssProfiles[slot].seedCount<=0)return;oi=R_ELSS_FindOwner(s_elssProfiles[slot].key);if(oi<0||s_elssOwners[oi].ambiguous)return;(void)R_ELSS_BuildManual(&s_elssProfiles[slot],&s_elssOwners[oi],&s_elssFixtures[slot]);
}
'''
new='''static void R_ELSS_PrepareProfileFixture(int slot)
{
    int oi;
    if(slot<0||slot>=ELSS_MAX_PROFILES||s_elssFixtures[slot].built)return;
    if(!s_elssProfiles[slot].used||s_elssProfiles[slot].selfShadow!=1||s_elssProfiles[slot].seedCount<=0) {
        s_elssFixtures[slot].built=qtrue;
        return;
    }
    /*
     * Persistence fix: after a fresh map/game load profiles are parsed before
     * electric DLight owners have been rediscovered. Do NOT poison the fixture
     * cache with built=true while the stable owner is still absent. A later
     * frame can then build the saved own-body mask as soon as that owner exists.
     */
    oi=R_ELSS_FindOwner(s_elssProfiles[slot].key);
    if(oi<0||s_elssOwners[oi].ambiguous)return;
    s_elssFixtures[slot].built=qtrue;
    (void)R_ELSS_BuildManual(&s_elssProfiles[slot],&s_elssOwners[oi],&s_elssFixtures[slot]);
}
'''
assert s.count(old)==1, "PrepareProfileFixture block mismatch"
s=s.replace(old,new)

old='''void R_ELSS_Frame(const refdef_t *fd)
{
    int i,sceneEnd;if(!fd||!tr.world||(fd->rdflags&(RDF_NOWORLDMODEL|RDF_SKYBOXPORTAL)))return;if(!R_ELSS_EnsureMap()||!R_StaticPromoteBuildPersistentRegistry())return;
    for(i=0;i<s_elssOwnerCount;++i){s_elssOwners[i].runtimeCount=0;s_elssOwners[i].runtimeIndex=-1;s_elssOwners[i].shadowSlot=-2;s_elssOwners[i].radius=0;s_elssOwners[i].nativeAuthored=s_elssOwners[i].promoted=s_elssOwners[i].localVolumetric=qfalse;s_elssOwners[i].ambiguous=qfalse;}
    if(r_dwElectricLightControl&&r_dwElectricLightControl->integer)for(i=0;i<ELSS_MAX_PROFILES;++i)if(s_elssProfiles[i].used&&s_elssProfiles[i].selfShadow==1&&s_elssProfiles[i].seedCount)R_ELSS_PrepareProfileFixture(i);
    sceneEnd=r_numdlights;for(i=r_firstSceneDlight;i<sceneEnd;++i)if(R_ELSS_IsElectric(&backEndData->dlights[i]))R_ELSS_UpsertOwner(&backEndData->dlights[i],i-r_firstSceneDlight);
}
'''
new='''void R_ELSS_Frame(const refdef_t *fd)
{
    int i,sceneEnd;if(!fd||!tr.world||(fd->rdflags&(RDF_NOWORLDMODEL|RDF_SKYBOXPORTAL)))return;if(!R_ELSS_EnsureMap()||!R_StaticPromoteBuildPersistentRegistry())return;
    for(i=0;i<s_elssOwnerCount;++i){s_elssOwners[i].runtimeCount=0;s_elssOwners[i].runtimeIndex=-1;s_elssOwners[i].shadowSlot=-2;s_elssOwners[i].radius=0;s_elssOwners[i].nativeAuthored=s_elssOwners[i].promoted=s_elssOwners[i].localVolumetric=qfalse;s_elssOwners[i].ambiguous=qfalse;}
    /*
     * Persistence fix: rediscover this frame's physical electric owners first.
     * Saved OFF profiles can then resolve their stable fixture/native/origin key
     * on the very first usable frame after restarting the game.
     */
    sceneEnd=r_numdlights;for(i=r_firstSceneDlight;i<sceneEnd;++i)if(R_ELSS_IsElectric(&backEndData->dlights[i]))R_ELSS_UpsertOwner(&backEndData->dlights[i],i-r_firstSceneDlight);
    if(r_dwElectricLightControl&&r_dwElectricLightControl->integer)for(i=0;i<ELSS_MAX_PROFILES;++i)if(s_elssProfiles[i].used&&s_elssProfiles[i].selfShadow==1&&s_elssProfiles[i].seedCount)R_ELSS_PrepareProfileFixture(i);
}
'''
assert s.count(old)==1, "Frame block mismatch"
s=s.replace(old,new)
p.write_text(s)

proof={
 "version":"ELSS V1.0.1 Persistence Fix",
 "base":"ELSS V1 on IFLC V1.5 Universal",
 "base_iflc_run":41895006605,
 "change":["R_ELSS_Frame owner discovery order","R_ELSS_PrepareProfileFixture cache readiness"],
 "profile_format":"DW_ELSS 1 unchanged",
 "commands":"unchanged",
 "shadow_slot_policy":"unchanged",
 "iflc_v15u":"unchanged",
 "glsl":"unchanged",
 "expected_behavior":"saved selfshadow OFF automatically rebinds after fresh game/map startup"
}
(ev/'ELSS_V101_PERSISTENCE_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
(ev/'ELSS_V101_TR_ELSS_SHA256.txt').write_text(hashlib.sha256(s.encode()).hexdigest()+'  tr_elss.inc\n')
print("ELSS_V101_PERSISTENCE_PATCH_APPLIED")
