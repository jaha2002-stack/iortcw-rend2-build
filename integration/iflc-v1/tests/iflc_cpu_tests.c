/*
 * Real production-code CPU tests for DarkWolf Individual Fire Light Control.
 * The renderer translation unit is included so private parser/math/profile
 * functions are tested without reimplementing their algorithms in the test.
 * --gc-sections removes unrelated GL rendering. The game FS is an in-memory
 * mock and deliberately supports truncation/failure injection for save tests.
 */
#include "tr_scene.c"
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

refimport_t ri;
trGlobals_t tr;
glconfig_t glConfig;
glRefConfig_t glRefConfig;
backEndState_t backEnd;
backEndData_t *backEndData;

static cvar_t testControl;
cvar_t *r_dwFireLightControl = &testControl;
static cvar_t testDynamicLight, testDlightScale, testContainment;
static cvar_t testDlightMode;
cvar_t *r_dynamiclight = &testDynamicLight;
cvar_t *r_dlightScale = &testDlightScale;
cvar_t *r_dlightWorldContainment = &testContainment;
cvar_t *r_dlightMode = &testDlightMode;
static model_t testBrushModel;
model_t *R_GetModelByHandle(qhandle_t handle) { return handle==1?&testBrushModel:NULL; }
qhandle_t RE_RegisterShader(const char *name) { (void)name; return 0; }
shader_t *R_GetShaderByHandle(qhandle_t handle) { (void)handle; return NULL; }

static int testPassed;
static int testFailed;
static int testFlushes;
static char testLog[65536];
static size_t testLogUsed;
static int testArgc;
static char *testArgv[16];

#define CHECK(condition, label) do { \
    if (condition) { ++testPassed; } else { \
        ++testFailed; fprintf(stderr, "FAIL %s:%d %s\n", __FILE__, __LINE__, label); \
    } \
} while (0)
#define CLOSE(a,b) (fabsf((float)(a) - (float)(b)) < 0.0001f)

static void QDECL TestPrintf(int level, const char *fmt, ...) {
    va_list ap; int count; (void)level;
    if (testLogUsed >= sizeof(testLog)-1) return;
    va_start(ap,fmt);
    count=vsnprintf(testLog+testLogUsed,sizeof(testLog)-testLogUsed,fmt,ap);
    va_end(ap);
    if (count>0) testLogUsed += MIN((size_t)count,sizeof(testLog)-testLogUsed-1);
}
void QDECL Com_Printf(const char *fmt, ...) {
    va_list ap; va_start(ap,fmt); vfprintf(stderr,fmt,ap); va_end(ap);
}
void QDECL Com_Error(int level, const char *fmt, ...) {
    va_list ap; (void)level; va_start(ap,fmt); vfprintf(stderr,fmt,ap); va_end(ap); abort();
}
static void QDECL TestError(int level, const char *fmt, ...) __attribute__((noreturn));
static void QDECL TestError(int level, const char *fmt, ...) {
    va_list ap; (void)level; va_start(ap,fmt); vfprintf(stderr,fmt,ap); va_end(ap); abort();
}
static int TestMilliseconds(void) { return 1000; }
static int TestArgCount(void) { return testArgc; }
static char *TestArg(int index) { return index>=0&&index<testArgc?testArgv[index]:""; }
static void *TestAlloc(int size) { return calloc(1,(size_t)size); }
void R_IssuePendingRenderCommands(void) { ++testFlushes; }

typedef struct {
    char path[256];
    char *contents;
    int length;
} testFile_t;
static testFile_t testFiles[12];
static int testWriteFailure;
static int testWriteTruncate;
static char testFailWritePath[256];
static testFile_t *TestFindFile(const char *path, qboolean create) {
    int i; testFile_t *empty=NULL;
    for(i=0;i<(int)ARRAY_LEN(testFiles);++i) {
        if(testFiles[i].path[0]&&!strcmp(testFiles[i].path,path)) return &testFiles[i];
        if(!testFiles[i].path[0]&&!empty) empty=&testFiles[i];
    }
    if(create&&empty) { Q_strncpyz(empty->path,path,sizeof(empty->path)); return empty; }
    return NULL;
}
static long TestReadFile(const char *path, void **out) {
    testFile_t *file=TestFindFile(path,qfalse);
    if(out) *out=NULL;
    if(!file) return -1;
    if(out) { *out=malloc((size_t)file->length+1); memcpy(*out,file->contents,(size_t)file->length); ((char*)*out)[file->length]=0; }
    return file->length;
}
static void TestWriteFile(const char *path,const void *data,int length) {
    testFile_t *file;
    if(testWriteFailure) return;
    if(testFailWritePath[0]&&!strcmp(path,testFailWritePath)) { testFailWritePath[0]=0; return; }
    file=TestFindFile(path,qtrue); if(!file) abort();
    if(testWriteTruncate&&length>0) length/=2;
    free(file->contents); file->contents=malloc((size_t)length+1);
    memcpy(file->contents,data,(size_t)length); file->contents[length]=0; file->length=length;
}
static qboolean TestFileExists(const char *path) { return TestFindFile(path,qfalse)?qtrue:qfalse; }
static void TestClearFiles(void) {
    int i; for(i=0;i<(int)ARRAY_LEN(testFiles);++i) free(testFiles[i].contents);
    memset(testFiles,0,sizeof(testFiles)); testWriteFailure=0; testWriteTruncate=0; testFailWritePath[0]=0;
}

