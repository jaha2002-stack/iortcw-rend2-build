#!/usr/bin/env python3
"""Second AND LAST user-facing experimental point-shadow GPU PROOF release.
Build against V4 source reconstructed from accepted immutable #41019985033.
No global shader/material/texture/surface suppression, all new defaults OFF.
"""
import argparse,hashlib,json
from pathlib import Path
MARK="DARKWOLF_POINT_V5_CROSSMAP_SOURCE_LOCAL_PROOF_41019985033"
EXPECTED={
  "tr_local.h":"8a858f17ea1feb9b8a1a1f2cf7f210f234e1ab44d6e1f277e7d3587218ce3a02",
  "tr_init.c":"c14ebc1e7738e775c747d079c5b8fe7aa441db89c9f092260a2bb58eaddb5680",
  "tr_backend.c":"cfa50647c160f83e453a1ce123dc56655d259d2b9b2c1364e79e1f2cb671bae3",
}
NAMES=("r_dwPointV5ProofMode","r_dwPointV5ProofAudit")

def sha(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def one(s,a,b,tag):
    n=s.count(a)
    assert n==1,(tag,n)
    return s.replace(a,b,1)

HELPERS=r'''
/* DARKWOLF_POINT_V5_CROSSMAP_SOURCE_LOCAL_PROOF_41019985033
 * SECOND / FINAL GPU PROOF ONLY, never implicit production policy.
 * A strict source-local conservative caster hypothesis is evaluated against
 * independent attribution controls in each map. No map, ID or shader name is
 * hard-coded as a removal rule. Geometry is drawn in normal scenes and for
 * every other shadow source. Fail open whenever association is uncertain.
 *
 * Classification bitmask (per source and BSP map):
 *   1 = large source-attached opaque housing next to emitter-like BSP
 *   2 = small thin horizontal dish below a confirmed radial emitter cage
 *   4 = radial vertical panels of a confirmed source-centered symmetric cage
 *   8 = paired tall ladder-like rails (ATTRIBUTION CONTROL ONLY)
 *
 * A spatial test alone is not a true per-pixel GPU depth-owner measurement.
 * Therefore only mode1 is a candidate repair, and even it requires per-map
 * GPU acceptance. Modes2/3 are deliberately control interventions.
 */
#define DW5_LINKED 1
#define DW5_DISH 2
#define DW5_CAGE 4
#define DW5_RAIL 8
static unsigned char *dw5Flags=NULL;
static const world_t *dw5World=NULL;
static const msurface_t *dw5Surfs=NULL;
static char dw5Map[MAX_QPATH]="";
static int dw5Count=0,dw5BuiltSource=-1,dw5ReportWritten=0;
static vec3_t dw5Capture={0,0,0};
static int dw5MatchedSource=0,dw5SourceStats[4]={0,0,0,0};
static int dw5SkipCalls=0,dw5ReportedSkip=0;
static int dw5CageValid=0,dw5LadderValid=0;

static int DW5PointCaptureSelected(void)
{
    vec3_t v;
    if(!r_dwPointV5ProofMode || r_dwPointV5ProofMode->integer==0)
        return 0;
    if(!r_dwPointV5ProofAudit || r_dwPointV5ProofAudit->integer!=1)
        return 0;
    if(!DWV4OrdinaryPoint() || dwV4CurrentSource<0)
        return 0;
    if(!r_dwPointV4Mode || r_dwPointV4Mode->integer!=0)
        return 0;
    if(r_dwPointV32FixtureGuard && r_dwPointV32FixtureGuard->integer!=0)
        return 0;
    if(strcmp(tr.world->baseName,r_dwPointV4FocusMap->string)!=0)
        return 0;
    v[0]=r_dwPointV4FocusX->value;
    v[1]=r_dwPointV4FocusY->value;
    v[2]=r_dwPointV4FocusZ->value;
    return DWV4Dist3(dwV4Sources[dwV4CurrentSource].capture,v)<=0.30f;
}
static int DW5PlanarRadialSide(const cullinfo_t *ci,const vec3_t src)
{
    float xl=ci->bounds[0][0]-src[0],xh=ci->bounds[1][0]-src[0];
    float yl=ci->bounds[0][1]-src[1],yh=ci->bounds[1][1]-src[1];
    float zl=ci->bounds[0][2]-src[2],zh=ci->bounds[1][2]-src[2];
    if(zl>-24 || zh<32 || zh-zl<70 || zh-zl>180)return -1;
    if(xl>=-2 && xl<=2 && xh>=8 && xh<=32 &&
       fabsf(yl)<=2 && fabsf(yh)<=2)return 0;
    if(xh>=-2 && xh<=2 && xl<=-8 && xl>=-32 &&
       fabsf(yl)<=2 && fabsf(yh)<=2)return 1;
    if(yl>=-2 && yl<=2 && yh>=8 && yh<=32 &&
       fabsf(xl)<=2 && fabsf(xh)<=2)return 2;
    if(yh>=-2 && yh<=2 && yl<=-8 && yl>=-32 &&
       fabsf(xl)<=2 && fabsf(xh)<=2)return 3;
    return -1;
}
static void DW5ResetMap(void)
{
    if(!tr.world)return;
    if(dw5World!=tr.world || dw5Surfs!=tr.world->surfaces ||
       dw5Count!=tr.world->numsurfaces ||
       strcmp(dw5Map,tr.world->name)!=0)
    {
        free(dw5Flags);dw5Flags=NULL;
        dw5World=tr.world;dw5Surfs=tr.world->surfaces;
        dw5Count=tr.world->numsurfaces;
        Q_strncpyz(dw5Map,tr.world->name,sizeof(dw5Map));
        dw5BuiltSource=-1;dw5ReportWritten=0;
        dw5SkipCalls=0;dw5ReportedSkip=0;
        dw5CageValid=0;dw5LadderValid=0;
        memset(dw5SourceStats,0,sizeof(dw5SourceStats));
    }
}
static void DW5BuildClassifiedSource(void)
{
    int i,j,counts[4]={0,0,0,0},sides=0,nearRails=0;
    char radialName[112]="";
    const char *railName=NULL;
    dwV4Source_t *src;
    const vec3_t *org;
    int n;
    DW5ResetMap();
    if(!DW5PointCaptureSelected())return;
    n=tr.world->numWorldSurfaces;
    if(n<1 || n>200000 || n>tr.world->numsurfaces)return;
    src=&dwV4Sources[dwV4CurrentSource];
    org=(const vec3_t*)&src->capture;
    if(dw5Flags && dw5BuiltSource==dwV4CurrentSource &&
       DWV4Dist3(dw5Capture,*org)<0.2f)return;
    free(dw5Flags);dw5Flags=(unsigned char*)calloc((size_t)n,1);
    if(!dw5Flags){dw5BuiltSource=-1;return;}
    dw5BuiltSource=dwV4CurrentSource;
    VectorCopy(*org,dw5Capture);
    dw5CageValid=0;dw5LadderValid=0;
    memset(dw5SourceStats,0,sizeof(dw5SourceStats));

    /* Known Boss1-like geometry: dominant physical housing near its own
       emissive BSP part. Do not use any literal material as an exclusion. */
    if(src->hasEmitter)
    {
        int best=-1;
        float bestScore=-1.0f;
        for(i=0;i<src->candidateCount;i++)
        {
            dwV4Candidate_t *c=&src->candidates[i];
            float apparent=c->halfDiag/(c->centerDist>8?c->centerDist:8);
            if(!c->linked || c->seenDraws==0 ||
               c->nearDist>16 || c->halfDiag<12 ||
               apparent<0.70f)continue;
            if(c->score>bestScore){bestScore=c->score;best=c->id;}
        }
        if(best>=0 && best<n)dw5Flags[best]|=DW5_LINKED;
    }

    /* Choose radial enclosure material only by the fixture's geometry,
       never by a hard-coded shader path or global surface class. */
    for(i=0;i<n;i++)
    {
        const msurface_t *m=&tr.world->surfaces[i];
        if(!m->data||!m->shader||!(m->cullinfo.type&CULLINFO_BOX))continue;
        if(DWV4DisallowCandidate(m->shader->name))continue;
        if(DW5PlanarRadialSide(&m->cullinfo,*org)<0)continue;
        if(DWV4BoxPointDist(*org,&m->cullinfo)>2.0f)continue;
        Q_strncpyz(radialName,m->shader->name,sizeof(radialName));
        break;
    }
    if(radialName[0])
    {
        for(i=0;i<n;i++)
        {
            const msurface_t *m=&tr.world->surfaces[i];
            int side;
            if(!m->data||!m->shader||!(m->cullinfo.type&CULLINFO_BOX)||
               strcmp(m->shader->name,radialName)!=0)continue;
            side=DW5PlanarRadialSide(&m->cullinfo,*org);
            if(side<0 || DWV4BoxPointDist(*org,&m->cullinfo)>2.0f)continue;
            dw5Flags[i]|=DW5_CAGE;
            counts[side]++;
            nearRails++;
        }
        for(j=0;j<4;j++)if(counts[j]>0)sides++;
        if(sides==4 && nearRails>=8 && nearRails<=80)
            dw5CageValid=1;
        else
            for(i=0;i<n;i++)dw5Flags[i]&=~DW5_CAGE;
    }

    /* Plausible small horizontal fixture basin below flame. Only evaluated
       when a source-centered symmetric enclosure is independently detected.
       Avoid nearby world floors by strict dimensions and proximity gates. */
    if(dw5CageValid)
    {
        for(i=0;i<n;i++)
        {
            const msurface_t *m=&tr.world->surfaces[i];
            const cullinfo_t *c=&m->cullinfo;
            float dx,dy,dz,xc,yc,zc;
            if(!m->data||!m->shader||!(c->type&CULLINFO_BOX)||
               DWV4DisallowCandidate(m->shader->name))continue;
            dx=c->bounds[1][0]-c->bounds[0][0];
            dy=c->bounds[1][1]-c->bounds[0][1];
            dz=c->bounds[1][2]-c->bounds[0][2];
            xc=0.5f*(c->bounds[0][0]+c->bounds[1][0]);
            yc=0.5f*(c->bounds[0][1]+c->bounds[1][1]);
            zc=0.5f*(c->bounds[0][2]+c->bounds[1][2]);
            if(dx<8 || dy<8 || dx>96 || dy>96 || dz>5.0f)continue;
            if(fabsf(xc-(*org)[0])>40 || fabsf(yc-(*org)[1])>40)continue;
            if(zc>(*org)[2]-8 || zc<(*org)[2]-96)continue;
            dw5Flags[i]|=DW5_DISH;
        }
    }

    /* Factory-like paired physical ladder rails are a diagnostic control,
       NOT a proposed universal exclusion. Detect by geometry only. */
    if(src->candidateCount>=2 && !src->candidates[0].linked &&
       !src->candidates[1].linked)
    {
        const dwV4Candidate_t *a=&src->candidates[0],*b=&src->candidates[1];
        float ax=a->upper[0]-a->lower[0], ay=a->upper[1]-a->lower[1];
        float bx=b->upper[0]-b->lower[0], by=b->upper[1]-b->lower[1];
        float ac=0.5f*(a->lower[0]+a->upper[0]),bc=0.5f*(b->lower[0]+b->upper[0]);
        float ayc=0.5f*(a->lower[1]+a->upper[1]);
        float byc=0.5f*(b->lower[1]+b->upper[1]);
        if(strcmp(a->material,b->material)==0 && a->seenDraws>0 &&
           b->seenDraws>0 && ax<=8 && bx<=8 && ay<=3 && by<=3 &&
           a->upper[2]-a->lower[2]>=60 &&
           b->upper[2]-b->lower[2]>=60 &&
           fabsf(ac-bc)>=20 && fabsf(ac-bc)<=72 &&
           fabsf(ayc-byc)<=3 && a->nearDist<=32 && b->nearDist<=64)
        {
            railName=a->material;dw5LadderValid=1;
            for(i=0;i<n;i++)
            {
                const msurface_t *m=&tr.world->surfaces[i];
                const cullinfo_t *c=&m->cullinfo;
                float dx,dy,dz,cx,cy;
                if(!m->data||!m->shader||!(c->type&CULLINFO_BOX)||
                   strcmp(m->shader->name,railName)!=0)continue;
                dx=c->bounds[1][0]-c->bounds[0][0];
                dy=c->bounds[1][1]-c->bounds[0][1];
                dz=c->bounds[1][2]-c->bounds[0][2];
                cx=0.5f*(c->bounds[0][0]+c->bounds[1][0]);
                cy=0.5f*(c->bounds[0][1]+c->bounds[1][1]);
                if(dx>8 || dy>3 || dz<60 || dz>220)continue;
                if(fabsf(cy-ayc)>6 || fabsf(cx-ac)>12 && fabsf(cx-bc)>12)
                    continue;
                dw5Flags[i]|=DW5_RAIL;
            }
        }
    }
    for(i=0;i<n;i++)
    {
        if(dw5Flags[i]&DW5_LINKED)dw5SourceStats[0]++;
        if(dw5Flags[i]&DW5_DISH)dw5SourceStats[1]++;
        if(dw5Flags[i]&DW5_CAGE)dw5SourceStats[2]++;
        if(dw5Flags[i]&DW5_RAIL)dw5SourceStats[3]++;
    }
    ri.Printf(PRINT_ALL,
       "DW_PS_V5_CLASSIFIED map=%s capture=(%.2f %.2f %.2f) linkedHousing=%d dish=%d radialCage=%d pairedRails=%d cageSymmetryValid=%d ladderControlValid=%d (heuristic, no GPU depth-owner proof)\n",
       tr.world->baseName,(*org)[0],(*org)[1],(*org)[2],
       dw5SourceStats[0],dw5SourceStats[1],dw5SourceStats[2],
       dw5SourceStats[3],dw5CageValid,dw5LadderValid);
}
static int DW5ActiveMask(void)
{
    int mode=r_dwPointV5ProofMode->integer;
    if(mode==1)
    {
        if(dw5SourceStats[0]>0)return DW5_LINKED;
        if(dw5CageValid && dw5SourceStats[1]>0)return DW5_DISH;
        return 0;
    }
    if(mode==2)return DW5_CAGE|DW5_RAIL;
    if(mode==3)return DW5_LINKED|DW5_DISH|DW5_CAGE|DW5_RAIL;
    return 0;
}
static qboolean DW5ProofMaybeSkip(const drawSurf_t *ds)
{
    int id,mask,entityNum;
    if(!DW5PointCaptureSelected() || !ds || !ds->surface)return qfalse;
    DW5BuildClassifiedSource();
    if(!dw5Flags)return qfalse;
    mask=DW5ActiveMask();
    if(mask==0)return qfalse;
    entityNum=(ds->sort>>QSORT_REFENTITYNUM_SHIFT)&REFENTITYNUM_MASK;
    if(entityNum!=REFENTITYNUM_WORLD)return qfalse;
    id=DWPointV3SurfaceId(ds->surface);
    if(id<0 || id>=tr.world->numWorldSurfaces)return qfalse;
    if(!(dw5Flags[id]&mask))return qfalse;
    dw5SkipCalls++;
    if(!dw5ReportedSkip)
    {
        dw5ReportedSkip=1;
        ri.Printf(PRINT_ALL,
          "DW_PS_V5_SOURCE_LOCAL_SKIP map=%s mode=%d surface=%d material=%s capture=(%.1f %.1f %.1f) isolatedOtherLights=1 otherCasterPathsUnaffected=1\n",
          tr.world->baseName,r_dwPointV5ProofMode->integer,id,
          tr.world->surfaces[id].shader?tr.world->surfaces[id].shader->name:"(none)",
          dw5Capture[0],dw5Capture[1],dw5Capture[2]);
    }
    return qtrue;
}
static void DW5WriteAtEnd(void)
{
    char *buf,*cur,path[128];
    size_t left=640*1024;
    int i,n,emitted=0,mode;
    if(!DW5PointCaptureSelected()||dw5ReportWritten||!dw5Flags)return;
    if(fabsf(backEnd.viewParms.or.axis[0][0])>0.01f ||
       fabsf(backEnd.viewParms.or.axis[0][1])>0.01f ||
       backEnd.viewParms.or.axis[0][2]<0.99f)return;
    mode=r_dwPointV5ProofMode->integer;
    buf=(char*)malloc(left);
    if(!buf){ri.Printf(PRINT_WARNING,"DW_PS_V5_AUDIT_ALLOC_FAIL\n");return;}
    cur=buf;
    DWV4Append(&cur,&left,
        "{\"format\":\"DW_POINT_V5_PROOF_SOURCE_LOCAL_GROUPS\","
        "\"map\":\"%s\",\"proofMode\":%d,\"source\":[%.3f,%.3f,%.3f],"
        "\"groupCounts\":{\"linkedHousing\":%d,\"dish\":%d,"
        "\"radialCage\":%d,\"pairedRails\":%d},"
        "\"symmetricCage\":%s,\"ladderControl\":%s,"
        "\"casterDrawCallsSkipped\":%d,"
        "\"notVerifiedGPUShadowOwner\":true,"
        "\"doesNotModifyOtherLightShadowMaps\":true,"
        "\"mode1IsOnlyCorrectionCandidate\":true,"
        "\"mode2And3AreAttributionControls\":true,\"surfaces\":[",
        tr.world->baseName,mode,dw5Capture[0],dw5Capture[1],dw5Capture[2],
        dw5SourceStats[0],dw5SourceStats[1],dw5SourceStats[2],dw5SourceStats[3],
        dw5CageValid?"true":"false",dw5LadderValid?"true":"false",
        dw5SkipCalls);
    n=tr.world->numWorldSurfaces;
    for(i=0;i<n;i++)
    {
        const msurface_t *m=&tr.world->surfaces[i];
        char safe[140];
        if(!dw5Flags[i] || !m->shader)continue;
        if(emitted>=320)break;
        DWV4SafeString(m->shader->name,safe,sizeof(safe));
        DWV4Append(&cur,&left,
            "%s{\"id\":%d,\"bits\":%d,\"material\":\"%s\","
            "\"min\":[%.2f,%.2f,%.2f],\"max\":[%.2f,%.2f,%.2f]}",
            emitted?",":"",i,(int)dw5Flags[i],safe,
            m->cullinfo.bounds[0][0],m->cullinfo.bounds[0][1],m->cullinfo.bounds[0][2],
            m->cullinfo.bounds[1][0],m->cullinfo.bounds[1][1],m->cullinfo.bounds[1][2]);
        emitted++;
    }
    DWV4Append(&cur,&left, "],\"reportedSurfaces\":%d,"
       "\"limitations\":\"Geometric grouping and stable A/B controls only; physical legitimacy needs scene inspection; no global surface/material exclusion.\"}\n",emitted);
    snprintf(path,sizeof(path),"dw_ps_v5_%s_mode%d.json",tr.world->baseName,mode);
    ri.FS_WriteFile(path,buf,(int)strlen(buf));
    free(buf);dw5ReportWritten=1;
    ri.Printf(PRINT_ALL,
      "DW_PS_V5_PROOF_REPORT_OK file=%s skipped=%d candidateSurfaces=%d cage=%d ladder=%d\n",
      path,dw5SkipCalls,emitted,dw5CageValid,dw5LadderValid);
}
'''
def apply(root,check=False,proof=None):
    base=Path(root)/"SP/code/rend2"
    old={name:(base/name).read_text(encoding="utf-8") for name in EXPECTED}
    for n,v in old.items():
        assert sha(v)==EXPECTED[n],("V4 source mismatch",n,sha(v))
        assert MARK not in v,(n,"V5 already installed")
    assert "DARKWOLF_POINT_V4_AUTOMATIC_FIXTURE_ATTRIBUTION_DIAGNOSTIC_41019985033" in old["tr_backend.c"]
    assert "DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886" in old["tr_backend.c"]
    new=dict(old)
    target='extern cvar_t  *r_dwPointV4FocusLinked; // DARKWOLF_POINT_V4_AUTOMATIC_FIXTURE_ATTRIBUTION_DIAGNOSTIC_41019985033'
    new["tr_local.h"]=one(new["tr_local.h"],target,target+
      "\n"+''.join('extern cvar_t  *'+x+'; // '+MARK+'\n' for x in NAMES),"extern")
    target='cvar_t  *r_dwPointV4FocusLinked; // DARKWOLF_POINT_V4_AUTOMATIC_FIXTURE_ATTRIBUTION_DIAGNOSTIC_41019985033'
    new["tr_init.c"]=one(new["tr_init.c"],target,target+
      "\n"+''.join('cvar_t  *'+x+'; // '+MARK+'\n' for x in NAMES),"def")
    target='\tri.Cvar_CheckRange( r_dwPointV4FocusLinked, 0, 1, qtrue );'
    regs=(
        '\n\t// '+MARK+': second/final TEST only; both default off.\n'
        '\tr_dwPointV5ProofMode = ri.Cvar_Get( "r_dwPointV5ProofMode", "0", CVAR_LATCH );\n'
        '\tri.Cvar_CheckRange( r_dwPointV5ProofMode, 0, 3, qtrue );\n'
        '\tr_dwPointV5ProofAudit = ri.Cvar_Get( "r_dwPointV5ProofAudit", "0", 0 );\n'
        '\tri.Cvar_CheckRange( r_dwPointV5ProofAudit, 0, 1, qtrue );\n')
    new["tr_init.c"]=one(new["tr_init.c"],target,target+regs,"register")
    backend=new["tr_backend.c"]
    backend=one(backend,'static qboolean DWPointV32SkipProvenFixtureCaster(const drawSurf_t *ds)',
        HELPERS+'\nstatic qboolean DWPointV32SkipProvenFixtureCaster(const drawSurf_t *ds)',"helpers")
    backend=one(backend,
        '\t\tif(DWV4InspectAndMaybeSkip(drawSurf))continue;',
        '\t\tif(DWV4InspectAndMaybeSkip(drawSurf))continue;\n'
        '\t\tif(DW5ProofMaybeSkip(drawSurf))continue; // '+MARK,"loop")
    backend=one(backend,
        '\tif(DWV4Enabled())DWV4WriteDiagnostics();',
        '\tif(DWV4Enabled())DWV4WriteDiagnostics();\n'
        '\tif(r_dwPointV5ProofAudit && r_dwPointV5ProofAudit->integer==1)DW5WriteAtEnd();',"end")
    new["tr_backend.c"]=backend
    assert 'DARKWOLF_STAGE11_UNIFIED_ASSET_SHADOW_COVERAGE_CLEAN_PRODUCTION_V1' in backend
    if not check:
        for n,v in new.items():(base/n).write_text(v,encoding="utf-8")
    obj={
        "type":"DARKWOLF_V5_SECOND_AND_LAST_CROSSMAP_SOURCE_LOCAL_PROOF",
        "accepted_base_run":41019985033,
        "source_parent":"V4 #41292154221",
        "marker":MARK,"check_only":check,
        "sha256_before":{n:sha(s) for n,s in old.items()},
        "sha256_after":{n:sha(s) for n,s in new.items()},
        "modified_files":["SP/code/rend2/"+n for n in EXPECTED],
        "safe_default_mode":0,"safe_default_audit":0,
        "no_global_material_suppression":True,
        "no_hardcoded_bsp_ids_or_material_names":True,
        "strict_one_source_current_map_only":True,
        "fire_tesla_sun_and_other_light_casters_preserved":True,
        "stage11_full_casters_and_receivers_preserved_at_defaults":True,
        "first_proof_mode_hypothesis_only_not_accepted":True,
        "cage_group_requires_four_symmetric_sides_and_eight_faces":True,
        "ladder_rail_group_is_control_only_never_production_fix":True,
        "gpu_visual_acceptance":"PENDING; requires Boss1, Factory, Crypt1, Crypt2 stable controls; no third diagnostic attempt"
    }
    if proof:
        p=Path(proof);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
    print("DW_PS_V5_SECOND_PROOF_SOURCE_PASS")
    return obj

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    ap.add_argument("--check-only",action="store_true")
    ap.add_argument("--proof",type=Path)
    a=ap.parse_args()
    apply(a.root,check=a.check_only,proof=a.proof)
