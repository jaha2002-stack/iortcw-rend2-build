/* Standalone, real C native exercise of the exact runtime file journal.
 * This harness compiles integration/pcps-v2/persistence.inc unchanged.
 * No simulated Python parser or fake journal implementation.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdarg.h>
#include <math.h>
#include <assert.h>
#include <stddef.h>
#define MAX_QPATH 64
#define CULLINFO_BOX 1
#define DWPS_MAX_RULES 24
#define DWPS_MAX_CASTERS 32
#define PRINT_ALL 0
#define PRINT_WARNING 1
#define qtrue 1
#define qfalse 0
typedef int qboolean;
typedef int surfaceType_t;
typedef float vec3_t[3];
typedef struct {int type;vec3_t bounds[2];} cullinfo_t;
typedef struct {char name[MAX_QPATH];} shader_t;
typedef struct {surfaceType_t *data;shader_t *shader;cullinfo_t cullinfo;} msurface_t;
typedef struct {
 char name[MAX_QPATH],baseName[MAX_QPATH];
 int dataSize,numWorldSurfaces,numsurfaces;
 msurface_t *surfaces;
} world_t;
static struct {world_t *world;}tr;
typedef struct {int id;surfaceType_t *surface;char material[MAX_QPATH];vec3_t bounds[2];}dwpsCaster_t;
typedef struct {vec3_t origin;float radius;int sourceClass,fixtureId;int shadowOff,numCasters;dwpsCaster_t casters[DWPS_MAX_CASTERS];}dwpsRule_t;
static dwpsRule_t dwpsRules[DWPS_MAX_RULES];
static int dwpsNumRules=0,dwpsSelected=-1,dwpsLastSurface=-1;
static const world_t *dwpsWorld=NULL;
static const msurface_t *dwpsWorldSurfaces=NULL;
static char dwpsMap[MAX_QPATH]="";
#define Com_Memset memset
static void Q_strncpyz(char *dst,const char *src,size_t n){assert(n>0);snprintf(dst,n,"%s",src);}
static int Q_stricmp(const char *a,const char *b){return strcasecmp(a,b);}
static struct {
 long (*FS_ReadFile)(const char *,void **);
 void (*FS_FreeFile)(void *);
 void (*FS_WriteFile)(const char *,const void *,int);
 void (*Printf)(int,const char *,...);
}ri;
static char disk[2][262144],diskPath[2][128];
static int diskLen[2]={0,0},writeBreak=0;
static int diskIndex(const char *path)
{
 size_t n=strlen(path);
 if(n<6)return -1;
 if(strcmp(path+n-6,"_a.dat")==0)return 0;
 if(strcmp(path+n-6,"_b.dat")==0)return 1;
 return -1;
}
static long MockRead(const char *path,void **out)
{
 int i=diskIndex(path);
 *out=NULL;
 if(i<0 || diskLen[i]<=0)return -1;
 *out=malloc((size_t)diskLen[i]+1);
 assert(*out);
 memcpy(*out,disk[i],(size_t)diskLen[i]);
 ((char *)(*out))[diskLen[i]]=0;
 return diskLen[i];
}
static void MockFree(void *ptr){free(ptr);}
static void MockWrite(const char *path,const void *data,int n)
{
 int i=diskIndex(path);
 assert(i>=0 && n>0 && n<=262144);
 snprintf(diskPath[i],sizeof(diskPath[i]),"%s",path);
 diskLen[i]=n;
 memcpy(disk[i],data,(size_t)n);
 if(writeBreak && n>10)disk[i][n/2]^=0x01;
}
static void MockPrint(int level,const char *fmt,...)
{
 va_list args;
 (void)level;
 va_start(args,fmt);
 vfprintf(stdout,fmt,args);
 va_end(args);
}
static qboolean DWPS_CasterValid(const dwpsCaster_t *c)
{
 const msurface_t *m;
 int i,k;
 if(!tr.world || c->id<0 || c->id>=tr.world->numWorldSurfaces)return qfalse;
 m=&tr.world->surfaces[c->id];
 if(!m->data || m->data!=c->surface || !m->shader ||
    Q_stricmp(c->material,m->shader->name) || !(m->cullinfo.type&CULLINFO_BOX))
    return qfalse;
 for(i=0;i<2;i++)for(k=0;k<3;k++)
  if(fabsf(c->bounds[i][k]-m->cullinfo.bounds[i][k])>0.25f)return qfalse;
 return qtrue;
}
static void DWPS_LoadCurrentMap(void);
static void DWPS_CheckWorld(void)
{
 if(!tr.world){dwpsNumRules=0;dwpsWorld=NULL;return;}
 if(dwpsWorld==tr.world && dwpsWorldSurfaces==tr.world->surfaces &&
    !Q_stricmp(dwpsMap,tr.world->name))return;
 dwpsWorld=tr.world;dwpsWorldSurfaces=tr.world->surfaces;
 Q_strncpyz(dwpsMap,tr.world->name,sizeof(dwpsMap));
 dwpsNumRules=0;
 DWPS_LoadCurrentMap();
}
#include "persistence.inc"

static int faceA=4,faceB=5;
static shader_t shaderA={"textures/metal_misc/ametal_m03dm"};
static shader_t shaderB={"textures/lights/light_m4"};
static msurface_t surfA[2]={
 {&faceA,&shaderA,{CULLINFO_BOX,{{-10,-10,-10},{10,10,10}}}},
 {&faceB,&shaderB,{CULLINFO_BOX,{{11,11,-10},{20,20,10}}}}
};
static world_t worldA={"maps/boss1.bsp","boss1",987654,2,2,surfA};
static world_t worldB={"maps/factory.bsp","factory",987654,2,2,surfA};

static void StartLightRule(void)
{
 dwpsNumRules=1;
 Com_Memset(&dwpsRules[0],0,sizeof(dwpsRules[0]));
 dwpsRules[0].origin[0]=-2764;
 dwpsRules[0].origin[1]=-219;
 dwpsRules[0].origin[2]=-24;
 dwpsRules[0].radius=260;
 dwpsRules[0].sourceClass=1;
 dwpsRules[0].fixtureId=17;
 dwpsRules[0].shadowOff=qtrue;
 dwpsRules[0].numCasters=1;
 dwpsRules[0].casters[0].id=0;
 dwpsRules[0].casters[0].surface=surfA[0].data;
 Q_strncpyz(dwpsRules[0].casters[0].material,shaderA.name,MAX_QPATH);
 memcpy(dwpsRules[0].casters[0].bounds,surfA[0].cullinfo.bounds,sizeof(surfA[0].cullinfo.bounds));
}
static void NewSession(void)
{
 dwpsWorld=NULL;dwpsWorldSurfaces=NULL;dwpsMap[0]=0;
 dwpsNumRules=0;dwpsSelected=-1;dwpsLastSurface=-1;
 memset(dwpsRules,0,sizeof(dwpsRules));
 dwpsPersistMapHash=0;dwpsPersistGeneration=0;dwpsPersistSlot=-1;
 DWPS_CheckWorld();
}
#define CHECK(a,msg) do{if(!(a)){fprintf(stderr,"FAIL: %s line %d\n",msg,__LINE__);exit(3);}else puts("PASS " msg);}while(0)
int main(void)
{
 ri.FS_ReadFile=MockRead;ri.FS_WriteFile=MockWrite;ri.FS_FreeFile=MockFree;ri.Printf=MockPrint;
 tr.world=&worldA;
 NewSession();
 CHECK(dwpsNumRules==0,"new map has no overrides");
 StartLightRule();
 CHECK(DWPS_SaveCurrentMap(),"persistent write generation 1");
 CHECK(dwpsPersistSlot==0 && dwpsPersistGeneration==1,"first write to journal A");
 CHECK(strstr(disk[0],"DWPCPS_V2")!=NULL,"plain text format");
 CHECK(strstr(disk[0],"textures/metal_misc/ametal_m03dm")!=NULL,"caster material stored");
 CHECK(strstr(disk[0],"maps/boss1.bsp")!=NULL,"map stored");

 NewSession();
 CHECK(dwpsNumRules==1 && dwpsRules[0].shadowOff,"rules auto load after restart");
 CHECK(dwpsRules[0].numCasters==1 && DWPS_CasterValid(&dwpsRules[0].casters[0]),
   "BSP identity pointer and bounds restored safely");
 dwpsRules[0].shadowOff=qfalse;
 CHECK(DWPS_SaveCurrentMap(),"new light ON state saved");
 CHECK(dwpsPersistSlot==1 && dwpsPersistGeneration==2,"second write to journal B");
 NewSession();
 CHECK(dwpsNumRules==1 && !dwpsRules[0].shadowOff,"latest journal restored on restart");

 tr.world=&worldB;NewSession();
 CHECK(dwpsNumRules==0,"other map cannot inherit Boss1 overrides");

 tr.world=&worldA;NewSession();
 CHECK(dwpsNumRules==1 && !dwpsRules[0].shadowOff,"original map reloads its profile");
 disk[1][22]^=0x08;
 NewSession();
 CHECK(dwpsNumRules==1 && dwpsRules[0].shadowOff,"corrupted newest journal falls back to older valid A");
 CHECK(dwpsPersistSlot==0 && dwpsPersistGeneration==1,"fallback generation preserved");

 dwpsRules[0].numCasters=0;
 dwpsRules[0].shadowOff=qfalse;
 dwpsNumRules=0;
 CHECK(DWPS_SaveCurrentMap(),"explicit reset persists empty profile");
 NewSession();
 CHECK(dwpsNumRules==0 && dwpsPersistGeneration==2,"empty latest journal overrides old populated A");

 tr.world=&worldB;NewSession();
 CHECK(dwpsNumRules==0,"no cross-map fallthrough after empty reset");
 tr.world=&worldA;NewSession();

 StartLightRule();
 writeBreak=1;
 CHECK(!DWPS_SaveCurrentMap(),"damaged write is detected by readback");
 CHECK(dwpsPersistGeneration==2,"failed write does not advance generation");
 writeBreak=0;
 NewSession();
 CHECK(dwpsNumRules==0 && dwpsPersistGeneration==2,"failed write does not activate corruption");

 /* On a changed BSP build even if name and surface ID stayed the same,
    map signature mismatch must reject persisted rules. */
 surfA[0].cullinfo.bounds[0][0]-=1;
 NewSession();
 CHECK(dwpsNumRules==0,"BSP geometry change invalidates persisted rules");
 puts("DW_PCPS_V2_NATIVE_JOURNAL_REPLAY_AND_SAFETY_PASS");
 return 0;
}