static void TestInit(void) {
    memset(&ri,0,sizeof(ri)); memset(&tr,0,sizeof(tr));
    ri.Printf=TestPrintf; ri.Error=TestError; ri.Milliseconds=TestMilliseconds;
    ri.Z_Malloc=TestAlloc; ri.Free=free;
    ri.Hunk_AllocateTempMemory=TestAlloc; ri.Hunk_FreeTempMemory=free;
    ri.Cmd_Argc=TestArgCount; ri.Cmd_Argv=TestArg;
    ri.FS_ReadFile=TestReadFile; ri.FS_WriteFile=TestWriteFile;
    ri.FS_FreeFile=free; ri.FS_FileExists=TestFileExists;
    testControl.integer=1; testControl.value=1.0f;
    testDynamicLight.integer=1; testDynamicLight.value=1.0f;
    testDlightScale.integer=1; testDlightScale.value=1.0f;
    testContainment.integer=1; testContainment.value=1.0f;
    testDlightMode.integer=2; testDlightMode.value=2.0f;
    tr.registered=qtrue;
    backEndData=calloc(1,sizeof(*backEndData));
    if(!backEndData) abort();
}

static void TestSetOwners(void) {
    memset(s_iflcOwners,0,sizeof(s_iflcOwners));
    memset(s_iflcProfiles,0,sizeof(s_iflcProfiles));
    s_iflcOwnerCount=2;
    Q_strncpyz(s_iflcMap,"crypt1",sizeof(s_iflcMap));
    s_iflcFingerprint=0x1234abcdu;
    Q_strncpyz(s_iflcOwners[0].key,"native:217",sizeof(s_iflcOwners[0].key));
    Q_strncpyz(s_iflcOwners[1].key,"native:218",sizeof(s_iflcOwners[1].key));
    s_iflcOwners[0].nativeOrdinal=217; s_iflcOwners[0].promotedOrdinal=-1;
    s_iflcOwners[1].nativeOrdinal=218; s_iflcOwners[1].promotedOrdinal=-1;
    s_iflcOwners[0].kind=s_iflcOwners[1].kind=IFLC_NATIVE;
}

static void TestParser(void) {
    static const char *bad[] = {
        "DW_IFLC 2\nmap crypt1\nbsp 1234abcd\ncount 0\nend\n",
        "DW_IFLC 1\nmap escape1\nbsp 1234abcd\ncount 0\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abce\ncount 0\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount -1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 999999999999999\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 0\nfixture native:217 1 1 1 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:999 1 1 1 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 2\nfixture native:217 1 1 1 0 0 1 1 1\nfixture native:217 2 1 1 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 nan 1 1 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1 inf 1 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1 1 -inf 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1e1000 1 1 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 3.001 1 1 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 -0.1 1 1 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1 0.249 1 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1 2.01 1 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1 1 3.01 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1 1 1 2 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1 1 1 0 2 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1 1 1 0 1 1.1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1 1 1 0 1 0 0 0\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1junk 1 1 0 0 1 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1 1 1 0 0 1 1 1 extra\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 1\nfixture native:217 1 1 1 0 0 1 1\nend\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 0\n",
        "DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 0\nend\ntrailing\n"
    };
    const char *valid="DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 2\nfixture native:217 2 1.4 1 0 0 1 .52 .16\nfixture native:218 .5 .25 3 0 1 1 .58 .23\nend\n";
    iflcProfile_t parsed[256];
    iflcProfile_t untouched[256];
    const char *reason=NULL;
    int count=-1, i;
    TestSetOwners();
    memset(parsed,0,sizeof(parsed));
    CHECK(R_IFLC_ParseProfile(valid,(int)strlen(valid),parsed,&count,&reason),"valid profile loads");
    CHECK(count==2,"declared profile count");
    CHECK(parsed[0].owner==0&&parsed[1].owner==1,"stable key resolves owners");
    CHECK(CLOSE(parsed[0].direct,2)&&CLOSE(parsed[0].radius,1.4f),"profile values preserved");
    CHECK(CLOSE(parsed[1].volume,3)&&parsed[1].colorEnabled,"second profile preserved");
    memcpy(untouched,s_iflcProfiles,sizeof(untouched));
    for(i=0;i<(int)ARRAY_LEN(bad);++i) {
        qboolean accepted=R_IFLC_ParseProfile(bad[i],(int)strlen(bad[i]),parsed,&count,&reason);
        if(accepted) fprintf(stderr,"Bad parser case %d accepted: %s",i,bad[i]);
        CHECK(!accepted,"malformed/mismatched profile rejected");
        CHECK(!memcmp(untouched,s_iflcProfiles,sizeof(untouched)),"parse failure leaves live profiles unchanged");
    }
    for(i=0;i<=(int)strlen(valid)-4;++i) {
        char *shortText=malloc((size_t)i+1);
        memcpy(shortText,valid,(size_t)i); shortText[i]=0;
        CHECK(!R_IFLC_ParseProfile(shortText,i,parsed,&count,&reason),"every incomplete valid-file prefix rejected");
        free(shortText);
    }
    {
        const char *empty="DW_IFLC 1\nmap crypt1\nbsp 1234abcd\ncount 0\nend\n";
        CHECK(R_IFLC_ParseProfile(empty,(int)strlen(empty),parsed,&count,&reason)&&count==0,"valid empty profile");
    }
    printf("CHECKED parser: stable keys, ranges, finite values, duplicates, version/map/BSP, truncation\n");
}

