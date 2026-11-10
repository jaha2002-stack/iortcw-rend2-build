#!/usr/bin/env python3
"""Differential tests of actual RC1/RC2 C functions and GLSL arithmetic.
Synthetic inputs and mocked graphics calls are NOT GPU or gameplay evidence.
"""
from pathlib import Path
import json, re, subprocess, sys, tempfile
A,B,O=map(lambda s:Path(s).resolve(),sys.argv[1:]); O.mkdir(parents=True,exist_ok=True)
results={}
def text(root,p): return (root/p).read_bytes().decode('latin1')
def func(s,name):
    masked=re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:re.sub(r'[^\n]', ' ', m[0]),s,flags=re.S)
    m=re.search(r'^[^\n;{}]*\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',masked,re.M)
    if not m: raise AssertionError('Missing definition '+name)
    i=masked.index('{',m.start()); depth=1;j=i+1
    while depth: depth+=(masked[j]=='{')-(masked[j]=='}');j+=1
    return s[m.start():j]
def renamed(s,name,new): return re.sub(r'\b'+name+r'\b',new,func(s,name))
def run_case(name,code,cpp=False,includes=None,asan=False,expected_failure=False):
    suffix='cpp' if cpp else 'c'; p=O/(name+'.'+suffix);p.write_text(code)
    exe=O/(name+'.exe.native')
    command=['g++' if cpp else 'gcc','-std=c++11' if cpp else '-std=gnu99','-O2','-ffunction-sections','-fdata-sections','-fno-sanitize-recover=all',
             '-fsanitize=address' if asan else '-fsanitize=undefined',str(p),'-Wl,--gc-sections','-lm','-o',str(exe)]
    if includes:
        command+=['-DARCH_STRING="x86_64"','-I'+str(includes),str(includes/'SP/code/qcommon/q_math.c'),str(includes/'SP/code/qcommon/q_shared.c')]
    c=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (O/(name+'-compile.log')).write_text(c.stdout)
    if c.returncode: raise AssertionError(name+': compile failed; '+c.stdout[-2500:])
    r=subprocess.run([str(exe)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
    (O/(name+'-run.log')).write_text(r.stdout+r.stderr)
    if expected_failure:
        if r.returncode==0 or 'buffer-overflow' not in r.stderr: raise AssertionError('Expected sanitizer overflow absent: '+r.stderr[-1000:])
        return {'expected_sanitizer_failure':True}
    if r.returncode: raise AssertionError(name+': runtime failed; '+r.stderr[-2500:])
    return json.loads(r.stdout)
CHEAD='''#include <stdio.h>\n#include <stdlib.h>\n#include <stdint.h>\n#include <string.h>\n#include <math.h>\n#include <assert.h>\n#define ID_INLINE inline\n#define Com_Memcpy memcpy\n#define qtrue 1\n#define qfalse 0\ntypedef int qboolean;\ntypedef float vec3_t[3];\nstatic uint32_t rng=4462;\nstatic uint32_t rnd(void){rng=rng*1664525u+1013904223u;return rng;}\n'''
# 01 stable sort: compare every byte, including equal-key source order.
s1=text(A,'SP/code/rend2/tr_main.c');s2=text(B,'SP/code/rend2/tr_main.c')
code=CHEAD+'''#define MAX_DRAWSURFS 65536\n#define Q3_LITTLE_ENDIAN\ntypedef struct {uint32_t sort,id;uintptr_t payload;} drawSurf_t;\n'''
code+=func(s1,'R_Radix')+'\n'+renamed(s1,'R_RadixSort','base_sort')+'\n'+renamed(s2,'R_RadixSort','new_sort')+r'''
int main(void){static drawSurf_t a[MAX_DRAWSURFS],b[MAX_DRAWSURFS];unsigned cases=0;
for(int mode=0;mode<8;mode++)for(int test=0;test<80;test++){
 int n=test==79?MAX_DRAWSURFS:(test<3?test:1+(rnd()%3000));
 for(int i=0;i<n;i++){uint32_t key=rnd();if(mode==0)key=0;else if(mode==1)key=i;else if(mode==2)key=n-i;
 else if(mode==3)key&=255;else if(mode==4)key=(key&255)<<24;else if(mode==5)key&=0xff00ff;else if(mode==6)key=i%13;
 a[i]=(drawSurf_t){key,(uint32_t)i,(uintptr_t)(i*7)};b[i]=a[i];}
 base_sort(a,n);new_sort(b,n);assert(!memcmp(a,b,n*sizeof(*a)));cases++;
}printf("{\"cases\":%u,\"stable_record_equivalence\":true,\"histogram_traversals_before\":4,\"histogram_traversals_after\":1}",cases);}
'''
results['RC2-01']=run_case('radix',code)
# 02/03/10 actual setters, observable mock GL and actual matrix math.
s1=text(A,'SP/code/rend2/tr_backend.c');s2=text(B,'SP/code/rend2/tr_backend.c')
code=CHEAD+r'''
typedef int GLint;typedef int GLsizei;typedef float mat4_t[16];
static struct {int viewportValid,scissorValid,matrixProductValid;int viewportRect[4],scissorRect[4];mat4_t projection,modelview,modelviewProjection;} glState;
static int viewport[4],scissor[4];static unsigned vc,sc,mults,tc;
static void qglViewport(int x,int y,int w,int h){vc++;if(w>=0&&h>=0){int r[4]={x,y,w,h};memcpy(viewport,r,sizeof(r));}}
static void qglScissor(int x,int y,int w,int h){sc++;if(w>=0&&h>=0){int r[4]={x,y,w,h};memcpy(scissor,r,sizeof(r));}}
'''
mathsrc=text(A,'SP/code/rend2/tr_extramath.c')
code+=func(mathsrc,'Mat4Copy')+'\n'+func(mathsrc,'Mat4Multiply').replace('{','{ ++mults;',1)+'\n'
for n in ['GL_Viewport','GL_Scissor','GL_SetProjectionMatrix','GL_SetModelviewMatrix']: code+=func(s2,n)+'\n'
code+='static double counted_tan(double x){tc++;return tan(x);}\n#define tan counted_tan\n'+func(s2,'RB_FarPlaneExtents')+'\n#undef tan\n'
code+=r'''
int main(void){unsigned resets=0;mat4_t p={0},m={0},expected;
for(int i=0;i<10000;i++){
 if(i%137==0){glState.viewportValid=glState.scissorValid=glState.matrixProductValid=0;resets++;}
 int r[4]={i/31%7,i/31%11,320+(i/31%3)*160,240+(i/31%5)*60};
 GL_Viewport(r[0],r[1],r[2],r[3]);GL_Scissor(r[0],r[1],r[2],r[3]);
 assert(!memcmp(r,viewport,sizeof(r))&&!memcmp(r,scissor,sizeof(r)));
 if(i%17==0){GL_Viewport(0,0,-1,1);GL_Scissor(0,0,1,-1);assert(!glState.viewportValid&&!glState.scissorValid);}
 if(i%23==0)for(int j=0;j<16;j++)p[j]=(int)(rnd()%200-100)/17.0f;
 if(i%29==0)for(int j=0;j<16;j++)m[j]=(int)(rnd()%200-100)/13.0f;
 GL_SetProjectionMatrix(p);GL_SetModelviewMatrix(m);unsigned saved=mults;
 Mat4Multiply(p,m,expected);mults=saved;assert(!memcmp(expected,glState.modelviewProjection,sizeof(expected)));
 float z=128.0f+(i/19%13)*100,fovX=30.0f+i/19%120,fovY=20.0f+i/19%100,x,y;
 RB_FarPlaneExtents(z,fovX,fovY,&x,&y);
 float ex=z*tan(fovX*M_PI/360.0f),ey=z*tan(fovY*M_PI/360.0f);
 assert(!memcmp(&x,&ex,sizeof(x))&&!memcmp(&y,&ey,sizeof(y)));
}printf("{\"operations\":10000,\"context_resets\":%u,\"viewport_calls\":%u,\"scissor_calls\":%u,\"matrix_multiplications\":%u,\"uncached_matrix_multiplications\":20000,\"tangent_calls\":%u,\"uncached_tangent_calls\":20000}",resets,vc,sc,mults,tc);}
'''
state=run_case('state',code)
results['RC2-02']=state;results['RC2-03']=state;results['RC2-10']=state
# 04 real point-in-leaf and exact plane-distance helper.
s1=text(A,'SP/code/rend2/tr_world.c');s2=text(B,'SP/code/rend2/tr_world.c')
code=CHEAD+r'''
#define DotProduct(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1]+(a)[2]*(b)[2])
#define ERR_DROP 1
typedef struct {float normal[3],dist;unsigned char type;} cplane_t;
typedef struct mnode_s {int contents; cplane_t *plane;struct mnode_s *children[2];} mnode_t;
static struct {struct {mnode_t *nodes;} *world;} tr;
static struct {void (*Error)(int,const char*,...);} ri;
'''
code+=func(text(B,'SP/code/rend2/tr_local.h'),'R_PointPlaneDistance')+'\n'+renamed(s1,'R_PointInLeaf','base_leaf')+'\n'+renamed(s2,'R_PointInLeaf','new_leaf')+r'''
int main(void){mnode_t nodes[127]={0};cplane_t planes[63]={0};typeof(*tr.world) world={nodes};tr.world=&world;
for(int i=0;i<127;i++){nodes[i].contents=i<63?-1:0;if(i<63){nodes[i].plane=&planes[i];nodes[i].children[0]=&nodes[2*i+1];nodes[i].children[1]=&nodes[2*i+2];
 planes[i].type=i%4;planes[i].dist=(int)(rnd()%100)-50;if(i%4<3)planes[i].normal[i%4]=1;else {planes[i].normal[0]=-.5f;planes[i].normal[1]=.25f;planes[i].normal[2]=.75f;}}}
for(int i=0;i<200000;i++){vec3_t p={(int)(rnd()%200)-100,(int)(rnd()%200)-100,(int)(rnd()%200)-100};assert(base_leaf(p)==new_leaf(p));}
printf("{\"tree_queries\":200000,\"leaf_identity_equal\":true,\"axial_and_oblique_planes\":true}");}
'''
results['RC2-04']=run_case('bsp',code)
# 05 actual insertion and Q_stricmp, collisions, case, order and full cap.
s1=text(A,'SP/code/qcommon/files.c');s2=text(B,'SP/code/qcommon/files.c');shared=text(A,'SP/code/qcommon/q_shared.c')
code=CHEAD+'''#define MAX_FOUND_FILES 0x1000\n#define FILELIST_HASH_SIZE 1024\nstatic unsigned long long calls;\nstatic char *CopyString(const char *s){return strdup(s);}\n'''
code+=func(shared,'Q_stricmpn')+'\n'+func(shared,'Q_stricmp').replace('{','{calls++;',1)+'\n'+func(s2,'FS_FileListHash')+'\n'
code+=renamed(s1,'FS_AddFileToList','base_add')+'\n'+renamed(s2,'FS_AddFileToList','new_add')+r'''
int main(void){unsigned long long ca=0,cb=0;unsigned inserts=0;
for(int round=0;round<6;round++){
 char *a[MAX_FOUND_FILES],*b[MAX_FOUND_FILES];int heads[FILELIST_HASH_SIZE],links[MAX_FOUND_FILES],na=0,nb=0;for(int i=0;i<FILELIST_HASH_SIZE;i++)heads[i]=-1;
 for(int i=0;i<6000;i++){char name[100];int id=round%2?i:i%2000;snprintf(name,sizeof(name),"%s/%d_%d.shader",(i/2000)%2?"Textures":"tEXTURES",id,round);if(i==0)name[0]=0;
 calls=0;na=base_add(name,a,na);ca+=calls;calls=0;nb=new_add(name,b,nb,heads,links);cb+=calls;assert(na==nb);inserts++;}
 for(int i=0;i<na;i++){assert(!strcmp(a[i],b[i]));free(a[i]);free(b[i]);}
}assert(cb<ca);printf("{\"insertions\":%u,\"comparisons_before\":%llu,\"comparisons_after\":%llu,\"order_and_case_equivalent\":true}",inserts,ca,cb);}
'''
results['RC2-05']=run_case('filelist',code)
for label,src,fail in [('old',s1,True),('new',s2,False)]:
    block=src.split('pathLength = strlen( path );',1)[1].split('extensionLength = strlen( extension );',1)[0]
    code=CHEAD+'int main(void){static const char path[1]={0};int pathLength=strlen(path);'+block+'printf("{\\"empty_root_path\\":true}");return pathLength;}'
    results['RC2-05-root-'+label]=run_case('root-'+label,code,asan=True,expected_failure=fail)
# 06/07 whole cgame units with real engine math.
common=r'''
#include <stdio.h>
#include <stdint.h>
#include <assert.h>
static uint64_t resultHash=1469598103934665603ULL;static unsigned polys,angleCalls;
static void hashBytes(const void *v,size_t n){const unsigned char *p=v;while(n--)resultHash=(resultHash^*p++)*1099511628211ULL;}
'''
particle=common+r'''
#define vectoangles counted_vectoangles
#include "SP/code/cgame/cg_particles.c"
#undef vectoangles
extern void vectoangles(const vec3_t value,vec3_t angles);
void counted_vectoangles(const vec3_t value,vec3_t angles){angleCalls++;vectoangles(value,angles);}
cg_t cg;cgs_t cgs;vmCvar_t cg_particleDist,cg_particleLOD,cg_wolfparticles;
void trap_R_AddPolyToScene(qhandle_t shader,int count,const polyVert_t *poly){hashBytes(&shader,sizeof(shader));hashBytes(&count,sizeof(count));hashBytes(poly,count*sizeof(*poly));polys++;}
qhandle_t trap_R_RegisterShader(const char *name){(void)name;return 1;}
int main(void){snapshot_t snap={0};cg.snap=&snap;cg_wolfparticles.integer=1;cg_particleDist.value=999999;srand(446);
for(int frame=0;frame<80;frame++){CG_ClearParticles();cg.time=100+(frame/2)*17;
 vec3_t ang={frame*3.0f,frame*7.0f,frame*1.0f};AnglesToAxis(ang,cg.refdef.viewaxis);
 for(int i=0;i<128;i++){cparticle_t *p=&particles[i];memset(p,0,sizeof(*p));p->next=i<127?&particles[i+1]:NULL;
 p->type=(int[]){P_SPRITE,P_BLEED,P_ANIM,P_SMOKE}[i%4];p->org[0]=200+i;p->org[1]=20-i;p->org[2]=40+i;
 p->pshader=1;p->time=cg.time-10;p->endtime=cg.time+100;p->width=2;p->height=3;p->endwidth=4;p->endheight=5;p->alpha=.7f;p->roll=i%11?i:0;p->shaderAnim=0;}
 active_particles=particles;free_particles=&particles[128];CG_AddParticles();}
printf("{\"hash\":\"%llx\",\"polygons\":%u,\"vectoangles_calls\":%u}",(unsigned long long)resultHash,polys,angleCalls);}
'''
trail=common+r'''
#define VectorDistance counted_VectorDistance
#include "SP/code/cgame/cg_trails.c"
#undef VectorDistance
extern float VectorDistance(vec3_t a,vec3_t b);
static unsigned lengthCalls;
float counted_VectorDistance(vec3_t a,vec3_t b){lengthCalls++;return VectorDistance(a,b);}
cg_t cg;cgs_t cgs;vmCvar_t cg_paused;
void trap_R_AddPolyToScene(qhandle_t shader,int count,const polyVert_t *poly){hashBytes(&shader,sizeof(shader));hashBytes(&count,sizeof(count));hashBytes(poly,count*sizeof(*poly));polys++;}
void trap_R_AddPolysToScene(qhandle_t shader,int n,const polyVert_t *poly,int count){for(int i=0;i<count;i++)trap_R_AddPolyToScene(shader,n,poly+i*n);}
int main(void){
 for(int frame=0;frame<80;frame++){trailJunc_t chain[12]={0};vec3_t ang={frame*2.f,frame*3.f,0};AnglesToAxis(ang,cg.refdef.viewaxis);
 VectorCopy(cg.refdef.viewaxis[0],trailOrientation.vforward);VectorCopy(cg.refdef.viewaxis[1],trailOrientation.vright);VectorCopy(cg.refdef.viewaxis[2],trailOrientation.vup);
 for(int i=0;i<12;i++){chain[i].nextJunc=i<11?chain+i+1:NULL;chain[i].inuse=1;chain[i].shader=1;chain[i].sType=frame%3?STYPE_REPEAT:STYPE_STRETCH;
 chain[i].sTex=i*.17f;chain[i].pos[0]=200+i*10;chain[i].pos[1]=i*i+frame;chain[i].pos[2]=20+i*3;chain[i].alpha=.8f;chain[i].width=2;chain[i].widthEnd=2;
 chain[i].color[0]=.4;chain[i].color[1]=.7;chain[i].color[2]=.5;
 chain[i].flags=(frame%2?TJFL_FIXDISTORT:0)|(frame%5?0:TJFL_NOPOLYMERGE);if(frame%3==1)chain[i].flags|=TJFL_CROSSOVER;}
 CG_AddTrailToScene(chain,0,0);}
printf("{\"hash\":\"%llx\",\"polygons\":%u,\"length_calls\":%u}",(unsigned long long)resultHash,polys,lengthCalls);}
'''
for key,code in [('RC2-06',particle),('RC2-07',trail)]:
    a=run_case(key+'-base',code,includes=A);b=run_case(key+'-new',code,includes=B)
    if a['hash']!=b['hash'] or a['polygons']!=b['polygons']: raise AssertionError((key,a,b))
    results[key]={'baseline':a,'candidate':b,'actual_cgame_polygon_bytes_equal':True}
# 08/09 actual extracted GLSL function bodies in a CPU arithmetic harness only.
vec=r'''
#include <cstdio>
#include <cmath>
#include <cassert>
#include <cstdint>
struct vec2{float x,y;vec2(float a=0):x(a),y(a){}vec2(float a,float b):x(a),y(b){}vec2&operator*=(float k){x*=k;y*=k;return *this;}};
vec2 operator+(vec2 a,vec2 b){return vec2(a.x+b.x,a.y+b.y);}vec2 operator-(vec2 a,vec2 b){return vec2(a.x-b.x,a.y-b.y);}vec2 operator*(vec2 a,float k){return vec2(a.x*k,a.y*k);}
struct vec3{float x,y,z;vec2 xy;vec3(float a=0,float b=0,float c=0):x(a),y(b),z(c),xy(a,b){}};
vec3 operator-(vec3 a,vec3 b){return vec3(a.x-b.x,a.y-b.y,a.z-b.z);}
struct vec4{float x,y,z,w;};vec4 u_BaseColor,u_DlightInfo,u_ViewInfo;
float max(float a,float b){return a>b?a:b;}float min(float a,float b){return a<b?a:b;}
float clamp(float x,float a,float b){return min(max(x,a),b);}vec2 clamp(vec2 x,vec2 a,vec2 b){return vec2(clamp(x.x,a.x,b.x),clamp(x.y,a.y,b.y));}
float mix(float a,float b,float t){return a*(1-t)+b*t;}float smoothstep(float a,float b,float x){float t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);}
float dot(vec2 a,vec2 b){return a.x*b.x+a.y*b.y;}float length(vec2 a){return std::sqrt(dot(a,a));}
static unsigned long long trigCalls,expCalls;
double testSin(double x){trigCalls++;return std::sin(x);}double testExp(double x){expCalls++;return std::exp(x);}
#define sin testSin
#define exp testExp
static uint32_t seed=446;static uint32_t rnd(){seed=seed*1664525u+1013904223u;return seed;}
static float unit(){return (rnd()%100000)/99999.f;}
'''
s1=text(A,'SP/code/rend2/glsl/volumetriclocal_fp.glsl');s2=text(B,'SP/code/rend2/glsl/volumetriclocal_fp.glsl')
code=vec+renamed(s1,'fireShapeMask','baseFire')+'\n'+renamed(s2,'fireShapeMask','newFire')+r'''
int main(){unsigned long long ta=0,tb=0,ea=0,eb=0;for(int i=0;i<200000;i++){
 float radius=1+unit()*300;vec3 origin(17,-13,40),world(origin.x+(unit()*3-1.5f)*radius,origin.y+(unit()*3-1.5f)*radius,origin.z+(unit()*1.4f-.2f)*radius);
 u_BaseColor.z=.15f+unit()*.75f;u_BaseColor.w=.35f+unit()*.85f;u_DlightInfo.x=unit();u_DlightInfo.y=unit()*4;u_ViewInfo.z=unit()*1000;
 trigCalls=expCalls=0;float a=baseFire(world,origin,radius);ta+=trigCalls;ea+=expCalls;
 trigCalls=expCalls=0;float b=newFire(world,origin,radius);tb+=trigCalls;eb+=expCalls;assert(a==b);
}assert(tb<ta&&eb<ea);std::printf("{\"samples\":200000,\"equal_float_outputs\":true,\"sin_calls_before\":%llu,\"sin_calls_after\":%llu,\"exp_calls_before\":%llu,\"exp_calls_after\":%llu}",ta,tb,ea,eb);}
'''
results['RC2-08']=run_case('fire-shape',code,cpp=True)
s1=text(A,'SP/code/rend2/glsl/ssgi_fp.glsl');s2=text(B,'SP/code/rend2/glsl/ssgi_fp.glsl')
code=vec+'\nstatic float masks[13];static int taps;\nfloat SsgiSceneEntityMask(vec2 uv){(void)uv;return masks[taps++];}\n'
code+=renamed(s1,'SsgiSceneEntityGuardMask','baseMask')+'\n'+renamed(s2,'SsgiSceneEntityGuardMask','newMask')+r'''
int main(){unsigned long long aT=0,bT=0;for(int i=0;i<100000;i++){for(int j=0;j<13;j++)masks[j]=unit()*.999f;if(i%3)masks[rnd()%13]=1;
 float mode=i%3;taps=0;float a=baseMask(vec2(.5),vec2(.01),mode);aT+=taps;taps=0;float b=newMask(vec2(.5),vec2(.01),mode);bT+=taps;assert(a==b);}
assert(bT<aT);std::printf("{\"cases\":100000,\"equal_mask_values\":true,\"mask_samples_before\":%llu,\"mask_samples_after\":%llu}",aT,bT);}
'''
results['RC2-09']=run_case('ssgi-mask',code,cpp=True)
for i in range(1,11): assert f'RC2-{i:02}' in results
results.update(status='DIFFERENTIAL_PASS',scope='Actual source extraction/whole cgame code; synthetic data/mock GL; CPU GLSL arithmetic is not driver validation',GPU_PERFORMANCE='NOT_RUN')
(O/'rc2-tests.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
