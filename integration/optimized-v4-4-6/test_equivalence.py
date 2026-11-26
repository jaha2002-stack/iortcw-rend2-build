#!/usr/bin/env python3
"""Compile actual baseline/candidate C functions; compare outputs across changing inputs.
This is algorithm validation, not a GPU benchmark or gameplay test.
"""
from pathlib import Path
import sys, subprocess, tempfile, json

def function(s, name):
    import re
    m=re.search(r'^static [^\n]*\b'+name+r'\(',s,re.M)
    assert m, name
    a=m.start(); brace=s.index('{',m.end()); depth=1;i=brace+1
    # Selected functions have no brace characters in strings/comments.
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}');i+=1
    return s[a:i]

root=Path(sys.argv[1]); base=Path(sys.argv[2]); out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
a=(base/'SP/code/rend2/tr_main.c').read_text();b=(root/'SP/code/rend2/tr_main.c').read_text()
name='R_DarkWolfStaticPromoteShadowGroupCanonicalId'
common=r'''
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>
#include <stdarg.h>
#include <assert.h>
typedef int qboolean;
#define qtrue 1
#define qfalse 0
#define MAX_DLIGHTS 32
#define DWSHADOW_SOURCE_PERSISTENT_PHYSICAL 1
#define DWSHADOW_SOURCE_PERSISTENT_FIRE 2
typedef float vec3_t[3];
typedef struct { int integer; float value; } cvar_t;
typedef struct {vec3_t origin,color; float radius; int staticPromoteFixtureId,noDlightShadow,shadowSourceClass;} dlight_t;
static struct {struct {int num_dlights;dlight_t dlights[32];} refdef;} tr;
static cvar_t on={1,1},merge={16,16};
static cvar_t *s_rStaticPromotePhysicalShadowGroup=&on,*s_rStaticPromotePhysicalGroupMergeRadius=&merge;
static void R_DarkWolfEnsurePhysicalShadowGroupCvars(void) {}
#define VectorSubtract(a,b,c) do{for(int k=0;k<3;k++)(c)[k]=(a)[k]-(b)[k];}while(0)
#define DotProduct(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1]+(a)[2]*(b)[2])
#define Com_Memset memset
#define Com_Clamp(l,h,x) fminf(h,fmaxf(l,x))
static unsigned long long comparisons=0;
'''
for n in ['R_DarkWolfShadowSourceIsPersistent','R_DarkWolfStaticPromoteShadowGroupEligible','R_DarkWolfStaticPromoteShadowCompanionEquivalent']:
    f=function(a,n)
    if 'Companion' in n:f=f.replace('{','{ ++comparisons;',1)
    common+='\n'+f