static iflcProfile_t TestProfile(int owner) {
    iflcProfile_t p;
    memset(&p,0,sizeof(p)); p.used=qtrue; p.owner=owner;
    p.direct=p.radius=p.volume=1.0f;
    VectorSet(p.color,1.0f,0.52f,0.16f);
    return p;
}
static dlight_t TestNativeLight(void) {
    dlight_t dl; memset(&dl,0,sizeof(dl));
    VectorSet(dl.origin,120,16,64); VectorSet(dl.color,1,.5,.2);
    dl.radius=200; dl.forced=qtrue; dl.worldOcclusion=qtrue;
    dl.shadowSourceClass=DWSHADOW_SOURCE_PERSISTENT_FIRE;
    dl.nativeAuthoredDlight=qtrue; dl.fireVolumetricSource=qtrue;
    dl.staticPromoteFixtureId=-1; dl.fireVolumetricNativeOrdinal=217;
    dl.fireVolumetricSpeakerOrdinal=330;
    VectorSet(dl.fireVolumetricSpeakerOrigin,120,16,62);
    dl.fireVolumetricSpeakerDistance=2;
    return dl;
}
static void TestApply(void) {
    dlight_t a=TestNativeLight(),original=a,b=TestNativeLight(),peer=b,expected;
    iflcProfile_t p=TestProfile(0);
    int i;
    p.direct=2; p.radius=1.4f;
    R_IFLC_ApplyProfile(&a,&p,qfalse);
    CHECK(CLOSE(a.color[0],2)&&CLOSE(a.color[1],1)&&CLOSE(a.color[2],.4f),"direct scales RGB");
    CHECK(CLOSE(a.radius,280),"radius scales independently");
    CHECK(CLOSE(a.iflcBaseRadius,200)&&!memcmp(a.iflcBaseColor,original.color,sizeof(vec3_t)),"immutable original volume input");
    CHECK(CLOSE(a.iflcVolumeGain,1),"direct override leaves volume gain unity");
    CHECK(!memcmp(&b,&peer,sizeof(b)),"neighbor light untouched");
    expected=original; expected.radius=280; VectorScale(original.color,2,expected.color);
    CHECK(!memcmp(&a,&expected,offsetof(dlight_t,iflcActive)),"identity, classification, containment flags preserved");
    for(i=0;i<1000;++i) R_IFLC_ApplyProfile(&a,&p,qfalse);
    CHECK(CLOSE(a.radius,280)&&CLOSE(a.color[0],2),"repeated scene apply does not accumulate gains");
    p=TestProfile(0); p.direct=0;
    R_IFLC_ApplyProfile(&a,&p,qfalse);
    CHECK(a.color[0]==0&&a.color[1]==0&&a.color[2]==0,"zero direct mutes direct light");
    CHECK(!memcmp(a.iflcBaseColor,original.color,sizeof(vec3_t))&&CLOSE(a.iflcVolumeGain,1),"zero direct preserves independent volume");
    CHECK(a.fireVolumetricSource&&a.nativeAuthoredDlight&&a.worldOcclusion,"zero direct retains physical semantics");
    p=TestProfile(0); p.volume=3;
    R_IFLC_ApplyProfile(&a,&p,qfalse);
    CHECK(!memcmp(&a,&original,offsetof(dlight_t,iflcActive)),"volume-only profile preserves all original direct fields");
    CHECK(CLOSE(a.iflcVolumeGain,3),"volume gain above one is retained");
    p=TestProfile(0); p.volume=0;
    R_IFLC_ApplyProfile(&a,&p,qfalse);
    CHECK(!memcmp(&a,&original,offsetof(dlight_t,iflcActive))&&a.iflcVolumeGain==0,"zero volume leaves direct intact");
    a=original; a.radius=700; VectorSet(a.color,2,1,.4f); expected=a;
    p=TestProfile(0); p.volume=2;
    R_IFLC_ApplyProfile(&a,&p,qfalse);
    CHECK(!memcmp(&a,&expected,offsetof(dlight_t,iflcActive)),"volume-only must not cap original large radius or HDR color");
    a=original; p=TestProfile(0); p.colorEnabled=1; VectorSet(p.color,1e-40f,0,0);
    R_IFLC_ApplyProfile(&a,&p,qfalse);
    CHECK(isfinite(a.color[0])&&isfinite(a.color[1])&&isfinite(a.color[2]),"tiny positive hue never produces Inf/NaN");
    CHECK(CLOSE(.2126f*a.color[0]+.7152f*a.color[1]+.0722f*a.color[2],
                .2126f*original.color[0]+.7152f*original.color[1]+.0722f*original.color[2]),"hue override preserves Rec709 luminance");
    printf("CHECKED profile application: source isolation, no accumulation, direct/volume independence, flags\n");
}

