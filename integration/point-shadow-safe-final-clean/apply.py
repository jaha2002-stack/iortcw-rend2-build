#!/usr/bin/env python3
"""Clean Production after exactly two user-facing shadow test releases.
Accepted material/textures: texture V2 (Actions #41286257713) atop #41019985033.
Carry ONLY independently confirmed Boss1 source-local fix, not V5's
unproven generic Crypt/Factory classifier. No new cvars or telemetry.
"""
import argparse, hashlib, json
from pathlib import Path

SOURCE="SP/code/rend2/tr_backend.c"
EXPECTED_V2_SHA="ee22de02f024fccbad22c69d5b6c1ede5c56b2f4f3bd6d307c6880ad5d950be3"
MARK="DARKWOLF_BOSS1_PROVEN_SOURCE_LOCAL_FIX_CLEAN_PRODUCTION_V1"
CODE=r'''
/* DARKWOLF_BOSS1_PROVEN_SOURCE_LOCAL_FIX_CLEAN_PRODUCTION_V1
 * Production, NOT a generic material/mesh blacklist.
 * Accepted tests: V3.2 A/B/A + V5 six-phase proof, boss1 scene.
 * Only the verified unique world BSP housing surface belonging to one
 * exact point-light capture is not a caster for THAT light. It stays
 * visible and casts in all other light/shadow passes.
 *
 * No surface number, global texture class, CVar, shader edit, logging,
 * CSM, Fire/Tesla or unrelated caster/receiver change is introduced.
 * Any changed BSP version, ambiguity or source position FAILS OPEN.
 */
static const world_t *dwBoss1CleanWorld = NULL;
static const msurface_t *dwBoss1CleanSurfaces = NULL;
static const surfaceType_t *dwBoss1CleanCandidate = NULL;
static int dwBoss1CleanCount = -1;
static int dwBoss1CleanMainCount = -1;
static int dwBoss1CleanIndex = -1;
static qboolean dwBoss1CleanUnique = qfalse;

static qboolean DW_Boss1CleanAabbMatch(const msurface_t *s)
{
    const cullinfo_t *ci;
    if(!s || !s->data || !s->shader ||
       strcmp(s->shader->name,"textures/metal_misc/ametal_m03dm")!=0)
        return qfalse;
    ci=&s->cullinfo;
    if(!(ci->type & CULLINFO_BOX))return qfalse;
    if(fabsf(ci->bounds[0][0]-(-2799.02f))>0.25f ||
       fabsf(ci->bounds[0][1]-(-229.78f))>0.25f ||
       fabsf(ci->bounds[0][2]-(-40.53f))>0.25f ||
       fabsf(ci->bounds[1][0]-(-2774.36f))>0.25f ||
       fabsf(ci->bounds[1][1]-(-210.73f))>0.25f ||
       fabsf(ci->bounds[1][2]-(-16.56f))>0.25f)
        return qfalse;
    return qtrue;
}
static void DW_Boss1CleanResolve(void)
{
    int i,matched=0;
    if(dwBoss1CleanWorld==tr.world &&
       dwBoss1CleanSurfaces==tr.world->surfaces &&
       dwBoss1CleanCount==tr.world->numsurfaces &&
       dwBoss1CleanMainCount==tr.world->numWorldSurfaces)
        return;
    dwBoss1CleanWorld=tr.world;
    dwBoss1CleanSurfaces=tr.world->surfaces;
    dwBoss1CleanCount=tr.world->numsurfaces;
    dwBoss1CleanMainCount=tr.world->numWorldSurfaces;
    dwBoss1CleanCandidate=NULL;
    dwBoss1CleanIndex=-1;
    dwBoss1CleanUnique=qfalse;
    if(tr.world->numsurfaces!=7791 ||
       tr.world->numWorldSurfaces!=7274)return;
    for(i=0;i<tr.world->numWorldSurfaces;i++)
    {
        const msurface_t *s=&tr.world->surfaces[i];
        if(DW_Boss1CleanAabbMatch(s))
        {
            ++matched;
            dwBoss1CleanCandidate=s->data;
            dwBoss1CleanIndex=i;
            if(matched>1){dwBoss1CleanCandidate=NULL;dwBoss1CleanIndex=-1;return;}
        }
    }
    dwBoss1CleanUnique=(matched==1)?qtrue:qfalse;
}
static qboolean DW_Boss1CleanSkipSourceLocalCaster(const drawSurf_t *ds)
{
    int entityNum;
    if(!tr.world || !tr.world->surfaces || !ds || !ds->surface)
        return qfalse;
    if(strcmp(tr.world->baseName,"boss1")!=0 ||
       strcmp(tr.world->name,"maps/boss1.bsp")!=0)
        return qfalse;
    if((backEnd.viewParms.flags & (VPF_SHADOWMAP|VPF_DEPTHSHADOW)) !=
       (VPF_SHADOWMAP|VPF_DEPTHSHADOW))
        return qfalse;
    if(backEnd.viewParms.flags &
       (VPF_DLIGHT_WORLD_OCCLUSION|VPF_FIREVOL_SYNTHETIC_SHADOW))
        return qfalse;
    if(fabsf(backEnd.viewParms.or.origin[0]-(-2764.0f))>0.25f ||
       fabsf(backEnd.viewParms.or.origin[1]-(-219.0f))>0.25f ||
       fabsf(backEnd.viewParms.or.origin[2]-(-24.0f))>0.25f)
        return qfalse;
    entityNum=(ds->sort>>QSORT_REFENTITYNUM_SHIFT)&REFENTITYNUM_MASK;
    if(entityNum!=REFENTITYNUM_WORLD)return qfalse;
    DW_Boss1CleanResolve();
    if(!dwBoss1CleanUnique || ds->surface!=dwBoss1CleanCandidate)
        return qfalse;
    /* Revalidate the unique cached map-local fingerprint in O(1). */
    if(dwBoss1CleanIndex>=0 && dwBoss1CleanIndex<tr.world->numWorldSurfaces &&
       tr.world->surfaces[dwBoss1CleanIndex].data==ds->surface)
        return DW_Boss1CleanAabbMatch(&tr.world->surfaces[dwBoss1CleanIndex]);
    return qfalse;
}
'''
def one(s,a,b,label):
    c=s.count(a)
    assert c==1,(label,c)
    return s.replace(a,b,1)
