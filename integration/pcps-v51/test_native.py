#!/usr/bin/env python3
"""Compile real PCPS V5.1 C functions out of patched tr_main.c and test fire reversibility."""
import argparse
import pathlib
import re
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument("source",type=pathlib.Path)
parser.add_argument("--out",type=pathlib.Path,default=pathlib.Path("/tmp/dw_pcps_v51_native"))
args=parser.parse_args()
src=args.source.read_text(encoding="utf-8")

def extract(name):
    m=re.search(re.escape(name)+r"[^;{}]*\{",src)
    if m is None: raise ValueError("missing real C definition: "+name)
    first=src.index("{",m.start())
    depth=0
    for i in range(first,len(src)):
        if src[i]=="{": depth+=1
        if src[i]=="}":
            depth-=1
            if depth==0:return src[m.start():i+1]
    raise ValueError("unclosed C function "+name)

functions=[
 "static qboolean DWPS_SameSource(",
 "static int DWPS_FindRuleForLight(",
 "unsigned int DWPS_ApplyPendingMask(",
 "static qboolean DWPS5_FireTagged(",
 "static int DWPS5_LiveLinkedIndex(",
 "static int DWPS5_EnsurePointRule(",
 "static void DWPS5_FirePoint_f("
]

harness=r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdarg.h>
#include <math.h>
#define qtrue 1
#define qfalse 0
#define PRINT_ALL 0
#define PRINT_WARNING 1
#define DWSHADOW_SOURCE_PERSISTENT_FIRE 2
#define DWPS_MAX_RULES 24
#define MAX_DLIGHTS 32
typedef int qboolean;
typedef float vec3_t[3];
typedef struct {vec3_t origin;float radius;int shadowSourceClass;int staticPromoteFixtureId;int fireVolumetricSource;}dlight_t;
typedef struct {vec3_t origin;float radius;int sourceClass;int fixtureId;int shadowOff;int numCasters;}dwpsRule_t;
static dwpsRule_t dwpsRules[DWPS_MAX_RULES];
static int dwpsNumRules=0;
static struct {void *world;struct {int num_dlights;dlight_t dlights[MAX_DLIGHTS];}refdef;}tr;
static int dwps5LinkedFlame=-1,dwps5LinkedClass=-1,dwps5LinkedFixture=-1,dwps4FireConfirmed=-1;
static vec3_t dwps5LinkedOrigin;
static float dwps5LinkedRadius=0.0f;
static const char *mockCommand="dw_ps_fire_point_off";
static int saved=0;
#define VectorSubtract(a,b,c) do{int k;for(k=0;k<3;k++)(c)[k]=(a)[k]-(b)[k];}while(0)
#define VectorCopy(a,b) memcpy((b),(a),sizeof(vec3_t))
#define DotProduct(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1]+(a)[2]*(b)[2])
#define Com_Memset memset
static int Q_stricmp(const char *a,const char *b){return strcasecmp(a,b);}
static void DWPS_CheckWorld(void){}
static qboolean DWPS4_FireIsSelected(void){return dwps4FireConfirmed>=0;}
static float DWPS4_DistSq(const vec3_t a,const vec3_t b){vec3_t d;VectorSubtract(a,b,d);return DotProduct(d,d);}
static void DWPS_PersistAfterChange(void){saved++;}
static void MockPrint(int lv,const char *fmt,...){va_list a;(void)lv;va_start(a,fmt);vfprintf(stdout,fmt,a);va_end(a);}
static const char *MockCmdArgv(int n){(void)n;return mockCommand;}
static struct {void (*Printf)(int,const char*,...);const char *(*Cmd_Argv)(int);}ri={MockPrint,MockCmdArgv};
"""

test=r"""
#define VERIFY(e,m) do{if(!(e)){fprintf(stderr,"FAIL %s line %d\n",m,__LINE__);exit(3);}puts("PASS " m);}while(0)
static void setup(void)
{
 dlight_t *l;
 memset(&tr,0,sizeof(tr));memset(dwpsRules,0,sizeof(dwpsRules));
 tr.world=&tr;tr.refdef.num_dlights=1;dwpsNumRules=0;saved=0;
 l=&tr.refdef.dlights[0];l->origin[0]=-152;l->origin[1]=1668;l->origin[2]=636;
 l->radius=558.5f;l->shadowSourceClass=2;l->staticPromoteFixtureId=-1;l->fireVolumetricSource=1;
 dwps4FireConfirmed=2994;dwps5LinkedFlame=2994;dwps5LinkedClass=2;dwps5LinkedFixture=-1;
 dwps5LinkedRadius=558.5f;VectorCopy(l->origin,dwps5LinkedOrigin);
}
int main(void)
{
 dlight_t *l;dwpsRule_t *r;
 setup();l=&tr.refdef.dlights[0];
 VERIFY(DWPS5_LiveLinkedIndex()==0,"fire link at radius 558.5");
 mockCommand="dw_ps_fire_point_off";DWPS5_FirePoint_f();
 VERIFY(dwpsNumRules==1 && dwpsRules[0].shadowOff,"OFF saved exactly one rule");
 VERIFY(DWPS_ApplyPendingMask(1u)==0u,"OFF filters point slot eligibility");
 l->radius=393.0f;
 VERIFY(DWPS5_LiveLinkedIndex()==0,"fire link survives 165.5 radius change");
 VERIFY(DWPS_ApplyPendingMask(1u)==0u,"OFF stable at radius 393");
 mockCommand="dw_ps_fire_point_on";DWPS5_FirePoint_f();
 VERIFY(dwpsNumRules==1 && !dwpsRules[0].shadowOff,"ON reuses same rule");
 VERIFY(DWPS_ApplyPendingMask(1u)==1u,"ON restores eligibility");
 l->radius=558.5f;
 VERIFY(DWPS_ApplyPendingMask(1u)==1u && saved==2,"ON stable after radius returns");
 /* Reproduce two old V5 rows belonging to same source and different radii. */
 dwpsNumRules=2;r=&dwpsRules[1];*r=dwpsRules[0];
 r->radius=393.0f;r->shadowOff=qtrue;dwpsRules[0].shadowOff=qfalse;
 VERIFY(DWPS_ApplyPendingMask(1u)==0u,"legacy ghost OFF still blocks");
 DWPS5_FirePoint_f();
 VERIFY(!dwpsRules[0].shadowOff && !dwpsRules[1].shadowOff,"ON reconciles all ghost OFF rows");
 VERIFY(DWPS_ApplyPendingMask(1u)==1u,"old OFF cannot resurrect");
 l->radius=393.0f;
 VERIFY(DWPS_ApplyPendingMask(1u)==1u,"restored state stable at 393");
 tr.refdef.num_dlights=2;tr.refdef.dlights[1]=*l;
 VERIFY(DWPS5_LiveLinkedIndex()==-1,"two indistinguishable fire lights fail closed");
 dwpsRules[0].shadowOff=qtrue;
 VERIFY(DWPS_ApplyPendingMask(3u)==3u,"ambiguous fire cannot be mass suppressed");
 setup();l=&tr.refdef.dlights[0];l->shadowSourceClass=1;l->fireVolumetricSource=0;
 dwpsNumRules=1;r=&dwpsRules[0];memset(r,0,sizeof(*r));
 VectorCopy(l->origin,r->origin);r->sourceClass=1;r->fixtureId=-1;
 r->radius=558.5f;r->shadowOff=qtrue;
 VERIFY(DWPS_ApplyPendingMask(1u)==0u,"ordinary source old-radius rule remains");
 l->radius=393.0f;
 VERIFY(DWPS_ApplyPendingMask(1u)==1u,"ordinary source tolerance NOT changed");
 puts("DW_PCPS_V51_NATIVE_REAL_C_FIRE_POINT_REVERSIBILITY_PASS");
 return 0;
}
"""
args.out.parent.mkdir(parents=True,exist_ok=True)
source=args.out.with_suffix(".c")
source.write_text(harness+"\n\n".join(extract(name) for name in functions)+"\n"+test)
subprocess.run(["gcc","-std=gnu99","-O1","-Wall","-Wextra","-Werror","-o",str(args.out),str(source),"-lm"],check=True)
subprocess.run([str(args.out)],check=True)