common+='\n'+function(a,name).replace(name,'baseline')
common+='\nstatic qboolean s_dwShadowGroupLabelsActive;\nstatic int s_dwShadowGroupLabels[MAX_DLIGHTS];\n'+function(b,name).replace(name,'optimized')
common+=r'''
static unsigned rng=1;
static unsigned next(void){rng=rng*1664525u+1013904223u;return rng;}
int main(void){
 unsigned long long oldCount=0,newCount=0,checks=0;
 for(int epoch=0;epoch<5000;epoch++){
  tr.refdef.num_dlights=epoch%33; on.integer=(epoch%19)!=0;merge.value=(epoch%11)?16:0;
  for(int i=0;i<32;i++){
   dlight_t *d=&tr.refdef.dlights[i];memset(d,0,sizeof(*d));
   d->staticPromoteFixtureId=(epoch%7)?i:(int)(next()%10)-1;
   d->shadowSourceClass=(epoch%5)?1:next()%4;d->noDlightShadow=(epoch%13==0 && i%3==0);
   d->radius=190+(next()%3)*8;
   for(int k=0;k<3;k++){d->origin[k]=epoch%3==0?(float)(next()%160):(k==0?i*8.0f:0);d->color[k]=0.3f+(next()%2)*0.03f;}
   s_dwShadowGroupLabels[i]=-2;
  }
  s_dwShadowGroupLabelsActive=qtrue;
  for(int repeat=0;repeat<5;repeat++)for(int i=-1;i<=32;i++){
   comparisons=0;int expected=baseline(i);oldCount+=comparisons;
   comparisons=0;int actual=optimized(i);newCount+=comparisons;
   if(expected!=actual){fprintf(stderr,"epoch=%d index=%d expected=%d actual=%d\n",epoch,i,expected,actual);return 1;} checks++;
  }
  s_dwShadowGroupLabelsActive=qfalse;
  /* Outside the invocation, do not reuse labels after mutation. */
  tr.refdef.dlights[0].staticPromoteFixtureId=999;
  assert(baseline(0)==optimized(0));
 }
 printf("{\"comparisons_baseline\":%llu,\"comparisons_optimized\":%llu,\"label_checks\":%llu}",oldCount,newCount,checks);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'groups.c';p.write_text(common);exe=Path(tmp)/'groups'
 subprocess.run(['gcc','-std=c99','-O2','-fsanitize=undefined','-fno-sanitize-recover=all',str(p),'-lm','-o',str(exe)],check=True)
 result=json.loads(subprocess.check_output([str(exe)],text=True))

# The executed light-add function must have byte-identical light output across cvar limits,
# null candidates and a full light list. Formatting stubs count discarded calls.
a=(base/'SP/code/rend2/tr_scene.c').read_text();b=(root/'SP/code/rend2/tr_scene.c').read_text();name='R_StaticPromoteAddCandidate'
prefix=r'''
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <stdarg.h>
typedef int qboolean;
#define qtrue 1
#define qfalse 0
typedef float vec3_t[3];
typedef struct {float value;} cvar_t;
typedef struct {vec3_t origin,color;float intensity;int entityOrdinal;} staticPromoteCandidate_t;
#define MAX(a,b) ((a)>(b)?(a):(b))
#define CLAMP(x,l,h) ((x)<(l)?(l):((x)>(h)?(h):(x)))
#define VectorScale(a,s,b) do{for(int k=0;k<3;k++)(b)[k]=(a)[k]*(s);}while(0)
#define REF_FORCE_DLIGHT 1
#define DARKWOLF_REF_LOCALVOL_LAMP 2
static cvar_t values[7];
static cvar_t *r_staticPromoteGain=&values[0],*r_staticPromoteDirectGain=&values[1],*r_staticPromoteRadiusScale=&values[2],*r_staticPromoteMinRadius=&values[3],*r_staticPromoteMaxRadius=&values[4],*r_staticPromoteMaxColor=&values[5];
static int r_numdlights;
static struct {struct {int forced;} dlights[32];} data,*backEndData=&data;
static float captured[7];static int flags;
static void RE_AddLightToScene(const float *o,float radius,float r,float g,float b,int f){
 if(r_numdlights>=32)return;for(int k=0;k<3;k++)captured[k]=o[k];captured[3]=radius;captured[4]=r;captured[5]=g;captured[6]=b;flags=f;r_numdlights++;
}
static unsigned formats;
static void Com_sprintf(char *p,int n,const char *f,...){formats++;p[0]=0;}
static void R_StaticPromoteAppend(char *p,int n,int *l,const char *s){}
'''
prefix+=function(a,name).replace(name,'baseline')+'\n'+function(b,name).replace(name,'optimized')
prefix+=r'''
int main(void){
 for(int j=0;j<10000;j++){
  for(int i=0;i<6;i++)values[i].value=((j*(i+1))%1100-100)/10.0f;
  staticPromoteCandidate_t c={{1,2,3},{0.3f,0.7f,0.1f},j%900,j};
  char report[768];int len=0;float expected[7];
  r_numdlights=j%33;memset(&data,0,sizeof(data));memset(captured,0,sizeof(captured));flags=0;
  int a=baseline(0,j%17?&c:NULL,"test",0,report,sizeof(report),&len);
  memcpy(expected,captured,sizeof(expected));int count=r_numdlights,flag=flags;typeof(data) saved=data;
  r_numdlights=j%33;memset(&data,0,sizeof(data));memset(captured,0,sizeof(captured));flags=0;
  int b=optimized(j%17?&c:NULL);
  assert(a==b && count==r_numdlights && flag==flags && !memcmp(expected,captured,sizeof(expected)) && !memcmp(&saved,&data,sizeof(data)));
 }
 printf("{\"light_add_cases\":10000,\"discarded_format_calls_removed\":%u}",formats);
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'lights.c';p.write_text(prefix);exe=Path(tmp)/'lights'
 subprocess.run(['gcc','-std=gnu99','-O2','-fsanitize=undefined','-fno-sanitize-recover=all',str(p),'-o',str(exe)],check=True)
 result.update(json.loads(subprocess.check_output([str(exe)],text=True)))
result.update(status='PASS',scope='actual extracted C algorithm differential tests; synthetic inputs; not game FPS')
(out/'algorithm-equivalence.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