static world_t testWorld;
static mnode_t testLeaf;
static byte testVis=1;
static FBO_t testWorldFbo;
static refdef_t TestReadyScene(void) {
    refdef_t fd;
    TestSetOwners();
    memset(&testWorld,0,sizeof(testWorld)); memset(&testLeaf,0,sizeof(testLeaf));
    Q_strncpyz(testWorld.baseName,"crypt1",sizeof(testWorld.baseName));
    testWorld.entityString="{\"classname\" \"worldspawn\"}";
    testWorld.nodes=&testLeaf; testWorld.numnodes=1; testWorld.numClusters=1;
    testWorld.clusterBytes=1; testWorld.vis=&testVis;
    testLeaf.cluster=0; testLeaf.area=0;
    VectorSet(testLeaf.mins,-2048,-2048,-2048); VectorSet(testLeaf.maxs,2048,2048,2048);
    tr.world=&testWorld; tr.dlightWorldFbo=&testWorldFbo;
    s_iflcReady=qtrue; s_iflcDirty=qfalse; s_iflcCatalogOverflow=qfalse;
    s_iflcViewValid=qfalse; s_iflcSurfaceCount=0; s_iflcBrushCount=0;
    s_staticPromotePersistentBuildGeneration=1; s_iflcGeneration=1;
    s_iflcSelected=-1; s_iflcPickCount=0; s_iflcPickCursor=-1;
    r_numdlights=r_firstSceneDlight=r_numentities=r_firstSceneEntity=0;
    memset(backEndData->dlights,0,sizeof(backEndData->dlights));
    testControl.integer=1; testControl.value=1;
    testDynamicLight.integer=1; testDlightScale.value=1; testContainment.integer=1; testDlightMode.integer=2;
    memset(&fd,0,sizeof(fd)); AxisClear(fd.viewaxis); fd.time=1000;
    return fd;
}

static void TestScenes(void) {
    refdef_t fd=TestReadyScene();
    dlight_t previous=TestNativeLight(), first=TestNativeLight(), second=TestNativeLight();
    dlight_t allBefore[MAX_DLIGHTS];
    second.fireVolumetricNativeOrdinal=218; second.origin[1]=80;
    s_iflcProfiles[0]=TestProfile(0); s_iflcProfiles[0].direct=2; s_iflcProfiles[0].radius=1.4f;
    backEndData->dlights[0]=previous; backEndData->dlights[1]=first; backEndData->dlights[2]=second;
    r_firstSceneDlight=1; r_numdlights=3;
    R_IFLC_Frame(&fd);
    CHECK(!memcmp(&previous,&backEndData->dlights[0],sizeof(previous)),"prior scene untouched");
    CHECK(CLOSE(backEndData->dlights[1].color[0],2)&&CLOSE(backEndData->dlights[1].radius,280),"current exact owner modified");
    CHECK(!memcmp(&second,&backEndData->dlights[2],sizeof(second)),"current neighbor unchanged");
    CHECK(r_numdlights==3,"existing override creates no new dlight");
    R_IFLC_Frame(&fd);
    CHECK(CLOSE(backEndData->dlights[1].color[0],2)&&CLOSE(backEndData->dlights[1].radius,280),"scene re-entry idempotent");
    backEndData->dlights[1]=first; backEndData->dlights[2]=second;
    testControl.integer=0;
    memcpy(allBefore,backEndData->dlights,sizeof(allBefore));
    R_IFLC_Frame(&fd);
    CHECK(!memcmp(allBefore,backEndData->dlights,sizeof(allBefore)),"master OFF exact byte parity for fresh scene");
    testControl.integer=1; memset(s_iflcProfiles,0,sizeof(s_iflcProfiles));
    R_IFLC_Frame(&fd);
    CHECK(!memcmp(allBefore,backEndData->dlights,sizeof(allBefore)),"zero profiles exact byte parity");
    s_iflcProfiles[0]=TestProfile(0); s_iflcProfiles[0].direct=3;
    backEndData->dlights[2]=first;
    memcpy(allBefore,backEndData->dlights,sizeof(allBefore));
    R_IFLC_Frame(&fd);
    CHECK(s_iflcOwners[0].runtimeCount==2,"duplicate owners detected");
    CHECK(!memcmp(allBefore,backEndData->dlights,sizeof(allBefore)),"duplicate owner refuses unsafe direct override");
    backEndData->dlights[1]=second; backEndData->dlights[2]=first;
    R_IFLC_Frame(&fd);
    CHECK(CLOSE(backEndData->dlights[2].color[0],3)&&!memcmp(&second,&backEndData->dlights[1],sizeof(second)),"owner stable under dlight index reorder");
    fd.rdflags=RDF_SKYBOXPORTAL;
    backEndData->dlights[1]=first;
    memcpy(allBefore,backEndData->dlights,sizeof(allBefore));
    R_IFLC_Frame(&fd);
    CHECK(!memcmp(allBefore,backEndData->dlights,sizeof(allBefore)),"sky portal scene is untouched");
    printf("CHECKED scenes: current range isolation, duplicates, reordered owners, zero-profile/master-OFF parity\n");
}

