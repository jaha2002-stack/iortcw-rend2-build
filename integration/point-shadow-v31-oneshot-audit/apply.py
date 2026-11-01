#!/usr/bin/env python3
"""V3.1 TEST ONLY: one-shot source-specific BSP candidate report.

Apply AFTER the guarded V3 apply.py to the reconstructed exact clean source.
No change to production, normal caster eligibility, GLSL, capture geometry,
shadow budget, HDR, sun, fire, local or any shader.
"""
import argparse
import hashlib
import json
from pathlib import Path

MARK="DARKWOLF_POINT_SHADOW_V31_ONESHOT_BSP_AUDIT_41019985033"
CVAR="r_dwPointV31AutoAudit"
FILES=("tr_local.h","tr_init.c","tr_backend.c")

def replace_once(s, old, new, label):
    n=s.count(old)
    assert n==1,(label,n)
    return s.replace(old,new,1)

def digest(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

HELPERS=r'''
/* DARKWOLF_POINT_SHADOW_V31_ONESHOT_BSP_AUDIT_41019985033:
 * Test only. Nothing is filtered/altered; identifies candidate BSP ids and
 * exports factual source-relative metadata. Does not infer per-pixel depth owner.
 * Restricted to exact source selected by V3 and selected BSP ID interval.
 */
#include <stdarg.h>
typedef struct {
    int id, seen, inside, kind, cullType;
    float distance, centerDist, angularProxy, radius;
} dwPointV31Entry_t;

static unsigned char *dwPointV31Submitted=NULL;
static const world_t *dwPointV31World=NULL;
static const msurface_t *dwPointV31WorldSurfs=NULL;
static int dwPointV31NumSurfaces=0;
static char dwPointV31Map[MAX_QPATH]="";
static qboolean dwPointV31Dumped=qfalse;

static qboolean DWPointV31Enabled(void)
{
    return r_dwPointV31AutoAudit && r_dwPointV31AutoAudit->integer==1 &&
           r_dwPointV3Mode && r_dwPointV3Mode->integer==0 &&
           r_dwPointV3TargetTolerance && r_dwPointV3TargetTolerance->value>0.0f;
}

static void DWPointV31EnsureMap(void)
{
    if(!DWPointV31Enabled()||!tr.world||!tr.world->surfaces)return;
    if(dwPointV31World!=tr.world ||
       dwPointV31WorldSurfs!=tr.world->surfaces ||
       dwPointV31NumSurfaces!=tr.world->numsurfaces ||
       strcmp(dwPointV31Map,tr.world->name)!=0)
    {
        free(dwPointV31Submitted);
        dwPointV31Submitted=NULL;
        dwPointV31World=tr.world;
        dwPointV31WorldSurfs=tr.world->surfaces;
        dwPointV31NumSurfaces=tr.world->numsurfaces;
        dwPointV31Dumped=qfalse;
        Q_strncpyz(dwPointV31Map,tr.world->name,sizeof(dwPointV31Map));
        if(dwPointV31NumSurfaces>0 && dwPointV31NumSurfaces<=500000)
            dwPointV31Submitted=(unsigned char*)calloc((size_t)dwPointV31NumSurfaces,1);
        if(!dwPointV31Submitted)
            ri.Printf(PRINT_WARNING,"DW_PS_V31_REPORT_BLOCKED: BSP map allocation/count\n");
    }
}

static void DWPointV31Record(int id)
{
    if(!DWPointV31Enabled())return;
    DWPointV31EnsureMap();
    if(dwPointV31Submitted && id>=0 && id<dwPointV31NumSurfaces)
        dwPointV31Submitted[id]=1;
}

static float DWPointV31BoxDistance(const vec3_t p,const cullinfo_t *ci)
{
    int j;
    float dd=0.0f;
    for(j=0;j<3;j++)
    {
        float d=0.0f;
        if(p[j]<ci->bounds[0][j])d=ci->bounds[0][j]-p[j];
        else if(p[j]>ci->bounds[1][j])d=p[j]-ci->bounds[1][j];
        dd+=d*d;
    }
    return sqrtf(dd);
}

static int DWPointV31ScoreCompare(const void *aa,const void *bb)
{
    const dwPointV31Entry_t *a=(const dwPointV31Entry_t*)aa;
    const dwPointV31Entry_t *b=(const dwPointV31Entry_t*)bb;
    /* Primary: an actually submitted world surface. Secondary: angular size
       and source proximity. This is candidate ordering, NOT depth ownership. */
    if(a->seen!=b->seen)return b->seen-a->seen;
    if(a->inside!=b->inside)return b->inside-a->inside;
    if(a->angularProxy>b->angularProxy)return -1;
    if(a->angularProxy<b->angularProxy)return 1;
    if(a->distance<b->distance)return -1;
    if(a->distance>b->distance)return 1;
    return a->id-b->id;
}

static void DWPointV31Append(char **out,size_t *space,const char *fmt,...)
{
    va_list args;
    int n;
    if(*space<=1)return;
    va_start(args,fmt);
    n=vsnprintf(*out,*space,fmt,args);
    va_end(args);
    if(n<0||((size_t)n)>=*space)
    {
        *out+=*space-1;
        *space=1;
        **out=0;
    }
    else
    {
        *out+=n;
        *space-=(size_t)n;
    }
}

static void DWPointV31JsonName(const char *in,char *out,size_t cap)
{
    size_t i=0;
    if(!cap)return;
    if(!in)in="(none)";
    while(*in && i+1<cap)
    {
        unsigned char c=(unsigned char)(*in++);
        out[i++]=(c>=32 && c<=126 && c!='"' && c!='\\')?(char)c:'_';
    }
    out[i]=0;
}

static void DWPointV31MaybeDump(void)
{
    dwPointV31Entry_t *candidates;
    int count=0, submitted=0, insideCount=0, near16=0,near32=0,near64=0;
    int i, first,last, maxDump=160, shown=0;
    char *output,*pos,*pathPart,*safe,reportName[96];
    size_t cap=2*1024*1024,remain;
    const vec3_t *lightOrigin;
    if(!DWPointV31Enabled()||!DWPointV3CaptureSelected())return;
    /* Last cubemap face (+Z). Disallow depth prepass and repeated reports. */
    if(backEnd.depthFill||dwPointV31Dumped ||
       fabsf(backEnd.viewParms.or.axis[0][0])>0.01f||
       fabsf(backEnd.viewParms.or.axis[0][1])>0.01f||
       backEnd.viewParms.or.axis[0][2]<0.99f)return;
    DWPointV31EnsureMap();
    if(!dwPointV31Submitted)return;
    first=r_dwPointV3SurfaceFirst->integer;
    last=r_dwPointV3SurfaceLast->integer;
    if(first<0)first=0;
    if(last>=tr.world->numsurfaces)last=tr.world->numsurfaces-1;
    if(last<first)return;
    candidates=(dwPointV31Entry_t*)calloc((size_t)(last-first+1),sizeof(*candidates));
    output=(char*)malloc(cap);
    if(!candidates||!output)
    {
        ri.Printf(PRINT_WARNING,"DW_PS_V31_REPORT_BLOCKED: candidate/output allocation failed\n");
        free(candidates);free(output);return;
    }
    lightOrigin=(const vec3_t*)&backEnd.viewParms.or.origin;
    for(i=first;i<=last;i++)
    {
        const msurface_t *s=&tr.world->surfaces[i];
        const cullinfo_t *ci=&s->cullinfo;
        float dx,dy,dz,dist,halfdiag,centerDist,proxy;
        dwPointV31Entry_t *c=&candidates[count];
        if(!s->data || !(ci->type&CULLINFO_BOX))continue;
        dx=0.5f*(ci->bounds[1][0]+ci->bounds[0][0])-(*lightOrigin)[0];
        dy=0.5f*(ci->bounds[1][1]+ci->bounds[0][1])-(*lightOrigin)[1];
        dz=0.5f*(ci->bounds[1][2]+ci->bounds[0][2])-(*lightOrigin)[2];
        centerDist=sqrtf(dx*dx+dy*dy+dz*dz);
        dx=ci->bounds[1][0]-ci->bounds[0][0];
        dy=ci->bounds[1][1]-ci->bounds[0][1];
        dz=ci->bounds[1][2]-ci->bounds[0][2];
        halfdiag=0.5f*sqrtf(dx*dx+dy*dy+dz*dz);
        dist=DWPointV31BoxDistance(*lightOrigin,ci);
        proxy=halfdiag/(centerDist>0.1f?centerDist:0.1f);
        if(proxy>1000.0f)proxy=1000.0f;
        c->id=i;c->distance=dist;c->radius=halfdiag;
        c->centerDist=centerDist;c->angularProxy=proxy;
        c->seen=dwPointV31Submitted[i]?1:0;
        c->inside=(dist<0.001f)?1:0;
        c->kind=(int)*s->data;c->cullType=ci->type;
        count++;
        submitted+=c->seen;
        insideCount+=c->inside;
        if(dist<=16.0f)near16++;
        if(dist<=32.0f)near32++;
        if(dist<=64.0f)near64++;
    }
    qsort(candidates,(size_t)count,sizeof(*candidates),DWPointV31ScoreCompare);
    pos=output;remain=cap;
    DWPointV31Append(&pos,&remain,
      "{\n \"format\":\"DW_POINT_SHADOW_V31_BSP_AUTO_AUDIT\",\n"
      " \"map\":\"%s\",\n \"status\":\"CANDIDATE_INVENTORY_NOT_PIXEL_CAUSAL_PROOF\",\n"
      " \"acceptedProductionUnchanged\":true,\n"
      " \"stage11CasterCoveragePreserved\":true,\n"
      " \"shadowDepthWinnerIdentified\":false,\n \"physicalFixtureIdVerified\":false,\n"
      " \"captureOrigin\":[%.3f,%.3f,%.3f],\n"
      " \"range\":{\"first\":%d,\"last\":%d},\n"
      " \"surfaceCounts\":{\"rendererTotal\":%d,\"mainWorld\":%d,"
      "\"rangeAabb\":%d,\"seenInSelectedShadowDrawlist\":%d,"
      "\"captureInsideAabb\":%d,\"boxDistanceLE16\":%d,\"LE32\":%d,\"LE64\":%d},\n"
      " \"ranking\":\"draw-list candidate > origin-inside-box > AABB apparent angular size; NOT a depth-winner ranking\",\n"
      " \"candidateShortlist\":[\n",
      tr.world->baseName,(*lightOrigin)[0],(*lightOrigin)[1],(*lightOrigin)[2],
      first,last,tr.world->numsurfaces,tr.world->numWorldSurfaces,
      count,submitted,insideCount,near16,near32,near64);
    for(i=0;i<count&&shown<maxDump;i++)
    {
        dwPointV31Entry_t *c=&candidates[i];
        const msurface_t *s=&tr.world->surfaces[c->id];
        char shader[128];
        if(!c->seen)continue;
        DWPointV31JsonName(s->shader?s->shader->name:NULL,shader,sizeof(shader));
        DWPointV31Append(&pos,&remain,
          "%s  {\"id\":%d,\"shader\":\"%s\",\"surfType\":%d,"
          "\"cullType\":%d,\"submitted\":true,\"captureInsideAabb\":%s,"
          "\"boxDistance\":%.3f,\"centerDistance\":%.3f,"
          "\"halfDiagonal\":%.3f,\"angularProxy\":%.4f,"
          "\"boundsMin\":[%.2f,%.2f,%.2f],\"boundsMax\":[%.2f,%.2f,%.2f]}\n",
          shown?",\n":"",c->id,shader,c->kind,c->cullType,
          c->inside?"true":"false",c->distance,c->centerDist,
          c->radius,c->angularProxy,
          s->cullinfo.bounds[0][0],s->cullinfo.bounds[0][1],s->cullinfo.bounds[0][2],
          s->cullinfo.bounds[1][0],s->cullinfo.bounds[1][1],s->cullinfo.bounds[1][2]);
        shown++;
    }
    DWPointV31Append(&pos,&remain,
       " ],\n \"shortlistCount\":%d,\n"
       " \"proofLimit\":\"A shadow draw-list candidate has NOT been proven to win the GPU depth test. Verify pixel owner before any production fix.\"\n}\n",
       shown);
    /* One small file written by the engine into its active writable game fs.
       No console condump, repeated manual range changes or debug PK3 required. */
    pathPart=tr.world->baseName;
    snprintf(reportName,sizeof(reportName),"dw_ps_v31_%s_auto.json",pathPart);
    for(safe=reportName;*safe;++safe)
        if(*safe=='/'||*safe=='\\'||*safe==':'||*safe==' ') *safe='_';
    ri.FS_WriteFile(reportName,output,(int)strlen(output));
    ri.Printf(PRINT_ALL,
      "DW_PS_V31_AUTOREPORT_OK path=%s map=%s capture=(%.1f %.1f %.1f) range=%d..%d submittedCandidates=%d insideAABB=%d shortlist=%d (GPU depth ownership NOT YET proved)\n",
      reportName,tr.world->baseName,
      (*lightOrigin)[0],(*lightOrigin)[1],(*lightOrigin)[2],
      first,last,submitted,insideCount,shown);
    dwPointV31Dumped=qtrue;
    free(output);free(candidates);
}
'''

def apply(root,check=False,proof=None):
    base=Path(root)/"SP/code/rend2"
    old={n:(base/n).read_text(encoding="utf-8") for n in FILES}
    assert all(MARK not in s for s in old.values()),"V31 duplicate"
    assert "DARKWOLF_POINT_SHADOW_GEOMETRY_FIDELITY_V3_41019985033" in old["tr_backend.c"]
    assert "DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886" in old["tr_backend.c"]
    assert "DWPointV3CaptureSelected" in old["tr_backend.c"]
    new=dict(old)
    ref="extern cvar_t  *r_dwPointV3InspectSurface; // DARKWOLF_POINT_SHADOW_GEOMETRY_FIDELITY_V3_41019985033"
    new["tr_local.h"]=replace_once(new["tr_local.h"],ref,ref+"\nextern cvar_t  *"+CVAR+"; // "+MARK,"extern cvar")
    define="cvar_t  *r_dwPointV3InspectSurface; // DARKWOLF_POINT_SHADOW_GEOMETRY_FIDELITY_V3_41019985033"
    new["tr_init.c"]=replace_once(new["tr_init.c"],define,
       define+"\ncvar_t  *"+CVAR+"; // "+MARK,"define cvar")
    anchor="\tri.Cvar_CheckRange( r_dwPointV3InspectSurface, -1, 500000, qtrue );"
    new["tr_init.c"]=replace_once(new["tr_init.c"],anchor,
       anchor+"\n\t"+CVAR+' = ri.Cvar_Get( "'+CVAR+'", "0", 0 );' +
       "\n\tri.Cvar_CheckRange( "+CVAR+", 0, 1, qtrue );","cvar reg")
    backend=new["tr_backend.c"]
    backend=replace_once(backend,
       "static void DWPointV3InspectSelectedSurface(void)",
       HELPERS+"\nstatic void DWPointV3InspectSelectedSurface(void)","helpers before inspect")
    oldcondition=("            (r_dwPointV3Mode->integer != 0 ||\n"
                  "             r_dwPointV3InspectSurface->integer >= 0) &&")
    newcondition=("            (r_dwPointV3Mode->integer != 0 ||\n"
                  "             r_dwPointV3InspectSurface->integer >= 0 ||\n"
                  "             DWPointV31Enabled()) &&")
    backend=replace_once(backend,oldcondition,newcondition,"enrich shadow source gate")
    oldsource="if (dwEntityNum == REFENTITYNUM_WORLD && dwMode != 0)"
    backend=replace_once(backend,oldsource,
       "if (dwEntityNum == REFENTITYNUM_WORLD && (dwMode != 0 || DWPointV31Enabled()))",
       "lookup world when logging")
    insert_before="            if (dwId >= 0 && dwId == r_dwPointV3InspectSurface->integer &&"
    backend=replace_once(backend,insert_before,
       "            if (DWPointV31Enabled() && dwId >= 0 && !backEnd.depthFill)\n"
       "                DWPointV31Record(dwId);\n"+insert_before,"submission mark")
    anchor_end=("\t// go back to the world modelview matrix\n"
                "\tbackEnd.currentEntity = &tr.worldEntity;")
    backend=replace_once(backend,anchor_end,
       "\t// "+MARK+": after the final (+Z) capture face, dump one JSON report.\n"
       "\tif (DWPointV31Enabled()) DWPointV31MaybeDump();\n\n"+anchor_end,
       "shadow view end")
    assert "DWPointV31MaybeDump()" in backend
    new["tr_backend.c"]=backend
    if not check:
        for name in FILES:
            (base/name).write_text(new[name],encoding="utf-8")
    obj={
      "type":"V3.1_TEST_ONLY_AUTOMATED_SOURCE_GEOMETRY_REPORT",
      "accepted_baseline_run":41019985033,
      "source_parent":"V3 exact after V1+V2 on #41019985033",
      "marker":MARK,"check_only":check,
      "modified_files":["SP/code/rend2/"+n for n in FILES],
      "sha256_before":{k:digest(v) for k,v in old.items()},
      "sha256_after":{k:digest(v) for k,v in new.items()},
      "cvar":{CVAR:"0=no effect;1=one-shot JSON report only; no caster filtering"},
      "report":"dw_ps_v31_<map>_auto.json (writable game filesystem)",
      "diagnostic_matches_only_selected_capture":True,
      "no_change_to_GL_shaders":True,
      "no_change_to_capture_origin_depth_or_casting":True,
      "other_effects_and_production_untouched":True,
      "physical_light_id_verified":False,
      "gpu_depth_winner_verified":False,
      "gpu_test":"PENDING"
    }
    if proof:
        p=Path(proof);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
    print("DW_PS_V31_ONESHOT_SOURCE_PASS")
    return obj

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    ap.add_argument("--check-only",action="store_true")
    ap.add_argument("--proof",type=Path)
    a=ap.parse_args()
    apply(a.root,check=a.check_only,proof=a.proof)
