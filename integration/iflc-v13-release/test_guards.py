#!/usr/bin/env python3
"""Execute actual new C functions with bounded current-frame owner fixtures."""
from pathlib import Path
import re,sys,subprocess,json,os
src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
def function(path,name):
 s=path.read_text();start=s.index('static int '+name+'(');brace=s.index('{',start);depth=1
 for t in re.finditer(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[{}]',s[brace+1:],re.S):
  if t[0] not in '{}':continue
  depth+=1 if t[0]=='{' else -1
  if not depth:return s[start:brace+1+t.end()]
 raise ValueError(name)
funcs=function(src/'SP/code/rend2/tr_backend.c','RB_FireWorldOwner')+'\n'+function(src/'SP/code/rend2/tr_main.c','R_ElectricFixtureForCapture')
support=r'''
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define MAX_DLIGHTS 32
#define DLIGHT_WORLD_CACHE_MAX 32
typedef float vec3_t[3];
typedef struct { vec3_t origin; int worldOcclusion,iflcOptIn,fireVolumetricSource,fixture,group; } dlight_t;
typedef struct { int num_dlights; dlight_t dlights[MAX_DLIGHTS]; signed char dlightWorldSlot[MAX_DLIGHTS]; } refdef_t;
static struct { refdef_t refdef; } backEnd;
static struct { refdef_t refdef; void *dlightWorldCubemaps[DLIGHT_WORLD_CACHE_MAX]; } tr;
#define VectorSubtract(a,b,d) do {int k;for(k=0;k<3;k++)(d)[k]=(a)[k]-(b)[k];} while(0)
#define DotProduct(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1]+(a)[2]*(b)[2])
static int R_ElectricFixtureForLight(const dlight_t *d){return d->fixture;}
static int R_DarkWolfStaticPromoteShadowGroupEligible(const dlight_t *d){return d->group>=0;}
static int R_DarkWolfStaticPromoteShadowGroupCanonicalId(int i){return tr.refdef.dlights[i].group;}
static int count;
#define CHECK(x) do{count++;if(!(x)){fprintf(stderr,"FAIL line=%d expr=%s\n",__LINE__,#x);return 1;}}while(0)
'''
cases=r'''
int main(void){
 dlight_t lamp;vec3_t plume={0,0,0};int i;
 memset(&lamp,0,sizeof(lamp));memset(&backEnd,0,sizeof(backEnd));memset(&tr,0,sizeof(tr));
 CHECK(RB_FireWorldOwner(NULL,plume)==-1);
 CHECK(RB_FireWorldOwner(&lamp,plume)==-1);
 backEnd.refdef.num_dlights=1;backEnd.refdef.dlights[0].worldOcclusion=1;backEnd.refdef.dlights[0].iflcOptIn=1;tr.dlightWorldCubemaps[0]=&lamp;
 CHECK(RB_FireWorldOwner(&lamp,plume)==0);
 backEnd.refdef.dlights[0].worldOcclusion=0;CHECK(RB_FireWorldOwner(&lamp,plume)==-1);backEnd.refdef.dlights[0].worldOcclusion=1;
 backEnd.refdef.dlights[0].iflcOptIn=0;CHECK(RB_FireWorldOwner(&lamp,plume)==-1);
 backEnd.refdef.dlights[0].fireVolumetricSource=1;CHECK(RB_FireWorldOwner(&lamp,plume)==0);
 backEnd.refdef.dlightWorldSlot[0]=-1;CHECK(RB_FireWorldOwner(&lamp,plume)==-1);
 backEnd.refdef.dlightWorldSlot[0]=32;CHECK(RB_FireWorldOwner(&lamp,plume)==-1);
 backEnd.refdef.dlightWorldSlot[0]=0;tr.dlightWorldCubemaps[0]=NULL;CHECK(RB_FireWorldOwner(&lamp,plume)==-1);tr.dlightWorldCubemaps[0]=&lamp;
 lamp.origin[2]=-12;CHECK(RB_FireWorldOwner(&lamp,plume)==-1);
 backEnd.refdef.dlights[0].iflcOptIn=1;CHECK(RB_FireWorldOwner(&lamp,plume)==0);
 CHECK(RB_FireWorldOwner(&lamp,NULL)==-1);
 plume[0]=16.01f;CHECK(RB_FireWorldOwner(&lamp,plume)==-1);plume[0]=0;
 backEnd.refdef.num_dlights=2;backEnd.refdef.dlights[1]=backEnd.refdef.dlights[0];CHECK(RB_FireWorldOwner(&lamp,plume)==-1);
 backEnd.refdef.dlights[1].origin[0]=200;CHECK(RB_FireWorldOwner(&lamp,plume)==0);
 backEnd.refdef.dlights[1].origin[0]=0;backEnd.refdef.dlights[1].worldOcclusion=0;CHECK(RB_FireWorldOwner(&lamp,plume)==0);
 CHECK(R_ElectricFixtureForCapture(-1)==0);CHECK(R_ElectricFixtureForCapture(0)==0);
 tr.refdef.num_dlights=1;tr.refdef.dlights[0].fixture=3;tr.refdef.dlights[0].group=-1;CHECK(R_ElectricFixtureForCapture(0)==3);
 CHECK(R_ElectricFixtureForCapture(1)==0);CHECK(R_ElectricFixtureForCapture(32)==0);
 tr.refdef.num_dlights=3;for(i=0;i<3;i++){tr.refdef.dlights[i].group=7;tr.refdef.dlights[i].fixture=3;}CHECK(R_ElectricFixtureForCapture(0)==3);
 tr.refdef.dlights[1].fixture=4;CHECK(R_ElectricFixtureForCapture(0)==0);
 tr.refdef.dlights[1].fixture=0;CHECK(R_ElectricFixtureForCapture(0)==0);
 tr.refdef.dlights[1].group=8;CHECK(R_ElectricFixtureForCapture(0)==3);
 tr.refdef.dlights[0].fixture=0;CHECK(R_ElectricFixtureForCapture(0)==0);
 printf("IFLC13_REAL_C_GUARDS_PASS assertions=%d\n",count);return 0;
}
'''
p=out/'guards.c';p.write_text(support+funcs+cases)
results=[]
for mode,flags in [('sanitized',['-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer']),('release',['-O3','-ffast-math'])]:
 exe=out/('guards-'+mode);subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror',*flags,str(p),'-o',str(exe)],check=True)
 env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0');r=subprocess.run([str(exe)],text=True,capture_output=True,env=env);(out/(mode+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,(mode,r.stderr);print(r.stdout.strip());results.append({'mode':mode,'output':r.stdout.strip(),'returncode':r.returncode})
(out/'RESULT.json').write_text(json.dumps({'actual_C_functions':['RB_FireWorldOwner','R_ElectricFixtureForCapture'],'tests':results,'limits':'Small fixture arrays, not full game or all lights.'},indent=2)+'\n')