static void TestBridge(void) {
    refdef_t fd=TestReadyScene();
    dlight_t before[MAX_DLIGHTS];
    int i;
    for(i=0;i<2;++i) {
        s_iflcOwners[i].kind=IFLC_SURFACE;
        s_iflcOwners[i].nativeOrdinal=s_iflcOwners[i].promotedOrdinal=-1;
        VectorSet(s_iflcOwners[i].origin,100+i*80,0,0);
        s_iflcProfiles[i]=TestProfile(i); s_iflcProfiles[i].enabled=1;
    }
    R_IFLC_Frame(&fd);
    CHECK(r_numdlights==2,"two independent volume-only sources 80u apart both get direct light");
    CHECK(backEndData->dlights[0].iflcOptIn&&backEndData->dlights[1].iflcOptIn,"new sources marked private opt-in");
    CHECK(!backEndData->dlights[0].nativeAuthoredDlight&&!backEndData->dlights[0].fireVolumetricSource,"bridge never impersonates native authored fire");
    CHECK(backEndData->dlights[0].worldOcclusion&&backEndData->dlights[1].worldOcclusion,"bridge requires world containment");
    R_IFLC_Frame(&fd);
    CHECK(r_numdlights==2,"bridge re-entry creates no duplicate source");
    r_numdlights=0; testDlightScale.value=4;
    R_IFLC_Frame(&fd);
    CHECK(r_numdlights==2&&CLOSE(backEndData->dlights[0].radius,512)&&CLOSE(backEndData->dlights[1].radius,512),"new bridge sources honor hard radius cap even at default individual multiplier");
    testDlightScale.value=1;
    r_numdlights=MAX_DLIGHTS; memset(backEndData->dlights,0,sizeof(backEndData->dlights));
    memcpy(before,backEndData->dlights,sizeof(before));
    R_IFLC_Frame(&fd);
    CHECK(r_numdlights==MAX_DLIGHTS&&!memcmp(before,backEndData->dlights,sizeof(before)),"full scene preserves every original source");
    CHECK(s_iflcOwners[0].blockedReason==4,"capacity denial reported");
    r_numdlights=0; testDynamicLight.integer=0;
    R_IFLC_Frame(&fd);
    CHECK(r_numdlights==0&&s_iflcOwners[0].blockedReason==1,"global dynamic-light off respected");
    testDynamicLight.integer=1; testContainment.integer=0;
    R_IFLC_Frame(&fd);
    CHECK(r_numdlights==0&&s_iflcOwners[0].blockedReason==2,"no containment means no unsafe light");
    testContainment.integer=1; fd.areamask[0]=1;
    R_IFLC_Frame(&fd);
    CHECK(r_numdlights==0&&s_iflcOwners[0].blockedReason==3,"closed area suppresses bridge");
    fd.areamask[0]=0; testLeaf.cluster=-1;
    R_IFLC_Frame(&fd);
    CHECK(r_numdlights==0&&s_iflcOwners[0].blockedReason==6,"solid anchor refuses bridge");
    testLeaf.cluster=0; backEndData->dlights[0]=TestNativeLight();
    VectorCopy(s_iflcOwners[0].origin,backEndData->dlights[0].origin); r_numdlights=1;
    R_IFLC_Frame(&fd);
    CHECK(s_iflcOwners[0].blockedReason==5,"existing physical owner suppresses duplicate bridge");
    printf("CHECKED direct bridge: nearby independent fixtures, no duplicates, MAX_DLIGHTS, global/PVS/containment gates\n");
}

