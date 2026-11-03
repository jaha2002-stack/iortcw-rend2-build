#!/usr/bin/env python3
"""Run CPU invariants on actual IFLC shadow selection/grouping functions.

These are source-extracted CPU tests, not cubemap/GPU tests. Capture geometry and
PCF are deliberately outside this test's mocked execution scope.
"""
import argparse
import pathlib
import subprocess
import tempfile

from run_backend_tests import extract_function


FUNCTIONS = (
    "R_IFLC_ShadowSelectionColor",
    "R_IFLC_ShadowSelectionRadius",
    "R_DlightShadowSelectionScore",
    "R_DarkWolfShadowSourceIsPersistent",
    "R_DarkWolfStaticPromoteShadowGroupEligible",
    "R_DarkWolfStaticPromoteShadowCompanionEquivalent",
)

SUPPORT = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
typedef float vec3_t[3];
typedef int qboolean;
#define qtrue 1
#define qfalse 0
#define VectorCopy(a,b) do{(b)[0]=(a)[0];(b)[1]=(a)[1];(b)[2]=(a)[2];}while(0)
#define VectorScale(a,s,b) do{(b)[0]=(a)[0]*(s);(b)[1]=(a)[1]*(s);(b)[2]=(a)[2]*(s);}while(0)
#define VectorSubtract(a,b,c) do{(c)[0]=(a)[0]-(b)[0];(c)[1]=(a)[1]-(b)[1];(c)[2]=(a)[2]-(b)[2];}while(0)
#define DotProduct(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1]+(a)[2]*(b)[2])
static float Com_Clamp(float lo,float hi,float v){return v<lo?lo:v>hi?hi:v;}
enum{DWSHADOW_SOURCE_PERSISTENT_PHYSICAL=1,DWSHADOW_SOURCE_PERSISTENT_FIRE=2,DWSHADOW_SOURCE_OTHER_DYNAMIC=3};
typedef struct {
    vec3_t origin,color;
    float radius;
    qboolean iflcActive,iflcOptIn;
    vec3_t iflcBaseColor;
    float iflcBaseRadius;
    int staticPromoteFixtureId,shadowSourceClass;
    qboolean noDlightShadow;
} dlight_t;
typedef struct{vec3_t vieworg;}refdef_t;
typedef struct{float value;int integer;}cvar_t;
static cvar_t groupCvar={1,1},mergeCvar={16,16};
static cvar_t *s_rStaticPromotePhysicalShadowGroup=&groupCvar;
static cvar_t *s_rStaticPromotePhysicalGroupMergeRadius=&mergeCvar;
static void R_DarkWolfEnsurePhysicalShadowGroupCvars(void){}
'''

CASES = r'''
static void eq(float a,float b){assert(fabsf(a-b)<1e-6f);}
int main(void){
    dlight_t original={0},peer={0},controlled,plain,optIn,before;
    refdef_t view={{30,40,50}};
    float gains[]={0,.5f,2,3};
    float baseScore,lastOptIn=-1;
    original.origin[0]=100;original.origin[1]=200;original.origin[2]=300;
    original.color[0]=1;original.color[1]=.52f;original.color[2]=.16f;
    original.radius=200;original.staticPromoteFixtureId=10;
    original.shadowSourceClass=DWSHADOW_SOURCE_PERSISTENT_FIRE;
    peer=original;peer.origin[0]+=8;peer.staticPromoteFixtureId=11;
    assert(R_DarkWolfStaticPromoteShadowCompanionEquivalent(&original,&peer));
    baseScore=R_DlightShadowSelectionScore(&original,&view);
    assert(R_IFLC_ShadowSelectionColor(&original)==original.color);
    eq(R_IFLC_ShadowSelectionRadius(&original),original.radius);
    /* Arbitrary inactive extension bytes cannot affect unprofiled lighting. */
    plain=original;plain.iflcOptIn=1;plain.iflcBaseRadius=1;
    plain.iflcBaseColor[0]=99;plain.iflcBaseColor[1]=98;plain.iflcBaseColor[2]=97;
    eq(R_DlightShadowSelectionScore(&plain,&view),baseScore);
    assert(R_DarkWolfStaticPromoteShadowCompanionEquivalent(&plain,&peer));
    for(int i=0;i<4;i++){
        controlled=original;controlled.iflcActive=1;
        controlled.iflcBaseRadius=original.radius;
        VectorCopy(original.color,controlled.iflcBaseColor);
        VectorScale(original.color,gains[i],controlled.color);
        controlled.radius=350;
        before=controlled;
        eq(R_DlightShadowSelectionScore(&controlled,&view),baseScore);
        assert(R_DarkWolfStaticPromoteShadowCompanionEquivalent(&controlled,&peer));
        assert(!memcmp(&before,&controlled,sizeof(controlled)));
        /* A newly opted-in emitter has no old shadow reservation. Its actual
         * power/radius participate in ranking exactly like any ordinary light. */
        optIn=controlled;optIn.iflcOptIn=1;
        plain=optIn;plain.iflcActive=0;
        eq(R_DlightShadowSelectionScore(&optIn,&view),R_DlightShadowSelectionScore(&plain,&view));
        assert(R_DlightShadowSelectionScore(&optIn,&view)>lastOptIn);
        lastOptIn=R_DlightShadowSelectionScore(&optIn,&view);
        assert(R_DarkWolfStaticPromoteShadowCompanionEquivalent(&optIn,&peer)==
            R_DarkWolfStaticPromoteShadowCompanionEquivalent(&plain,&peer));
        assert(R_IFLC_ShadowSelectionColor(&optIn)==optIn.color);
        eq(R_IFLC_ShadowSelectionRadius(&optIn),350);
    }
    /* Hue edits also leave existing ownership untouched, including direct=0. */
    controlled=original;controlled.iflcActive=1;controlled.iflcBaseRadius=original.radius;
    VectorCopy(original.color,controlled.iflcBaseColor);
    controlled.color[0]=0;controlled.color[1]=0;controlled.color[2]=3;
    eq(R_DlightShadowSelectionScore(&controlled,&view),baseScore);
    assert(R_DarkWolfStaticPromoteShadowCompanionEquivalent(&controlled,&peer));
    /* Existing geometric and eligibility boundaries remain enforced. */
    peer.origin[0]+=100;
    assert(!R_DarkWolfStaticPromoteShadowCompanionEquivalent(&controlled,&peer));
    peer=original;peer.staticPromoteFixtureId=11;peer.radius+=17;
    assert(!R_DarkWolfStaticPromoteShadowCompanionEquivalent(&controlled,&peer));
    peer=original;peer.staticPromoteFixtureId=11;peer.color[1]+=.5f;
    assert(!R_DarkWolfStaticPromoteShadowCompanionEquivalent(&controlled,&peer));
    peer=original;peer.staticPromoteFixtureId=11;peer.noDlightShadow=1;
    assert(!R_DarkWolfStaticPromoteShadowCompanionEquivalent(&controlled,&peer));
    puts("IFLC_SHADOW_SELECTION_CPU_PASS unprofiled parity, direct/color/radius existing-owner parity, opt-in normal ranking, unchanged eligibility, no mutation");
    return 0;
}
'''


def run(source_root, output, compiler):
    path = source_root / "SP/code/rend2/tr_main.c"
    source = path.read_text(encoding="utf-8")
    bodies = "\n\n".join(extract_function(source, name) for name in FUNCTIONS)
    output.mkdir(parents=True, exist_ok=True)
    c_file = output / "shadow_tests_extracted.c"
    binary = output / "shadow_tests"
    c_file.write_text(SUPPORT + bodies + CASES, encoding="utf-8")
    subprocess.run(
        [compiler, "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror",
         str(c_file), "-lm", "-o", str(binary)], check=True
    )
    subprocess.run([str(binary.resolve())], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--cc", default="gcc")
    args = parser.parse_args()
    if args.output:
        run(args.source_root, args.output, args.cc)
    else:
        with tempfile.TemporaryDirectory(prefix="iflc-shadow-tests-") as directory:
            run(args.source_root, pathlib.Path(directory), args.cc)


if __name__ == "__main__":
    main()
