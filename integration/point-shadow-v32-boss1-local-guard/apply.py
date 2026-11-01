#!/usr/bin/env python3
"""V3.2 TEST ONLY, exact #41019985033 reconstruction + V1/V2/V3/V31.
Boss1 spotlight: source-local removal of ONE proven oversized caster from ONE
ordinary point-light shadow cubemap only. All defaults OFF, FAIL OPEN.
Never change visible geometry, other lights, receivers, Fire/Tesla or Sun.
"""
import argparse,hashlib,json
from pathlib import Path

MARK="DARKWOLF_POINT_V32_BOSS1_SOURCE_LOCAL_SELFSHADOW_GUARD_41019985033"
CVAR="r_dwPointV32FixtureGuard"
EXPECTED={
  "tr_local.h":"88974f624cf67753126db59a21a8520d4c2ba8487163906400b59d93a7f0f58d",
  "tr_init.c":"e913660e0ff39721055a83dd1b56122d563eea8578a942fc7978355c0dbd9948",
  "tr_backend.c":"f9d57a90d2df9cfa4a6bcb7dc998ecb2d33f5e02a0353e16c0ef3bd891070c06",
}

def one(s,a,b,why):
    count=s.count(a)
    assert count==1,(why,count)
    return s.replace(a,b,1)