static void TestPersistence(void) {
    iflcProfile_t saved[IFLC_MAX_PROFILES],modified[IFLC_MAX_PROFILES];
    testFile_t *file;
    char *savedText;
    int savedLength,flushes;
    TestReadyScene(); TestClearFiles();
    s_iflcProfiles[0]=TestProfile(0); s_iflcProfiles[0].direct=1.8f; s_iflcProfiles[0].radius=1.4f;
    s_iflcProfiles[1]=TestProfile(1); s_iflcProfiles[1].volume=2.5f;
    memcpy(saved,s_iflcProfiles,sizeof(saved)); s_iflcDirty=qtrue;
    R_IFLC_Save_f();
    file=TestFindFile("firelights/crypt1.iflc",qfalse);
    CHECK(file&&file->length>0&&!s_iflcDirty,"save writes verified profile and clears dirty flag");
    if(!file) return;
    savedLength=file->length; savedText=malloc((size_t)savedLength+1);
    memcpy(savedText,file->contents,(size_t)savedLength+1);
    s_iflcProfiles[0].direct=2.7f; s_iflcProfiles[1].volume=.4f; s_iflcDirty=qtrue;
    CHECK(R_IFLC_LoadProfile(qtrue),"reload accepts saved file");
    CHECK(!memcmp(saved,s_iflcProfiles,sizeof(saved))&&!s_iflcDirty,"save/reload exact roundtrip of independent profiles");
    s_iflcProfiles[0].direct=2.9f; s_iflcDirty=qtrue;
    memcpy(modified,s_iflcProfiles,sizeof(modified));
    { const char *wrongMap="DW_IFLC 1\nmap other\nbsp 1234abcd\ncount 0\nend\n";
      TestWriteFile("firelights/crypt1.iflc",wrongMap,(int)strlen(wrongMap)); }
    CHECK(!R_IFLC_LoadProfile(qtrue),"mismatched saved map rejected");
    CHECK(!memcmp(modified,s_iflcProfiles,sizeof(modified))&&s_iflcDirty,"bad reload preserves all live unsaved changes");
    TestWriteFile("firelights/crypt1.iflc",savedText,savedLength);
    testWriteFailure=1;
    R_IFLC_Save_f();
    CHECK(R_IFLC_VerifyFile("firelights/crypt1.iflc",savedText,savedLength)&&s_iflcDirty,"temporary write failure preserves saved file and dirty flag");
    testWriteFailure=0; testWriteTruncate=1;
    R_IFLC_Save_f();
    CHECK(R_IFLC_VerifyFile("firelights/crypt1.iflc",savedText,savedLength)&&s_iflcDirty,"truncated staging file never replaces previous profile");
    testWriteTruncate=0;
    Q_strncpyz(testFailWritePath,"firelights/crypt1.iflc",sizeof(testFailWritePath));
    R_IFLC_Save_f();
    CHECK(R_IFLC_VerifyFile("firelights/crypt1.iflc",savedText,savedLength)&&s_iflcDirty,"failed final write restores previous profile");
    CHECK(R_IFLC_VerifyFile("firelights/crypt1.iflc.bak",savedText,savedLength),"backup preserves previous bytes");
    memcpy(s_iflcProfiles,saved,sizeof(saved)); s_iflcSelected=0;
    R_IFLC_Reset_f();
    CHECK(!s_iflcProfiles[0].used&&s_iflcProfiles[1].used&&CLOSE(s_iflcProfiles[1].volume,2.5f),"reset changes selected owner only");
    R_IFLC_Save_f();
    memset(s_iflcProfiles,0,sizeof(s_iflcProfiles));
    CHECK(R_IFLC_LoadProfile(qtrue)&&s_iflcProfiles[0].used&&s_iflcProfiles[0].owner==1&&!s_iflcProfiles[1].used,"saved reset survives reload");
    TestClearFiles();
    CHECK(R_IFLC_LoadProfile(qtrue)&&!s_iflcProfiles[0].used,"explicit reload with no file restores baseline");
    s_iflcProfiles[0]=TestProfile(0); s_iflcDirty=qtrue;
    flushes=testFlushes; R_IFLC_ResetWorld();
    CHECK(!s_iflcReady&&!s_iflcDirty&&!s_iflcMap[0]&&s_iflcOwnerCount==0&&s_iflcSelected<0&&!s_iflcProfiles[0].used,"world change clears every selection/profile lifetime");
    CHECK(testFlushes>flushes,"world change synchronizes pending renderer work");
    free(savedText);
    printf("CHECKED persistence: transactional reload, verified save/backup/failure, selected reset, map lifetime\n");
}

static void TestCommands(void) {
    iflcProfile_t before[IFLC_MAX_PROFILES];
    TestReadyScene();
    s_iflcSelected=0;
    testArgc=3; testArgv[0]="dw_fl_set"; testArgv[1]="direct"; testArgv[2]="1.8";
    R_IFLC_Set_f();
    CHECK(s_iflcProfiles[0].used&&CLOSE(s_iflcProfiles[0].direct,1.8f)&&s_iflcDirty,"console set edits only selected profile");
    memcpy(before,s_iflcProfiles,sizeof(before)); testArgv[2]="nan";
    R_IFLC_Set_f();
    CHECK(!memcmp(before,s_iflcProfiles,sizeof(before)),"invalid console NaN leaves profiles unchanged");
    testArgv[1]="enabled"; testArgv[2]="1"; R_IFLC_Set_f();
    CHECK(!memcmp(before,s_iflcProfiles,sizeof(before)),"native owner refuses volume-only enabled control");
    s_iflcSelected=-1; testArgv[1]="direct"; testArgv[2]="2"; R_IFLC_Set_f();
    CHECK(!memcmp(before,s_iflcProfiles,sizeof(before)),"ambiguous/no selection cannot modify another flame");
    s_iflcSelected=0; s_iflcOwners[0].ambiguous=qtrue; R_IFLC_Set_f();
    CHECK(!memcmp(before,s_iflcProfiles,sizeof(before)),"ambiguous physical owner refuses console mutation");
    printf("CHECKED commands: selected mutation, invalid finite values, ambiguity, route restrictions\n");
}