def H(b):return hashlib.sha256(b).hexdigest()

def apply(root,check=False,proof=None):
    f=Path(root)/SOURCE
    before=f.read_text(encoding="utf-8")
    assert H(before.encode("utf-8"))==EXPECTED_V2_SHA,("unexpected TextureV2 production backend",H(before.encode()))
    assert MARK not in before
    for banned in ("DARKWOLF_POINT_V5_CROSSMAP_SOURCE_LOCAL_PROOF_41019985033",
                   "DARKWOLF_POINT_V4_AUTOMATIC_FIXTURE_ATTRIBUTION_DIAGNOSTIC_41019985033",
                   "DARKWOLF_POINT_V32_BOSS1_SOURCE_LOCAL_SELFSHADOW_GUARD_41019985033",
                   "DWPointV3CaptureSelected", "r_dwPointV5ProofMode"):
        assert banned not in before,("debug source leaked",banned)
    assert "DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886" in before
    assert "DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1" in before
    assert "VectorSet4(parms, cas, lut, (float)lutIndex, 0.0f);" in before
    signature="void RB_RenderDrawSurfList( drawSurf_t *drawSurfs, int numDrawSurfs )"
    # Use an exact proven C anchor; no direct editing of GLSL.
    loop="\tfor (i = 0, drawSurf = drawSurfs ; i < numDrawSurfs ; i++, drawSurf++) {\n"
    changed=one(before,signature,CODE+"\n"+signature,"function definition")
    changed=one(changed,loop,loop+
      "\t\t/* "+MARK+": narrowly scoped Boss1 ordinary point cubemap only. */\n"+
      "\t\tif(DW_Boss1CleanSkipSourceLocalCaster(drawSurf))continue;\n","drawlist loop")
    assert "DARKWOLF_STAGE11_UNIFIED_ASSET_SHADOW_COVERAGE_CLEAN_PRODUCTION_V1" in changed
    assert changed.count(MARK)>=3
    assert 'r_dwPointV5ProofMode' not in changed
    if not check:
        f.write_text(changed,encoding="utf-8")
    p={
       "release_kind":"FINAL_CLEAN_PRODUCTION_CONSERVATIVE",
       "accepted_original_run":41019985033,
       "accepted_texture_clean_run":41286257713,
       "last_shadow_proof_run":41294915333,
       "production_fix_scope":"One Boss1 source/caster fingerprint only, no numeric BSP ID",
       "default_behavior":"automatic only for exact matched Boss1 fixture; otherwise fail-open",
       "unresolved_maps":["Factory thick shadow attribution","Crypt1 octagonal shadow","Crypt2 octagonal shadow"],
       "modified_source_files":[SOURCE],
       "source_before_sha256":H(before.encode("utf-8")),
       "source_after_sha256":H(changed.encode("utf-8")),
       "unrelated_material_policy":"no globally suppressed material or shader",
       "no_new_cvars":True,
       "no_debug_or_telemetry":True,
       "all_other_shadow_sources_unchanged_by_rule":True,
       "fire_tesla_csm_unmodified":True,
       "stage11_full_coverage_except_one_proven_boss1_source_caster":True,
       "other_effects_and_shader_files_unchanged_by_fix":True,
       "crypt1_crypt2_proof":"NOT ACCEPTED; V5 dish group suppressed physically plausible basket and exposure varied",
       "factory_proof":"paired ladder rail filtering did not remove thick silhouette",
       "gpu_validation_of_new_binary":"PENDING; prior exact Boss1 V3.2/V5 behavior visually verified",
       "check_only":check
    }
    if proof:
        f2=Path(proof);f2.parent.mkdir(parents=True,exist_ok=True)
        f2.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DW_PS_FINAL_CONSERVATIVE_CLEAN_SOURCE_PASS")
    return p

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("root",type=Path);a.add_argument("--check-only",action="store_true")
    a.add_argument("--proof",type=Path)
    args=a.parse_args()
    apply(args.root,args.check_only,args.proof)