def H(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()

EXCLUDE_FUNCTION=r'''
/* DARKWOLF_POINT_V32_BOSS1_SOURCE_LOCAL_SELFSHADOW_GUARD_41019985033
 * Boss1 source-local world-mesh caster guard (EXPERIMENTAL, default OFF).
 * Exact GPU A/B evidence: world surface 7232 creates enlarged polygon shadow;
 * excluding only 7232 preserves the fixture stand + bracket shadow.
 *
 * No geometry/shader/global material class removal. Other lamps may still use
 * this mesh as a caster. The illuminated world still draws this mesh.
 * The source matcher is world-space, NOT the erroneous V3 dlight index.
 * Strict map, counts, shader, AABB and source match: any drift FAIL OPEN.
 */
static qboolean DWPointV32SkipProvenFixtureCaster(const drawSurf_t *ds)
{
    const msurface_t *surf;
    const cullinfo_t *ci;
    const vec3_t *capture;
    float tolerance=0.25f;
    int entityNum;
    static int loggedFrame=-1;
    static qboolean loggedOnce=qfalse;

    if(!r_dwPointV32FixtureGuard || r_dwPointV32FixtureGuard->integer!=1)
        return qfalse;
    if(!tr.world || !tr.world->surfaces || !ds || !ds->surface)
        return qfalse;
    if(strcmp(tr.world->baseName,"boss1")!=0 ||
       strcmp(tr.world->name,"maps/boss1.bsp")!=0 ||
       tr.world->numWorldSurfaces!=7274 || tr.world->numsurfaces!=7791)
        return qfalse;
    if((backEnd.viewParms.flags & (VPF_SHADOWMAP|VPF_DEPTHSHADOW))!=
       (VPF_SHADOWMAP|VPF_DEPTHSHADOW))
        return qfalse;
    if(backEnd.viewParms.flags &
       (VPF_DLIGHT_WORLD_OCCLUSION|VPF_FIREVOL_SYNTHETIC_SHADOW))
        return qfalse;

    capture=(const vec3_t *)&backEnd.viewParms.or.origin;
    if(fabsf((*capture)[0]-(-2764.0f))>tolerance ||
       fabsf((*capture)[1]-(-219.0f))>tolerance ||
       fabsf((*capture)[2]-(-24.0f))>tolerance)
        return qfalse;
    entityNum=(ds->sort>>QSORT_REFENTITYNUM_SHIFT)&REFENTITYNUM_MASK;
    if(entityNum!=REFENTITYNUM_WORLD)return qfalse;

    surf=&tr.world->surfaces[7232];
    if(surf->data!=ds->surface || !surf->data || !surf->shader ||
       strcmp(surf->shader->name,"textures/metal_misc/ametal_m03dm")!=0)
        return qfalse;
    ci=&surf->cullinfo;
    if(!(ci->type&CULLINFO_BOX))return qfalse;
    if(fabsf(ci->bounds[0][0]-(-2799.02f))>0.25f ||
       fabsf(ci->bounds[0][1]-(-229.78f))>0.25f ||
       fabsf(ci->bounds[0][2]-(-40.53f))>0.25f ||
       fabsf(ci->bounds[1][0]-(-2774.36f))>0.25f ||
       fabsf(ci->bounds[1][1]-(-210.73f))>0.25f ||
       fabsf(ci->bounds[1][2]-(-16.56f))>0.25f)
        return qfalse;

    if(!loggedOnce || (tr.frameCount!=loggedFrame && (tr.frameCount%120)==0))
    {
        loggedOnce=qtrue;loggedFrame=tr.frameCount;
        ri.Printf(PRINT_ALL,
          "DW_PS_V32_GUARD_APPLIED map=boss1 surface=7232 material=textures/metal_misc/ametal_m03dm capture=(-2764 -219 -24) scope=ONE_ORDINARY_POINT_SHADOW_FACE worldVisible=1 otherLightCasting=1 stage11Unchanged=1\n");
    }
    return qtrue;
}
'''
def apply(root,check=False,proof=None):
    base=Path(root)/"SP/code/rend2"
    prev={f:(base/f).read_text(encoding="utf-8") for f in EXPECTED}
    for f,v in prev.items():
        assert H(v)==EXPECTED[f],("V31 exact-source drift, will not patch",f,H(v))
        assert MARK not in v,("V32 already present",f)
    assert "DWPointV31MaybeDump" in prev["tr_backend.c"]
    assert "DARKWOLF_POINT_SHADOW_GEOMETRY_FIDELITY_V3_41019985033" in prev["tr_backend.c"]
    assert "DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886" in prev["tr_backend.c"]
    out=dict(prev)
    old="extern cvar_t  *r_dwPointV31AutoAudit; // DARKWOLF_POINT_SHADOW_V31_ONESHOT_BSP_AUDIT_41019985033"
    out["tr_local.h"]=one(out["tr_local.h"],old,old+"\nextern cvar_t  *"+CVAR+"; // "+MARK,"extern")
    old="cvar_t  *r_dwPointV31AutoAudit; // DARKWOLF_POINT_SHADOW_V31_ONESHOT_BSP_AUDIT_41019985033"
    out["tr_init.c"]=one(out["tr_init.c"],old,old+"\ncvar_t  *"+CVAR+"; // "+MARK,"definition")
    old="\tri.Cvar_CheckRange( r_dwPointV31AutoAudit, 0, 1, qtrue );"
    out["tr_init.c"]=one(out["tr_init.c"],old,old+
      "\n\t"+CVAR+' = ri.Cvar_Get( "'+CVAR+'", "0", CVAR_LATCH );'+
      "\n\tri.Cvar_CheckRange( "+CVAR+", 0, 1, qtrue );","register")
    backend=out["tr_backend.c"]
    backend=one(backend,"static void DWPointV3InspectSelectedSurface(void)",
       EXCLUDE_FUNCTION+"\nstatic void DWPointV3InspectSelectedSurface(void)","guard definition")
    loop="\tfor (i = 0, drawSurf = drawSurfs ; i < numDrawSurfs ; i++, drawSurf++) {\n"
    backend=one(backend,loop,loop+
      "\t\t/* "+MARK+": skip only one source-local BSP shadow caster. */\n"
      "\t\tif(DWPointV32SkipProvenFixtureCaster(drawSurf))continue;\n",
      "caster guard in shadow draw-loop")
    out["tr_backend.c"]=backend
    assert "DWPointV32SkipProvenFixtureCaster(drawSurf)" in backend
    assert "DARKWOLF_STAGE11_UNIFIED_ASSET_SHADOW_COVERAGE_CLEAN_PRODUCTION_V1" in backend
    assert "DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886" in backend
    if not check:
        for f,v in out.items(): (base/f).write_text(v,encoding="utf-8")
    report={
      "type":"EXPERIMENTAL_SOURCE_LOCAL_FIXTURE_SELF_SHADOW_CASTER_GUARD_V32",
      "base":41019985033,"parentDiagnostic":"V31 #41286948638",
      "marker":MARK,"check_only":check,
      "modified_files":["SP/code/rend2/"+x for x in out],
      "sha256_before":{x:H(v) for x,v in prev.items()},
      "sha256_after":{x:H(v) for x,v in out.items()},
      "guard_default":0,"guard_latched":True,
      "map":"boss1","mainWorldSurfaces":7274,"allBspSurfaces":7791,
      "source_capture":[-2764,-219,-24],"tolerance":0.25,
      "worldSurface":7232,"shader":"textures/metal_misc/ametal_m03dm",
      "bounds":[[-2799.02,-229.78,-40.53],[-2774.36,-210.73,-16.56]],
      "otherPointLightsCasterUnmodified":True,"sunFireTeslaVolumetricUnmodified":True,
      "visibleSceneGeometryUnmodified":True,"otherShadowCasterUnmodified":True,
      "stage11FullCasterReceiverUnmodifiedWhenOff":True,
      "gpuVisualAcceptance":"PENDING; prior V31 single surface exclusion is experimental evidence, not verification of this new binary",
      "generalization":"NEVER globally exclude this material or world surfaces."
    }
    if proof:
        p=Path(proof);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("DW_PS_V32_SOURCE_LOCAL_FIXTURE_GUARD_PATCH_PASS")
    return report

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    ap.add_argument("--check-only",action="store_true")
    ap.add_argument("--proof",type=Path)
    a=ap.parse_args()
    apply(a.root,check=a.check_only,proof=a.proof)