static msurface_t testSurfaces[3];
static srfBspSurface_t testBspSurfaces[3];
static srfVert_t testVertices[3][3];
static glIndex_t testIndexes[3]={0,1,2};
static shader_t testShaders[3];
static bmodel_t testBrush;

static void TestTriangle(int index,float x,float y,float size,const char *shaderName) {
    msurface_t *surface=&testSurfaces[index];
    srfBspSurface_t *bsp=&testBspSurfaces[index];
    memset(surface,0,sizeof(*surface)); memset(bsp,0,sizeof(*bsp)); memset(&testShaders[index],0,sizeof(testShaders[index]));
    bsp->surfaceType=SF_TRIANGLES; bsp->numVerts=3; bsp->verts=testVertices[index]; bsp->numIndexes=3; bsp->indexes=testIndexes;
    VectorSet(testVertices[index][0].xyz,x,y-size,-size);
    VectorSet(testVertices[index][1].xyz,x,y+size,-size);
    VectorSet(testVertices[index][2].xyz,x,y,size*2);
    surface->data=(surfaceType_t*)bsp; surface->shader=&testShaders[index];
    Q_strncpyz(testShaders[index].name,shaderName,sizeof(testShaders[index].name)); testShaders[index].sort=SS_OPAQUE;
    surface->cullinfo.type=CULLINFO_BOX;
    VectorSet(surface->cullinfo.bounds[0],x,y-size,-size); VectorSet(surface->cullinfo.bounds[1],x,y+size,size*2);
}

static void TestSelectionAndVolume(void) {
    refdef_t fd=TestReadyScene();
    vec3_t point={100,0,0},wrongPoint={100,100,100};
    float gain;
    int i;
    TestTriangle(0,100,0,6,"textures/flame1"); TestTriangle(1,100,80,6,"textures/flame1");
    TestTriangle(2,50,0,100,"textures/stonewall");
    testWorld.surfaces=testSurfaces; testWorld.numWorldSurfaces=2; testWorld.numsurfaces=3;
    s_iflcSurfaceCount=2;
    for(i=0;i<2;++i) {
        s_iflcSurfaces[i].surfaceIndex=i; s_iflcSurfaces[i].owner=i;
        Q_strncpyz(s_iflcSurfaces[i].shader,"textures/flame1",sizeof(s_iflcSurfaces[i].shader));
        VectorSet(s_iflcSurfaces[i].origin,100,i*80,0);
        VectorCopy(s_iflcSurfaces[i].origin,s_iflcOwners[i].origin); s_iflcOwners[i].surfaceCount=1;
    }
    R_IFLC_SnapshotView(&fd); R_IFLC_Select_f();
    CHECK(s_iflcSelected==0&&s_iflcPickCount==1,"precise ray selects first nearby torch independently");
    VectorSet(fd.viewaxis[0],100,80,0); VectorNormalize(fd.viewaxis[0]);
    R_IFLC_SnapshotView(&fd); R_IFLC_Select_f();
    CHECK(s_iflcSelected==1&&s_iflcPickCount==1,"precise ray selects second nearby torch independently");
    AxisClear(fd.viewaxis); R_IFLC_SnapshotView(&fd);
    VectorSet(tr.refdef.vieworg,999,999,999); VectorSet(tr.refdef.viewaxis[0],-1,0,0);
    R_IFLC_Select_f();
    CHECK(s_iflcSelected==0,"selection uses immutable last main view rather than later refdef");
    testWorld.numWorldSurfaces=3; R_IFLC_Select_f();
    CHECK(s_iflcSelected<0&&s_iflcPickCount==0,"opaque world triangle blocks hidden torch selection");
    testShaders[2].sort=SS_SEE_THROUGH; R_IFLC_Select_f();
    CHECK(s_iflcSelected==0,"transparent overlay permits intentional visible-flame selection");
    testShaders[2].sort=SS_OPAQUE; testWorld.numWorldSurfaces=2;
    memset(&testBrushModel,0,sizeof(testBrushModel)); memset(&testBrush,0,sizeof(testBrush));
    testBrushModel.type=MOD_BRUSH; testBrushModel.bmodel=&testBrush; Q_strncpyz(testBrushModel.name,"*1",sizeof(testBrushModel.name));
    testBrush.firstSurface=2; testBrush.numSurfaces=1;
    memset(&backEndData->entities[0],0,sizeof(backEndData->entities[0]));
    backEndData->entities[0].e.hModel=1; AxisClear(backEndData->entities[0].e.axis); r_numentities=1;
    R_IFLC_SnapshotView(&fd); R_IFLC_Select_f();
    CHECK(s_iflcSelected<0,"closed brush-submodel door blocks hidden torch");
    backEndData->entities[0].e.origin[1]=400;
    R_IFLC_SnapshotView(&fd); R_IFLC_Select_f();
    CHECK(s_iflcSelected==0,"translated open door allows selection with transformed geometry");
    r_numentities=0; R_IFLC_SnapshotView(&fd);
    TestTriangle(1,160,5,2,"textures/flame1"); VectorSet(s_iflcSurfaces[1].origin,160,5,0); VectorCopy(s_iflcSurfaces[1].origin,s_iflcOwners[1].origin);
    R_IFLC_Select_f();
    CHECK(s_iflcSelected<0&&s_iflcPickCount==2,"two possible aim candidates require explicit disambiguation");
    R_IFLC_Next_f(); CHECK(s_iflcSelected==0,"next explicitly selects first candidate");
    R_IFLC_Next_f(); CHECK(s_iflcSelected==1,"next explicitly selects different second candidate");
    s_iflcProfiles[0]=TestProfile(0); s_iflcProfiles[0].volume=.5f;
    s_iflcProfiles[1]=TestProfile(1); s_iflcProfiles[1].volume=2.0f;
    CHECK(R_IFLC_VolumeOverride(0,"textures/flame1",point,&gain)&&CLOSE(gain,.5f),"volume lookup uses stable surface owner");
    CHECK(R_IFLC_VolumeOverride(1,"textures/flame1",s_iflcSurfaces[1].origin,&gain)&&CLOSE(gain,2),"second independent volume gain retained");
    CHECK(!R_IFLC_VolumeOverride(0,"textures/wrong",point,&gain)&&gain==1,"wrong shader cannot inherit override");
    CHECK(!R_IFLC_VolumeOverride(0,"textures/flame1",wrongPoint,&gain)&&gain==1,"wrong anchor cannot inherit override");
    testControl.integer=0;
    CHECK(!R_IFLC_VolumeOverride(0,"textures/flame1",point,&gain)&&gain==1,"volume master OFF returns exact unity");
    testControl.integer=1; s_iflcOwners[0].ambiguous=qtrue;
    CHECK(!R_IFLC_VolumeOverride(0,"textures/flame1",point,&gain)&&gain==1,"ambiguous ownership cannot alter volume");
    printf("CHECKED selection/volume: two nearby torches, world/door LOS, main-view snapshot, ambiguity, stable lookup\n");
}

static void TestCatalog(void) {
    char keys[2][96];
    unsigned int fingerprint;
    TestReadyScene(); TestClearFiles();
    TestTriangle(0,100,0,6,"textures/flame1");
    TestTriangle(1,108,0,6,"textures/flame1");
    TestTriangle(2,180,0,6,"textures/flame1");
    testWorld.surfaces=testSurfaces; testWorld.numWorldSurfaces=testWorld.numsurfaces=3;
    /* Mock the pre-existing production StaticPromote registry as empty. The
     * IFLC catalog itself is built by the real production implementation. */
    s_staticPromotePersistentReady=qtrue;
    Q_strncpyz(s_staticPromotePersistentMapName,testWorld.baseName,sizeof(s_staticPromotePersistentMapName));
    s_staticPromotePersistentEntityString=testWorld.entityString;
    s_staticPromotePersistentCount=0; s_staticPromotePLRMarkerCount=0;
    TestWriteFile("maps/crypt1.bsp","fixture-bsp-a",13);
    s_iflcReady=qfalse;
    CHECK(R_IFLC_EnsureCatalog(),"real catalog builder accepts fingerprinted world geometry");
    CHECK(s_iflcOwnerCount==2&&s_iflcSurfaceCount==3,"coincident flame surfaces deduplicate without merging separate torch");
    CHECK(s_iflcSurfaces[0].owner==s_iflcSurfaces[1].owner&&s_iflcSurfaces[2].owner!=s_iflcSurfaces[0].owner,"surface owners preserve physical one-to-many identity");
    Q_strncpyz(keys[0],s_iflcOwners[0].key,sizeof(keys[0]));
    Q_strncpyz(keys[1],s_iflcOwners[1].key,sizeof(keys[1]));
    fingerprint=s_iflcFingerprint;
    R_IFLC_ResetWorld();
    CHECK(R_IFLC_EnsureCatalog()&&s_iflcOwnerCount==2&&!strcmp(keys[0],s_iflcOwners[0].key)&&!strcmp(keys[1],s_iflcOwners[1].key)&&s_iflcFingerprint==fingerprint,"world reload regenerates identical stable keys/fingerprint");
    s_iflcProfiles[0]=TestProfile(0); s_iflcProfiles[0].direct=2;
    s_iflcDirty=qtrue; R_IFLC_Save_f();
    TestWriteFile("maps/crypt1.bsp","fixture-bsp-b",13);
    R_IFLC_ResetWorld();
    CHECK(R_IFLC_EnsureCatalog()&&s_iflcFingerprint!=fingerprint&&!s_iflcProfiles[0].used,"same map name with changed BSP rejects stale saved overrides");
    TestClearFiles();
    printf("CHECKED catalog: actual world scan, multisurface dedup, stable reload keys, BSP-change rejection\n");
}

int main(void) {
    TestInit();
    TestParser();
    TestApply();
    TestScenes();
    TestBridge();
    TestPersistence();
    TestCommands();
    TestSelectionAndVolume();
    TestCatalog();
    TestClearFiles();
    free(backEndData);
    printf("IFLC CPU assertions: %d passed, %d failed; GPU not exercised\n",testPassed,testFailed);
    return testFailed||testPassed==0?1:0;
}
